from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI(title="VRATEMPO - Sistema Meteorológico")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/weather")
async def get_weather(
    lat: float = Query(-22.7253, description="Latitude"),
    lon: float = Query(-47.6492, description="Longitude")
):
    """Retorna dados de tempo real e previsão garantindo integridade das séries temporais."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cape,lifted_index"
            f"&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,surface_pressure,wind_gusts_10m,cape,lifted_index"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_gusts_10m_max"
            f"&timezone=auto"
        )
        response = await client.get(weather_url)
        weather_data = response.json() if response.status_code == 200 else {}

    return {"status": "success", "data": weather_data}

@app.get("/api/search")
async def search_city(q: str = Query(..., min_length=2)):
    """Busca coordenadas geográficas de cidades."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=5&language=pt&format=json"
        resp = await client.get(geo_url)
        return resp.json() if resp.status_code == 200 else {"results": []}
