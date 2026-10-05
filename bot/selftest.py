"""Prove the bot can still download, repair it when it cannot, then report.

Sites change what they demand, and when that happens the bot keeps running
while every download fails. Nothing notices until a user complains, which
in practice means days. This downloads a known video on a timer, so the
answer to "does it still work?" is checked rather than assumed.

Run as `python -m bot.selftest`.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import ConfigError, Settings, load_settings
from .downloader import DownloadFailure, run_download

logger = logging.getLogger("bot.selftest")

# A canary only has to prove the pipeline works, not that it is fast.
CHECK_QUALITY = "360"

# Failures that describe the video rather than the bot. A canary that was
# deleted, made private or geo-blocked says nothing about whether the bot
# can still download, and treating it as an outage would mean repairing a
# healthy bot every hour and crying wolf while doing it.
CONTENT_FAILURES = frozenset(
    {"err_unavailable", "err_private", "err_geo", "err_live", "err_too_long"}
)


@dataclass(frozen=True)
class CheckResult:
    url: str
    ok: bool
    detail: str
    strategy: str = ""
    failure_key: str = ""

    @property
    def canary_is_gone(self) -> bool:
        """The link itself died, which is not an outage of the bot."""
        return not self.ok and self.failure_key in CONTENT_FAILURES

    @property
    def summary(self) -> str:
        if self.canary_is_gone:
            mark = "canary gone"
        else:
            mark = "ok" if self.ok else "FAILED"
        via = f" via {self.strategy}" if self.strategy else ""
        return f"{mark}{via}: {self.url}\n    {self.detail}"


def canary_urls(settings: Settings) -> tuple[str, ...]:
    """What to check, preferring links this bot has already downloaded.

    Asking an operator to configure this was the wrong design: a hardcoded
    video gets deleted, and nobody notices until the check cries wolf. The
    bot already knows which links worked, so it watches those.
    """
    raw = os.getenv("SELFTEST_URLS", "").strip()
    if raw:
        return tuple(u.strip() for u in raw.replace(";", ",").split(",") if u.strip())

    from .storage import read_recent_successes

    proven = read_recent_successes(settings.database_path, limit=3)
    if proven:
        logger.info("checking %s link(s) this bot downloaded before", len(proven))
        return tuple(proven)

    # Nothing has been downloaded yet. Checking a hardcoded video instead
    # would mean reporting on a link nobody here can verify is still alive,
    # and a canary that is merely old produces a false alarm on every fresh
    # install. There is genuinely nothing to verify, so say so.
    logger.info("nothing downloaded yet; nothing to check")
    return ()


async def check_one(url: str, settings: Settings, work_root: Path) -> CheckResult:
    """Download `url` for real and confirm a usable file came out."""
    job = work_root / f"selftest-{abs(hash(url)) % 10**8}"
    try:
        result = await run_download(
            url,
            quality=CHECK_QUALITY,
            dest_dir=job,
            cookies_file=settings.cookies_file,
            proxy=settings.proxy,
            max_playlist_items=1,
            max_attempts=settings.max_attempts,
        )
    except DownloadFailure as failure:
        detail = f"{failure.key} {failure.params or ''}".strip()
        return CheckResult(url, False, detail, failure_key=failure.key)
    except Exception as exc:  # noqa: BLE001 - the report is the product
        return CheckResult(url, False, f"{type(exc).__name__}: {exc}")

    try:
        size = result.path.stat().st_size
    except OSError as exc:
        return CheckResult(url, False, f"downloaded but unreadable: {exc}", result.strategy)

    if size <= 0:
        return CheckResult(url, False, "produced an empty file", result.strategy)

    # The bug class that took a day to find: the file exists and the bot can
    # read it, but a local Bot API server cannot, so every upload fails.
    if settings.local_mode:
        unreachable = _first_unreadable(result.path, settings.work_dir)
        if unreachable is not None:
            return CheckResult(
                url, False,
                f"the Bot API server cannot read this path: {unreachable} "
                f"is mode {unreachable.stat().st_mode & 0o777:o}; needs 755",
                result.strategy,
            )

    return CheckResult(url, True, f"{size / 1024 / 1024:.1f} MB", result.strategy)


def _first_unreadable(path: Path, root: Path) -> Path | None:
    """The first component another user could not get through, if any."""
    try:
        if not path.stat().st_mode & 0o004:
            return path
    except OSError:
        return path

    current = path.parent
    for _ in range(12):
        try:
            if not current.stat().st_mode & 0o001:
                return current
        except OSError:
            return current
        if current == root or current.parent == current:
            return None
        current = current.parent
    return None


async def run_checks(settings: Settings) -> list[CheckResult]:
    with tempfile.TemporaryDirectory(dir=settings.work_dir, prefix="selftest-") as tmp:
        root = Path(tmp)
        # TemporaryDirectory creates 0700 by design. The real pipeline uses
        # mkdir(), which follows the umask and yields 0755, so without this
        # the check fails on its own scratch directory and reports a
        # permission problem the bot does not have.
        try:
            root.chmod(0o755)
        except OSError as exc:
            logger.warning("could not open up %s: %s", root, exc)
        # The checks are independent, so a slow site does not delay the rest.
        return list(
            await asyncio.gather(
                *(check_one(url, settings, root) for url in canary_urls(settings))
            )
        )


# --------------------------------------------------------------------------
# Repair
# --------------------------------------------------------------------------


def _run(command: list[str], timeout: float = 600.0) -> tuple[bool, str]:
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    output = (done.stdout + done.stderr).strip()
    return done.returncode == 0, output[-400:]


def repair(settings: Settings) -> list[str]:
    """The things that have actually fixed this bot before, in order."""
    steps: list[str] = []

    # Nearly every outage so far was an extractor that upstream had already
    # fixed on master.
    ok, _ = _run([
        sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "--pre",
        "yt-dlp", "bgutil-ytdlp-pot-provider",
    ])
    steps.append(f"update yt-dlp and the PO token plugin: {'ok' if ok else 'failed'}")

    if shutil.which("docker"):
        ok, _ = _run(["docker", "restart", "bgutil-provider"], timeout=120)
        if ok:
            steps.append("restart the PO token provider: ok")

    if shutil.which("systemctl"):
        ok, _ = _run(["systemctl", "restart", "jalal-bot"], timeout=120)
        steps.append(f"restart the bot: {'ok' if ok else 'failed'}")

    return steps


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


async def notify_admins(settings: Settings, text: str) -> None:
    if not settings.admin_users:
        logger.warning("no ADMIN_USERS configured, so nobody was told")
        return

    from telegram import Bot
    from telegram.error import TelegramError
    from telegram.request import HTTPXRequest

    bot = Bot(
        token=settings.token,
        base_url=settings.api_base_url,
        base_file_url=settings.api_file_base_url,
        local_mode=settings.local_mode,
        request=HTTPXRequest(connect_timeout=30, read_timeout=30),
    )
    async with bot:
        for admin in settings.admin_users:
            try:
                await bot.send_message(admin, text, disable_web_page_preview=True)
            except TelegramError as exc:
                logger.error("could not alert admin %s: %s", admin, exc)


def _canary_report(results: list[CheckResult]) -> str:
    return "\n".join([
        "ℹ️ The self-test links are gone, not the bot",
        "",
        *(r.summary for r in results),
        "",
        "Nothing was repaired: a deleted or blocked video says nothing about",
        "whether downloading works. Point SELFTEST_URLS in .env at links you",
        "actually care about, then: systemctl restart jalal-bot",
    ])


def _report(results: list[CheckResult], steps: list[str] | None = None) -> str:
    lines = ["⚠️ Self-test failed", ""]
    lines += [r.summary for r in results]
    if steps:
        lines += ["", "Tried to repair:"] + [f"  - {s}" for s in steps]
    lines += ["", "journalctl -u jalal-bot -n 50"]
    return "\n".join(lines)


async def main_async(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that downloading still works.")
    parser.add_argument("--no-repair", action="store_true",
                        help="report a failure without trying to fix it")
    parser.add_argument("--quiet", action="store_true",
                        help="do not message the admins")
    args = parser.parse_args(argv)

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO
    )

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    results = await run_checks(settings)
    if not results:
        logger.info(
            "no proven links yet: download something and this starts "
            "watching it automatically"
        )
        return 0

    for result in results:
        (logger.info if result.ok else logger.error)("%s", result.summary)

    if all(r.ok for r in results):
        return 0

    # A dead canary is not an outage. Repairing on one would mean reinstalling
    # yt-dlp and bouncing the service hourly over a video somebody deleted.
    failures = [r for r in results if not r.ok]
    if all(r.canary_is_gone for r in failures):
        logger.warning("every failing link is simply unavailable; not an outage")
        if not args.quiet:
            await notify_admins(settings, _canary_report(failures))
        return 0

    if args.no_repair:
        if not args.quiet:
            await notify_admins(settings, _report(results))
        return 1

    logger.warning("a check failed; attempting repair")
    steps = repair(settings)
    for step in steps:
        logger.info("  %s", step)

    results = await run_checks(settings)
    for result in results:
        (logger.info if result.ok else logger.error)("after repair: %s", result.summary)

    if all(r.ok for r in results):
        logger.info("repaired without help")
        if not args.quiet:
            await notify_admins(
                settings,
                "✅ Downloads had broken and were repaired automatically.\n\n"
                + "\n".join(f"  - {s}" for s in steps),
            )
        return 0

    if not args.quiet:
        await notify_admins(settings, _report(results, steps))
    return 1


def main() -> int:
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
