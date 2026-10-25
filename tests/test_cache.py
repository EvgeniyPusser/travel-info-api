import pytest

from cache import clear_last_pair, get_last_pair, set_last_pair


@pytest.fixture(autouse=True)
def reset_cache():
    clear_last_pair()
    yield
    clear_last_pair()


def test_get_last_pair_returns_none_when_empty():
    assert get_last_pair() is None


def test_set_last_pair_stores_countries_in_order():
    set_last_pair('France', 'Israel')
    assert get_last_pair() == ('France', 'Israel')


def test_set_last_pair_replaces_previous_pair():
    set_last_pair('France', 'Israel')
    set_last_pair('Germany', 'Japan')
    assert get_last_pair() == ('Germany', 'Japan')


def test_get_last_pair_preserves_stored_pair():
    set_last_pair('France', 'Israel')
    assert get_last_pair() == ('France', 'Israel')
    assert get_last_pair() == ('France', 'Israel')


def test_clear_last_pair_removes_stored_pair():
    set_last_pair('France', 'Israel')
    clear_last_pair()
    assert get_last_pair() is None


def test_clear_last_pair_accepts_empty_cache():
    clear_last_pair()
    assert get_last_pair() is None


def test_set_last_pair_works_after_clearing():
    set_last_pair('France', 'Israel')
    clear_last_pair()
    set_last_pair('Germany', 'Japan')
    assert get_last_pair() == ('Germany', 'Japan')
