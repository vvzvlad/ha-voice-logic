"""Current weather summary via OpenWeatherMap."""

import logging

import requests  # type: ignore

logger = logging.getLogger(__name__)

OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather_summary(city_name, api_key):
    """Return short current weather summary via OpenWeatherMap"""
    try:
        params = { "q": city_name, "appid": api_key, "units": "metric", "lang": "ru" }
        response = requests.get(OPENWEATHERMAP_URL, params=params, verify=False, timeout=8)
        logger.info( f"OpenWeatherMap response status for city '{city_name}': {response.status_code}" )
        if response.status_code != 200:
            logger.error( f"OpenWeatherMap error for city '{city_name}': {response.status_code} - {response.text}" )
            return None

        data = response.json()
        temp = data.get("main", {}).get("temp")
        wind_speed = data.get("wind", {}).get("speed")
        description = None
        weather_list = data.get("weather")
        if isinstance(weather_list, list) and weather_list:
            description = weather_list[0].get("description")

        parts = []
        if isinstance(temp, (int, float)):
            parts.append(f"{int(round(float(temp)))} градусов")
        if description:
            parts.append(description)
        if isinstance(wind_speed, (int, float)):
            wind_raw_str = f"{int(wind_speed)}".replace(".0", "")
            parts.append(f"ветер {wind_raw_str} метров в секунду")

        return ", ".join(parts) if parts else None
    except requests.RequestException as req_err:
        logger.error( f"OpenWeatherMap request error for city '{city_name}': {str(req_err)}" )
        return None
    except (ValueError, TypeError) as parse_err:
        logger.error( f"OpenWeatherMap parse error for city '{city_name}': {str(parse_err)}" )
        return None
