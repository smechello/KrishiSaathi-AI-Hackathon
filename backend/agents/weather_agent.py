"""Weather Agent - Provides weather forecasts and crop-specific advisories."""

from __future__ import annotations

import logging
from typing import Any

import requests

from backend.config import Config
from backend.knowledge_base.rag_engine import RAGEngine
from backend.services.llm_helper import llm

logger = logging.getLogger(__name__)


class WeatherAgent:
	"""Fetches weather data and provides RAG-enhanced crop-specific advice."""

	def __init__(self, rag_engine: RAGEngine | None = None) -> None:
		if not Config.OPENWEATHER_API_KEY:
			raise ValueError("OPENWEATHER_API_KEY is missing in environment.")
		self._api_key = Config.OPENWEATHER_API_KEY
		self._rag = rag_engine

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

	# ── RAG-powered weather advisory (called by Supervisor) ────────────

	def get_weather_advisory(self, city: str, crop: str = "") -> dict[str, Any]:
		"""Generate a full weather advisory using live data + RAG farming practices.

		Returns: {"advisory": str, "weather": dict, "sources": list[str]}
		"""
		# Fetch live weather
		weather: dict[str, Any] = {}
		forecast_text = ""
		try:
			weather = self.get_current_weather(city)
			forecast = self.get_forecast(city, days=3)
			if forecast:
				lines = []
				for day in forecast:
					lines.append(f"  {day['date']}: {day['temp_c']}°C, {day['description']}, humidity {day['humidity']}%")
				forecast_text = "\n".join(lines)
		except Exception as exc:
			logger.warning("Weather API call failed for '%s': %s", city, exc)
			weather = {"city": city, "temperature_c": "N/A", "humidity": "N/A", "description": "unavailable"}

		# Gather RAG context for farming practices
		rag_context = ""
		sources: list[str] = []
		if self._rag:
			try:
				search_q = f"weather advisory {crop} {city} season farming"
				hits = self._rag.query(
					search_q,
					collection_names=["farming_practices", "crop_diseases"],
					n_results=4,
				)
				for h in hits:
					meta = h.get("metadata", {})
					name = meta.get("name", meta.get("category", ""))
					col = h.get("collection", "")
					src = f"{col}: {name}" if name else col
					if src not in sources:
						sources.append(src)
				rag_context = self._rag.get_relevant_context(
					search_q,
					collection_names=["farming_practices", "crop_diseases"],
					n_results=4,
				)
			except Exception as exc:
				logger.warning("RAG weather context failed: %s", exc)

		# Build LLM prompt
		weather_block = (
			f"Live weather for {city}:\n"
			f"  Temperature: {weather.get('temperature_c', 'N/A')}°C\n"
			f"  Humidity: {weather.get('humidity', 'N/A')}%\n"
			f"  Wind: {weather.get('wind_speed', 'N/A')} m/s\n"
			f"  Conditions: {weather.get('description', 'N/A')}\n"
		)
		if forecast_text:
			weather_block += f"\n3-day forecast:\n{forecast_text}\n"

		context_parts = [weather_block]
		if rag_context:
			context_parts.append(f"Farming practice knowledge base:\n{rag_context}")

		context_block = "\n\n".join(context_parts)

		crop_note = f" for {crop} crop" if crop else ""
		prompt = (
			f"You are a Weather & Crop Advisory Expert for KrishiSaathi, serving Telangana farmers.\n\n"
			f"Based on the weather data below, provide a practical advisory{crop_note}:\n"
			"- Current conditions summary\n"
			"- Spray/irrigation recommendation\n"
			"- Disease risk warnings based on humidity/temperature\n"
			"- Specific farming activities to do or avoid today\n"
			"- 3-day outlook and preparations\n\n"
			"Cite knowledge base sources where applicable.\n"
			f"\n{context_block}\n\n"
			f"Farmer's location: {city}"
		)
		advisory = llm.generate(prompt, role="agent")
		return {
			"advisory": advisory,
			"weather": weather,
			"sources": sources,
		}
