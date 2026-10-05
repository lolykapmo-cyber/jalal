import pytest

from bot.i18n import LANGUAGES, STRINGS, normalize_language, quality_label, t


def test_both_languages_define_the_same_keys():
    assert set(STRINGS["ar"]) == set(STRINGS["en"])


@pytest.mark.parametrize("language", LANGUAGES)
def test_no_string_is_empty(language):
    for key, value in STRINGS[language].items():
        assert value.strip(), f"{language}:{key} is empty"


def test_placeholders_match_across_languages():
    """A key must take the same parameters in both catalogues.

    Otherwise t() silently drops the formatting and shows a raw template.
    """
    import re

    placeholder = re.compile(r"\{(\w+)\}")
    for key, arabic in STRINGS["ar"].items():
        arabic_params = sorted(set(placeholder.findall(arabic)))
        english_params = sorted(set(placeholder.findall(STRINGS["en"][key])))
        assert arabic_params == english_params, (
            f"placeholders differ for {key!r}: "
            f"ar={arabic_params} en={english_params}"
        )


def test_lookup_falls_back_instead_of_raising():
    assert t("ar", "cooldown", seconds=5).strip()
    # An unknown language falls back to the default catalogue.
    assert t("de", "fetching") == STRINGS["ar"]["fetching"]
    # An unknown key degrades to the key itself rather than KeyError.
    assert t("ar", "no_such_key") == "no_such_key"
    # A missing placeholder must not blow up mid-download.
    assert t("ar", "cooldown") == STRINGS["ar"]["cooldown"]


def test_language_normalisation():
    assert normalize_language("ar") == "ar"
    assert normalize_language("ar-SA") == "ar"
    assert normalize_language("en-GB") == "en"
    assert normalize_language("de") == "en"
    assert normalize_language(None) == "ar"


def test_quality_labels_cover_every_choice():
    from bot.downloader import QUALITY_CHOICES

    for language in LANGUAGES:
        for choice in QUALITY_CHOICES:
            assert quality_label(language, choice) != choice or choice.isdigit()
