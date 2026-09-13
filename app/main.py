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
    # 1. Tenta Open-Meteo Padrão
    try:
      weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,surface_pressure,wind_speed_10m&hourly=temperature_2m&timezone=auto"
      response = await client.get(weather_url)

      if response.status_code == 200:
        data = response.json()
        WEATHER_CACHE[cache_key] = {"timestamp": now, "data": data}
        return {"status": "success", "data": data}
    except Exception as e:
      print(f"Erro Open-Meteo: {e}")

    # 2. Fallback de emergência (wttr.in JSON) se a Open-Meteo bloquear o IP por 429
    try:
      fallback_url = f"https://wttr.in/{lat},{lon}?format=j1"
      resp = await client.get(
          fallback_url, headers={"User-Agent": "Mozilla/5.0"}
      )
      if resp.status_code == 200:
        wttr_data = resp.json()
        curr = wttr_data["current_condition"][0]

        # Adapta o formato wttr.in para a estrutura esperada pelo frontend
        data = {
            "current": {
                "temperature_2m": float(curr.get("temp_C", 0)),
                "wind_speed_10m": float(curr.get("windspeedKmph", 0)),
                "precipitation": float(curr.get("precipMM", 0)),
                "surface_pressure": float(curr.get("pressure", 0)),
                "cape": 0,
            },
            "hourly": {
                "time": [f"T{i:02d}:00" for i in range(24)],
                "temperature_2m": [float(curr.get("temp_C", 0))] * 24,
            },
        }
        WEATHER_CACHE[cache_key] = {"timestamp": now, "data": data}
        return {"status": "success", "data": data}
    except Exception as e:
      print(f"Erro Fallback wttr.in: {e}")

  return {
      "status": "error",
      "detail": "Não foi possível obter os dados no momento.",
  }


@app.get("/api/search")
async def search_city(q: str = Query(..., min_length=2)):
  async with httpx.AsyncClient(timeout=5.0) as client:
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=5&language=pt&format=json"
    resp = await client.get(geo_url)
    return resp.json() if resp.status_code == 200 else {"results": []}
