from yandex_music_og_songs.normalizer import exact_match, normalize_match_key


def test_normalize_match_key_strips_punctuation():
    assert normalize_match_key("Paint It, Black") == normalize_match_key("Paint It Black")


def test_exact_match_ignores_case_and_punctuation():
    assert exact_match("Adele", "adele")
    assert exact_match("Paint It, Black", "paint it black")
