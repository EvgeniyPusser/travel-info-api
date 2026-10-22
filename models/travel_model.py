from pydantic import BaseModel, Field


class TravelInfoRequest(BaseModel):
    country_from: str
    country_to: str
    is_capital: bool
    is_weather: bool
    is_currency: bool


class TravelInfoResponse(BaseModel):
    country_from: str
    country_to: str
    capital_to: str | None = None
    weather: str | None = None
    currency_code_from: str | None = Field(default=None, min_length=3, max_length=3)
    currency_code_to: str | None = Field(default=None, min_length=3, max_length=3)
    currency_name_from: str | None = None
    currency_name_to: str | None = None
    exchange_rate: float | int | None = None
