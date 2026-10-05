from bot.urls import extract_urls, host_of, is_known_platform, normalize, platform_name


def test_finds_links_among_arabic_text():
    text = "شاهد هذا https://youtu.be/abc123، ثم هذا www.tiktok.com/@a/video/7 شكراً"
    assert extract_urls(text) == [
        "https://youtu.be/abc123",
        "https://www.tiktok.com/@a/video/7",
    ]


def test_bare_www_gets_a_scheme():
    assert normalize("www.example.com/v") == "https://www.example.com/v"


def test_strips_sentence_punctuation_but_keeps_paths():
    assert normalize("https://a.co/v.") == "https://a.co/v"
    assert normalize("https://a.co/v!") == "https://a.co/v"
    assert normalize("https://a.co/v،") == "https://a.co/v"
    # A full stop inside the path must survive.
    assert normalize("https://a.co/clip.mp4") == "https://a.co/clip.mp4"


def test_keeps_balanced_parentheses_in_a_path():
    assert normalize("https://a.co/w_(x)") == "https://a.co/w_(x)"
    # A closing bracket the link never opened belongs to the sentence.
    assert normalize("https://a.co/w)") == "https://a.co/w"


def test_deduplicates_and_honours_the_limit():
    text = "https://a.co/1 https://a.co/1 https://a.co/2"
    assert extract_urls(text) == ["https://a.co/1", "https://a.co/2"]
    assert len(extract_urls(" ".join(f"https://a.co/{i}" for i in range(20)), limit=3)) == 3


def test_no_links_returns_empty():
    assert extract_urls("مرحبا كيف الحال") == []
    assert extract_urls("") == []
    assert extract_urls(None) == []


def test_host_parsing_drops_www_and_case():
    assert host_of("https://WWW.YouTube.com/watch?v=1") == "youtube.com"
    assert host_of("not a url") == ""


def test_platform_names():
    assert platform_name("https://youtu.be/x") == "YouTube"
    assert platform_name("https://m.tiktok.com/v/1") == "TikTok"
    assert platform_name("https://x.com/u/status/1") == "X / Twitter"
    assert platform_name("https://fb.watch/abc") == "Facebook"
    # An unknown host degrades to the hostname itself.
    assert platform_name("https://videos.example.org/v") == "videos.example.org"


def test_subdomains_count_as_known():
    assert is_known_platform("https://music.youtube.com/watch?v=1")
    assert not is_known_platform("https://example.org/v")
