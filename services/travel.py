from fastapi import HTTPException

from models.travel_model import TravelInfoRequest, TravelInfoResponse
from services.currency import get_exchange_rate
from services.geography import get_country_info
from services.weather import get_weather_summary


async def get_travel_info(request: TravelInfoRequest) -> TravelInfoResponse:
    response = TravelInfoResponse(
        country_from=request.country_from, country_to=request.country_to,
    )
    if not any((request.is_capital, request.is_weather, request.is_currency)):
        return response

    destination = await get_country_info(request.country_to)
    if request.is_capital or request.is_weather:
        if not destination.capital:
            raise HTTPException(status_code=422, detail='Destination has no capital')
        if request.is_capital:
            response.capital_to = destination.capital
        if request.is_weather:
            response.weather = await get_weather_summary(
                f'{destination.capital},{destination.country_code}',
            )

    if request.is_currency:
        origin = destination if request.country_from == request.country_to else (
            await get_country_info(request.country_from)
        )
        if not origin.currency_code or not destination.currency_code:
            raise HTTPException(status_code=422, detail='Country has no currency')
        response.currency_code_from = origin.currency_code
        response.currency_name_from = origin.currency_name
        response.currency_code_to = destination.currency_code
        response.currency_name_to = destination.currency_name
        response.exchange_rate = await get_exchange_rate(
            origin.currency_code, destination.currency_code,
        )

    return response
