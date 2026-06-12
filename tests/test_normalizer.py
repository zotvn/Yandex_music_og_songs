from yandex_music_og_songs.normalizer import base_title, normalize_text, strip_title_suffixes


def test_normalize_text_lowercases_and_trims():
    assert normalize_text("  Hello   World  ") == "hello world"


def test_strip_title_suffixes():
    patterns = [r"\(cover\)"]
    assert strip_title_suffixes("Song (Cover)", patterns) == "Song"


def test_base_title_removes_parentheses_suffix():
    patterns = [r"\(cover\)"]
    assert base_title("Song (Live)", patterns) == "Song"
