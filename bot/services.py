"""The shared objects every handler needs, parked on `bot_data`."""

from __future__ import annotations

from dataclasses import dataclass

from telegram.ext import Application, CallbackContext

from .config import Settings
from .inflight import InFlight
from .jobs import JobRegistry
from .membership import MembershipGate
from .storage import Storage
from .throttle import Throttle

BOT_DATA_KEY = "services"


@dataclass(frozen=True)
class Services:
    settings: Settings
    storage: Storage
    throttle: Throttle
    jobs: JobRegistry
    gate: MembershipGate
    inflight: InFlight


def attach(application: Application, services: Services) -> None:
    application.bot_data[BOT_DATA_KEY] = services


def of(context: CallbackContext) -> Services:
    services = context.bot_data.get(BOT_DATA_KEY)
    if services is None:  # pragma: no cover - wiring bug, not user input
        raise RuntimeError("Services were never attached to the application")
    return services
