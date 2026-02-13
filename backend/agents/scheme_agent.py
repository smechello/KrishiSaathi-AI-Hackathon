"""Scheme Agent - Provides information about government schemes and subsidies."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.knowledge_base.rag_engine import RAGEngine
from backend.services.llm_helper import llm

logger = logging.getLogger(__name__)


class SchemeAgent:
	"""Checks eligibility and provides scheme details with source citations."""

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

	def answer_scheme_query(self, query: str) -> dict[str, Any]:
		"""Answer a scheme-related question using RAG + LLM with source citations.

		This is the primary entry point called by the Supervisor.
		Returns: {"answer": str, "sources": list[str]}
		"""
		rag_context = ""
		sources: list[str] = []
		if self._rag:
			try:
				hits = self._rag.query(query, collection_names=["government_schemes"], n_results=5)
				for h in hits:
					src = self._build_source_label(h)
					if src not in sources:
						sources.append(src)
				rag_context = self._rag.get_relevant_context(
					query, collection_names=["government_schemes"], n_results=5,
				)
			except Exception as exc:
				logger.warning("RAG retrieval failed for scheme query: %s", exc)

		context_block = ""
		if rag_context:
			context_block = (
				"\n\nGovernment scheme information from knowledge base:\n"
				f"{rag_context}\n\n"
			)

		prompt = (
			"You are a Telangana Government Scheme Expert for KrishiSaathi.\n\n"
			"Answer the farmer's question about government schemes clearly:\n"
			"- Provide exact eligibility criteria\n"
			"- List required documents\n"
			"- Explain how to apply (online/offline)\n"
			"- Mention benefit amounts and payment schedules\n"
			"- Include relevant deadlines\n\n"
			"Cite the source of each piece of information as [Source: scheme_name].\n"
			f"{context_block}"
			f"Farmer's question: {query}"
		)
		answer = llm.generate(prompt, role="agent")
		return {
			"answer": answer,
			"sources": sources,
		}

	@staticmethod
	def _build_source_label(hit: dict[str, Any]) -> str:
		"""Build a human-readable source label from a RAG hit."""
		meta = hit.get("metadata", {})
		name = meta.get("name", meta.get("category", ""))
		collection = hit.get("collection", meta.get("source", ""))
		if name:
			return f"{collection}: {name}"
		return collection

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
