_last_pair: tuple[str, str] | None = None


def set_last_pair(country_from: str, country_to: str) -> None:
    global _last_pair
    _last_pair = (country_from, country_to)


def get_last_pair() -> tuple[str, str] | None:
    return _last_pair


def clear_last_pair() -> None:
    global _last_pair
    _last_pair = None
