"""Scheme Agent - Provides information about government schemes and subsidies."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.knowledge_base.rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class SchemeAgent:
	"""Checks eligibility and provides scheme details."""

	def __init__(self, rag_engine: RAGEngine | None = None) -> None:
		self._schemes = self._load_schemes()
		self._rag = rag_engine

	def check_eligibility(self, farmer_profile: dict[str, Any]) -> list[dict[str, Any]]:
		"""Return list of schemes that match a farmer profile (basic rules)."""
		eligible = []
		for scheme in self._schemes.get("schemes", []):
			criteria = scheme.get("eligibility", [])
			if self._matches_profile(farmer_profile, criteria):
				eligible.append(scheme)
		return eligible

	def get_scheme_details(self, scheme_name: str) -> dict[str, Any] | None:
		"""Return scheme details by name, augmented with RAG context."""
		# First try the local JSON database
		for scheme in self._schemes.get("schemes", []):
			if scheme_name.lower() in scheme.get("name", "").lower():
				return scheme

		# Fallback: search RAG knowledge base
		if self._rag:
			try:
				hits = self._rag.query(scheme_name, collection_names=["government_schemes"], n_results=1)
				if hits:
					return {"name": scheme_name, "rag_context": hits[0]["document"], "source": "knowledge_base"}
			except Exception as exc:
				logger.warning("RAG lookup failed for scheme '%s': %s", scheme_name, exc)

		return None

	def get_application_steps(self, scheme_name: str) -> list[str]:
		"""Return high-level application steps for a scheme."""
		scheme = self.get_scheme_details(scheme_name)
		if not scheme:
			return ["Visit your nearest agriculture office for guidance."]

		mode = scheme.get("application_mode", "Offline")
		portal = scheme.get("portal")
		steps = [
			"Prepare required documents (Aadhaar, bank details, land records).",
			"Verify eligibility with local agriculture office.",
		]
		if mode.lower() == "online" and portal:
			steps.append(f"Apply online at: {portal}")
		else:
			steps.append("Submit application at the nearest agriculture office or bank.")
		return steps

	def search_schemes(self, query: str, n_results: int = 5) -> str:
		"""Search the knowledge base for schemes matching a free-text query."""
		if not self._rag:
			return "Knowledge base not available."
		try:
			return self._rag.get_relevant_context(
				query,
				collection_names=["government_schemes"],
				n_results=n_results,
			)
		except Exception as exc:
			logger.warning("RAG search failed: %s", exc)
			return ""

	def get_document_checklist(self, scheme_name: str) -> list[str]:
		"""Return document checklist for a scheme."""
		scheme = self.get_scheme_details(scheme_name)
		if not scheme:
			return ["Aadhaar", "Bank account details", "Land records"]
		return scheme.get("documents", scheme.get("documents_required", []))

	def _load_schemes(self) -> dict[str, Any]:
		data_path = os.path.join(
			os.path.dirname(os.path.dirname(__file__)),
			"data",
			"schemes_database.json",
		)
		try:
			with open(data_path, "r", encoding="utf-8") as file:
				return json.load(file)
		except FileNotFoundError:
			return {"schemes": []}

	def _matches_profile(self, farmer_profile: dict[str, Any], criteria: list[str]) -> bool:
		"""Basic keyword-based matching for eligibility."""
		profile_text = " ".join(str(v).lower() for v in farmer_profile.values())
		if not criteria:
			return False
		return any(keyword.lower() in profile_text for keyword in criteria)
