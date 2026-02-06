"""Weather Agent - Provides weather forecasts and analysis."""

from __future__ import annotations

from typing import Any

import requests

from backend.config import Config


class WeatherAgent:
	"""Fetches weather data and provides crop-specific advice."""

	def __init__(self) -> None:
		if not Config.OPENWEATHER_API_KEY:
			raise ValueError("OPENWEATHER_API_KEY is missing in environment.")
		self._api_key = Config.OPENWEATHER_API_KEY

	def get_current_weather(self, city: str) -> dict[str, Any]:
		"""Return current weather for a city using OpenWeatherMap."""
		url = "https://api.openweathermap.org/data/2.5/weather"
		params = {"q": city, "appid": self._api_key, "units": "metric"}
		response = requests.get(url, params=params, timeout=10)
		response.raise_for_status()
		data = response.json()

		return {
			"city": city,
			"temperature_c": data["main"]["temp"],
			"humidity": data["main"]["humidity"],
			"wind_speed": data["wind"]["speed"],
			"description": data["weather"][0]["description"],
		}

	def get_forecast(self, city: str, days: int = 5) -> list[dict[str, Any]]:
		"""Return a multi-day forecast for a city."""
		url = "https://api.openweathermap.org/data/2.5/forecast"
		params = {"q": city, "appid": self._api_key, "units": "metric"}
		response = requests.get(url, params=params, timeout=10)
		response.raise_for_status()
		data = response.json()

		daily = []
		seen_dates = set()
		for item in data.get("list", []):
			date = item["dt_txt"].split(" ")[0]
			if date in seen_dates:
				continue
			seen_dates.add(date)
			daily.append(
				{
					"date": date,
					"temp_c": item["main"]["temp"],
					"humidity": item["main"]["humidity"],
					"wind_speed": item["wind"]["speed"],
					"description": item["weather"][0]["description"],
				}
			)
			if len(daily) >= days:
				break

		return daily

	def get_crop_advisory(self, crop: str, weather_data: dict[str, Any]) -> list[str]:
		"""Return crop-specific advice based on weather conditions."""
		advice: list[str] = []
		temp = weather_data.get("temperature_c", 0)
		humidity = weather_data.get("humidity", 0)
		description = weather_data.get("description", "").lower()

		if "rain" in description or "storm" in description:
			advice.append("Rain is expected. Avoid pesticide spraying today to prevent wash-off.")
		if temp >= 40:
			advice.append("Extreme heat detected. Increase irrigation frequency and apply mulching to conserve moisture.")
		if humidity >= 80:
			advice.append("High humidity detected. Monitor crops closely for fungal diseases like blast and blight.")
		if temp <= 5:
			advice.append("Cold conditions detected. Cover sensitive crops to prevent frost damage.")

		if not advice:
			advice.append("Weather conditions are favorable. You may proceed with regular farming activities.")

		return [f"{crop}: {item}" for item in advice]

	def check_spray_conditions(self, weather_data: dict[str, Any]) -> dict[str, Any]:
		"""Return whether pesticide spraying is recommended today."""
		description = weather_data.get("description", "").lower()
		humidity = weather_data.get("humidity", 0)
		wind_speed = weather_data.get("wind_speed", 0)

		if "rain" in description or "storm" in description:
			return {"spray": False, "reason": "Rain expected; spraying not recommended."}
		if wind_speed >= 8:
			return {"spray": False, "reason": "High wind speed may cause drift."}
		if humidity >= 85:
			return {"spray": False, "reason": "High humidity increases fungal risk."}

		return {"spray": True, "reason": "Conditions are suitable for spraying."}
