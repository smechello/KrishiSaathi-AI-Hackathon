"""Supervisor Agent - Orchestrates all other agents."""

from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai

from backend.config import Config


class SupervisorAgent:
	"""Classifies intent and routes queries to specialist agents."""

	def __init__(self) -> None:
		if not Config.GEMINI_API_KEY:
			raise ValueError("GEMINI_API_KEY is missing in environment.")
		genai.configure(api_key=Config.GEMINI_API_KEY)
		self._model = genai.GenerativeModel(Config.GEMINI_MODEL)

	def classify_intent(self, user_query: str) -> dict[str, Any]:
		"""Classify user intent and extract entities.

		Returns a JSON-compatible dict with keys:
		primary_intent, secondary_intent, entities, language_detected, confidence
		"""
		prompt = (
			"You are the Supervisor Agent for KrishiSaathi, an AI agricultural advisory system.\n\n"
			"Your job:\n"
			"1. Classify the farmer's question into one or more categories\n"
			"2. Extract key entities (crop name, location, disease symptoms, etc.)\n"
			"3. Return a structured JSON with routing information\n\n"
			"Categories: crop_disease, market_price, government_scheme, weather, soil_health, general\n\n"
			"Always respond in JSON format with keys: primary_intent, secondary_intent, entities, "
			"language_detected, confidence.\n\n"
			f"User Question: {user_query}"
		)

		response = self._model.generate_content(prompt)
		parsed = self._safe_json_loads(response.text)
		if parsed:
			return parsed

		return self._keyword_fallback(user_query)

	def route_query(self, user_query: str) -> dict[str, Any]:
		"""Route a user query to the correct agent(s)."""
		intent = self.classify_intent(user_query)
		primary = intent.get("primary_intent")
		secondary = intent.get("secondary_intent")

		routing = {
			"crop_disease": "crop_doctor",
			"market_price": "market_agent",
			"government_scheme": "scheme_agent",
			"weather": "weather_agent",
			"soil_health": "soil_agent",
			"general": "supervisor",
		}

		agents = []
		if primary in routing:
			agents.append(routing[primary])
		if secondary in routing and routing[secondary] not in agents:
			agents.append(routing[secondary])

		intent["routed_agents"] = agents
		return intent

	def synthesize_response(self, agent_responses: list[str]) -> str:
		"""Combine multiple agent responses into a single reply."""
		if not agent_responses:
			return "Sorry, I could not find relevant information at this time. Please try rephrasing your question."
		if len(agent_responses) == 1:
			return agent_responses[0]

		prompt = (
			"You are the Supervisor Agent. Combine the following responses into a single, "
			"clear, farmer-friendly answer. Preserve key steps and warnings.\n\n"
			+ "\n\n".join(agent_responses)
		)
		response = self._model.generate_content(prompt)
		return response.text.strip()

	def _safe_json_loads(self, text: str) -> dict[str, Any] | None:
		"""Try to parse JSON from model output."""
		try:
			return json.loads(text)
		except json.JSONDecodeError:
			pass

		try:
			start = text.find("{")
			end = text.rfind("}")
			if start != -1 and end != -1 and end > start:
				return json.loads(text[start : end + 1])
		except json.JSONDecodeError:
			return None
		return None

	def _keyword_fallback(self, user_query: str) -> dict[str, Any]:
		"""Fallback routing using keyword heuristics."""
		query = user_query.lower()
		intent = "general"

		if any(word in query for word in ["disease", "leaf", "pest", "blight", "wilt", "rot", "borer", "insect"]):
			intent = "crop_disease"
		elif any(word in query for word in ["mandi", "price", "rate", "market", "sell", "buy"]):
			intent = "market_price"
		elif any(word in query for word in ["scheme", "subsidy", "rythu bandhu", "government", "loan"]):
			intent = "government_scheme"
		elif any(word in query for word in ["weather", "rain", "forecast", "temperature", "monsoon"]):
			intent = "weather"
		elif any(word in query for word in ["soil", "fertilizer", "nutrient", "compost", "manure"]):
			intent = "soil_health"

		return {
			"primary_intent": intent,
			"secondary_intent": None,
			"entities": {},
			"language_detected": "en",
			"confidence": 0.6,
		}
