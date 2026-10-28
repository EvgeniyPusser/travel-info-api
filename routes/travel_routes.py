from fastapi import APIRouter, HTTPException, Request

from cache import get_last_pair, set_last_pair
from models.travel_model import TravelInfoRequest, TravelInfoResponse


router = APIRouter()
