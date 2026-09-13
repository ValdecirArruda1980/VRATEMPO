import time
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI(title="VRATEMPO - Sistema Meteorológico")

templates = Jinja2Templates(directory="app/templates")

WEATHER_CACHE = {}
CACHE_TTL = 300


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
  return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/weather")
async def get_weather(
    lat: float = Query(-22.7253, description="Latitude"),
    lon: float = Query(-47.6492, description="Longitude"),
):
  cache_key = f"{round(lat, 2)}_{round(lon, 2)}"
  now = time.time()

  if (
      cache_key in WEATHER_CACHE
      and (now - WEATHER_CACHE[cache_key]["timestamp"]) < CACHE_TTL
  ):
    return {"status": "success", "data": WEATHER_CACHE[cache_key]["data"]}

  async with httpx.AsyncClient(timeout=10.0) as client:
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cape"
        f"&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,surface_pressure,wind_gusts_10m,cape"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_gusts_10m_max"
        f"&timezone=auto"
    )
    response = await client.get(weather_url)

    if response.status_code != 200:
      fallback_url = (
          f"https://api.open-meteo.com/v1/forecast?"
          f"latitude={lat}&longitude={lon}"
          f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,surface_pressure,wind_speed_10m"
          f"&hourly=temperature_2m,precipitation_probability,surface_pressure"
          f"&timezone=auto"
      )
      response = await client.get(fallback_url)

    if response.status_code == 200:
      data = response.json()
      WEATHER_CACHE[cache_key] = {"timestamp": now, "data": data}
      return {"status": "success", "data": data}

    if cache_key in WEATHER_CACHE:
      return {"status": "success", "data": WEATHER_CACHE[cache_key]["data"]}

    return {
        "status": "error",
        "code": response.status_code,
        "detail": "Erro ao consultar provedor meteorológico.",
    }


@app.get("/api/search")
async def search_city(q: str = Query(..., min_length=2)):
  async with httpx.AsyncClient(timeout=5.0) as client:
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=5&language=pt&format=json"
    resp = await client.get(geo_url)
    return resp.json() if resp.status_code == 200 else {"results": []}
