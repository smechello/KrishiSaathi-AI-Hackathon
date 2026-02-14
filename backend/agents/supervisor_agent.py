"""Supervisor Agent - Orchestrates all other agents."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import Config
from backend.knowledge_base.rag_engine import RAGEngine
from backend.services.llm_helper import llm

logger = logging.getLogger(__name__)


class SupervisorAgent:
	"""Classifies intent, routes queries to specialist agents, and synthesizes responses."""

	def __init__(self, rag_engine: RAGEngine | None = None) -> None:
		self._rag = rag_engine

		# Lazy-init child agents (created on first use so startup is fast)
		self._agents: dict[str, Any] = {}

	# ── Child-agent factory ────────────────────────────────────────────

	def _get_agent(self, name: str) -> Any:
		"""Return (and lazily create) the requested specialist agent."""
		if name in self._agents:
			return self._agents[name]

		if name == "crop_doctor":
			from backend.agents.crop_doctor_agent import CropDoctorAgent
			self._agents[name] = CropDoctorAgent(rag_engine=self._rag)
		elif name == "market_agent":
			from backend.agents.market_agent import MarketAgent
			self._agents[name] = MarketAgent(rag_engine=self._rag)
		elif name == "scheme_agent":
			from backend.agents.scheme_agent import SchemeAgent
			self._agents[name] = SchemeAgent(rag_engine=self._rag)
		elif name == "soil_agent":
			from backend.agents.soil_agent import SoilAgent
			self._agents[name] = SoilAgent(rag_engine=self._rag)
		elif name == "weather_agent":
			from backend.agents.weather_agent import WeatherAgent
			self._agents[name] = WeatherAgent(rag_engine=self._rag)
		else:
			return None
		return self._agents[name]

	# ── Intent classification ──────────────────────────────────────────

	# ── Intent classification ──────────────────────────────────────────

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

		# Try keyword fallback first to save LLM calls
		fallback = self._keyword_fallback(user_query)
		if fallback["confidence"] >= 0.8:
			return fallback

		# Use LLM only when keyword heuristics are uncertain
		response_text = llm.generate(prompt, role="classifier")
		parsed = self._safe_json_loads(response_text)
		if parsed:
			return parsed

		return fallback

	# ── Routing ────────────────────────────────────────────────────────

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

	# ── Full pipeline: route → call agents → synthesize ────────────────

	def handle_query(self, user_query: str, memory_context: str = "") -> dict[str, Any]:
		"""End-to-end handler: classify → route → call agents → synthesize.

		Parameters
		----------
		user_query : str
			The farmer's question (in English).
		memory_context : str
			Pre-formatted memory context block (from MemoryEngine) to inject
			into all agent prompts for personalised responses.

		Returns:
			{
			  "intent": {...},
			  "agent_responses": [...],
			  "response": "final synthesized answer",
			  "sources": ["source1", ...]
			}
		"""
		intent = self.route_query(user_query)
		routed = intent.get("routed_agents", [])
		entities = intent.get("entities", {})
		agent_responses: list[dict[str, Any]] = []

		for agent_name in routed:
			try:
				result = self._dispatch(agent_name, user_query, entities, memory_context=memory_context)
				if result:
					agent_responses.append(result)
			except Exception as exc:
				logger.error("Agent '%s' failed: %s", agent_name, exc, exc_info=True)
				agent_responses.append({
					"agent": agent_name,
					"text": f"Sorry, {agent_name.replace('_', ' ')} encountered an error.",
					"sources": [],
				})

		# If routed to "supervisor" (general query), answer directly with RAG
		if not agent_responses or "supervisor" in routed:
			general_resp = self._answer_general(user_query, memory_context=memory_context)
			agent_responses.append(general_resp)

		# Synthesize final response
		texts = [r.get("text", "") for r in agent_responses if r.get("text")]
		final_response = self.synthesize_response(texts)

		# Collect all sources
		all_sources: list[str] = []
		for r in agent_responses:
			for s in r.get("sources", []):
				if isinstance(s, str):
					all_sources.append(s)
				else:
					all_sources.append(str(s))
		unique_sources = list(dict.fromkeys(all_sources))  # preserve order, deduplicate

		return {
			"intent": intent,
			"agent_responses": agent_responses,
			"response": final_response,
			"sources": unique_sources,
		}

	# ── Agent dispatch ─────────────────────────────────────────────────

	def _dispatch(self, agent_name: str, query: str, entities: dict[str, Any], memory_context: str = "") -> dict[str, Any] | None:
		"""Call the appropriate agent method and return a standardised result.

		If *memory_context* is provided, it is prepended to the query so that
		specialist agents can use farmer-specific context without being modified.
		"""
		# Build enriched query with memory for specialist agents
		enriched_query = query
		if memory_context:
			enriched_query = f"{memory_context}\n\nFarmer's question: {query}"

		if agent_name == "crop_doctor":
			agent = self._get_agent("crop_doctor")
			result = agent.diagnose_from_text(enriched_query)
			return {
				"agent": "crop_doctor",
				"text": result.get("diagnosis", ""),
				"sources": result.get("sources", []),
				"raw": result,
			}

		if agent_name == "market_agent":
			agent = self._get_agent("market_agent")
			crop = entities.get("crop", "")
			if crop:
				result = agent.get_price_summary(crop, enriched_query)
			else:
				result = agent.get_price_summary("", enriched_query)
			return {
				"agent": "market_agent",
				"text": result.get("summary", ""),
				"sources": result.get("sources", []),
				"raw": result,
			}

		if agent_name == "scheme_agent":
			agent = self._get_agent("scheme_agent")
			result = agent.answer_scheme_query(enriched_query)
			return {
				"agent": "scheme_agent",
				"text": result.get("answer", ""),
				"sources": result.get("sources", []),
				"raw": result,
			}

		if agent_name == "weather_agent":
			agent = self._get_agent("weather_agent")
			# Defensive: extract scalar values from entities
			raw_city = entities.get("location", entities.get("city", "Hyderabad"))
			city = raw_city[0] if isinstance(raw_city, list) else str(raw_city)
			raw_crop = entities.get("crop", "")
			crop = raw_crop[0] if isinstance(raw_crop, list) and raw_crop else str(raw_crop)
			result = agent.get_weather_advisory(city, crop)
			return {
				"agent": "weather_agent",
				"text": result.get("advisory", ""),
				"sources": result.get("sources", []),
				"raw": result,
			}

		if agent_name == "soil_agent":
			agent = self._get_agent("soil_agent")
			# Defensive: flatten list entity values to strings
			safe_entities = {}
			for k, v in entities.items():
				if isinstance(v, list):
					safe_entities[k] = ", ".join(str(x) for x in v)
				else:
					safe_entities[k] = v
			result = agent.answer_soil_query(enriched_query, safe_entities)
			return {
				"agent": "soil_agent",
				"text": result.get("answer", ""),
				"sources": result.get("sources", []),
				"raw": result,
			}

		return None

	# ── General-query handler (uses RAG) ───────────────────────────────

	def _answer_general(self, query: str, memory_context: str = "") -> dict[str, Any]:
		"""Answer a general agricultural question using RAG context + memory."""
		rag_context = ""
		sources: list[str] = []
		if self._rag:
			try:
				hits = self._rag.query(query, n_results=5)
				for h in hits:
					sources.append(h["metadata"].get("source", h["collection"]))
				rag_context = self._rag.get_relevant_context(query, n_results=5)
			except Exception as exc:
				logger.warning("RAG retrieval failed for general query: %s", exc)

		context_block = ""
		if rag_context:
			context_block = (
				"\n\nRelevant knowledge base information:\n"
				f"{rag_context}\n\n"
			)

		# Inject memory context if available
		memory_block = ""
		if memory_context:
			memory_block = f"\n{memory_context}\n"

		prompt = (
			"You are KrishiSaathi, an expert AI agricultural advisor for Telangana farmers.\n"
			"Answer the farmer's question clearly, practically, and concisely.\n"
			"If you use information from the knowledge base below, mention the source.\n"
			"If farmer memory/context is provided, use it to personalise your answer "
			"(e.g. refer to their crops, location, soil type by name).\n"
			f"{context_block}"
			f"{memory_block}"
			f"Farmer's question: {query}"
		)
		response_text = llm.generate(prompt, role="agent")
		return {
			"agent": "supervisor",
			"text": response_text,
			"sources": list(dict.fromkeys(sources)),
		}

	# ── Synthesis ─────────────────────────────────────────────────────

	def synthesize_response(self, agent_responses: list[str]) -> str:
		"""Combine multiple agent responses into a single reply with citations."""
		if not agent_responses:
			return "Sorry, I could not find relevant information at this time. Please try rephrasing your question."
		if len(agent_responses) == 1:
			return agent_responses[0]

		prompt = (
			"You are the KrishiSaathi Supervisor Agent. Combine the following specialist responses "
			"into a single, clear, farmer-friendly answer.\n"
			"Rules:\n"
			"- Preserve key steps, warnings, and source references\n"
			"- If sources are mentioned, keep them\n"
			"- Use a structured format with headings and bullet points\n"
			"- Keep the language simple and practical\n\n"
			+ "\n\n---\n\n".join(agent_responses)
		)
		return llm.generate(prompt, role="synthesis")

	# ── Helpers ────────────────────────────────────────────────────────

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
		"""Fallback routing using keyword heuristics.

		Returns high confidence (0.85) when keywords match clearly,
		so the LLM classifier is skipped to save API quota.
		"""
		words = set(user_query.lower().split())
		query = user_query.lower()
		intent = "general"
		confidence = 0.5
		entities: dict[str, Any] = {}

		# Use word-level matching to avoid substring false positives
		# e.g. "pesticide" should NOT match "pest" keyword

		# Weather keywords (check FIRST — spray/pesticide queries about weather)
		weather_kw = {"weather", "rain", "forecast", "temperature", "monsoon",
					  "humidity", "wind", "storm", "climate"}
		weather_phrases = ["should i spray", "can i spray", "spray today",
						   "spraying advice", "weather advisory"]
		if words & weather_kw or any(p in query for p in weather_phrases):
			intent = "weather"
			confidence = 0.85
			telangana_cities = ["hyderabad", "warangal", "karimnagar", "nizamabad",
							   "khammam", "mahbubnagar", "nalgonda", "adilabad",
							   "medak", "rangareddy", "siddipet", "suryapet"]
			for city in telangana_cities:
				if city in query:
					entities["city"] = city.title()
					break

		# Crop disease keywords (word-level to avoid 'pest' matching 'pesticide')
		elif words & {"disease", "blight", "wilt", "rot", "borer", "pest",
					   "insect", "fungus", "yellowing", "aphid", "mite",
					   "caterpillar", "curling", "dying"}:
			intent = "crop_disease"
			confidence = 0.85
		elif any(p in query for p in ["brown spots", "leaf spots", "black spots",
									 "leaves turning", "plant dying", "crop disease"]):
			intent = "crop_disease"
			confidence = 0.85

		# Market price keywords
		elif words & {"mandi", "price", "rate", "market", "sell",
					   "buy", "msp", "quintal", "wholesale"}:
			intent = "market_price"
			confidence = 0.85

		# Government scheme keywords
		elif words & {"scheme", "subsidy", "government", "loan", "insurance", "apply"}:
			intent = "government_scheme"
			confidence = 0.85
		elif any(p in query for p in ["rythu bandhu", "rythu bima", "pm kisan",
									 "mission kakatiya", "eligib"]):
			intent = "government_scheme"
			confidence = 0.85

		# Soil keywords
		elif words & {"soil", "fertilizer", "nutrient", "compost", "manure",
					   "npk", "urea", "dap", "potash", "rotation"}:
			intent = "soil_health"
			confidence = 0.85
		elif any(p in query for p in ["red soil", "black soil"]):
			intent = "soil_health"
			confidence = 0.85

		# Extract common crop entities
		crops = ["rice", "paddy", "wheat", "cotton", "maize", "chilli", "tomato",
				 "turmeric", "groundnut", "soybean", "red gram", "bengal gram",
				 "sugarcane", "onion", "jowar", "sunflower", "mango", "banana"]
		for crop in crops:
			if crop in query:
				entities["crop"] = crop.title()
				break

		return {
			"primary_intent": intent,
			"secondary_intent": None,
			"entities": entities,
			"language_detected": "en",
			"confidence": confidence,
		}
