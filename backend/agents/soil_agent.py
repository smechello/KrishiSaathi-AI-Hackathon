"""Soil Agent - Analyzes soil health and provides recommendations."""

from __future__ import annotations

import logging
from typing import Any

from backend.knowledge_base.rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class SoilAgent:
	"""Provides soil health analysis and fertilizer recommendations."""

	def __init__(self, rag_engine: RAGEngine | None = None) -> None:
		self._rag = rag_engine

	def analyze_soil(self, soil_type: str) -> dict[str, Any]:
		"""Return soil characteristics and general notes.

		First tries RAG knowledge base for Telangana-specific soil data,
		then falls back to a static lookup.
		"""
		# Try RAG first for detailed Telangana soil data
		if self._rag:
			try:
				hits = self._rag.query(soil_type, collection_names=["soil_data"], n_results=1)
				if hits and hits[0]["distance"] < 0.5:
					return {
						"soil_type": soil_type,
						"details": hits[0]["document"],
						"source": "knowledge_base",
					}
			except Exception as exc:
				logger.warning("RAG soil lookup failed: %s", exc)

		# Fallback static map
		soil_map = {
			"clay": {
				"characteristics": ["High water retention", "Poor drainage"],
				"notes": ["Avoid waterlogging", "Add organic matter"],
			},
			"sandy": {
				"characteristics": ["Fast drainage", "Low fertility"],
				"notes": ["Frequent irrigation", "Add compost"]
			},
			"loamy": {
				"characteristics": ["Balanced texture", "Good fertility"],
				"notes": ["Maintain organic matter", "Balanced fertilization"],
			},
			"red": {
				"characteristics": ["Good drainage", "Low nutrient content", "Common in Telangana"],
				"notes": ["Apply FYM generously", "Use balanced NPK", "Mulching to conserve moisture"],
			},
			"black": {
				"characteristics": ["High clay content", "Excellent moisture retention", "Poor drainage"],
				"notes": ["Apply gypsum to improve drainage", "Ridges and furrows", "Avoid waterlogging"],
			},
			"laterite": {
				"characteristics": ["Iron-rich", "Acidic", "Low fertility"],
				"notes": ["Lime application to correct acidity", "Heavy FYM", "Rock phosphate recommended"],
			},
			"alluvial": {
				"characteristics": ["River-deposited", "Rich in nutrients", "Good for farming"],
				"notes": ["Ideal for multi-cropping", "Monitor salinity", "Good for rice and vegetables"],
			},
		}
		return soil_map.get(
			soil_type.lower(),
			{
				"characteristics": ["Mixed soil"],
				"notes": ["Conduct soil test for precise recommendations"],
			},
		)

	def get_fertilizer_recommendation(self, crop: str, land_size_acres: float) -> dict[str, Any]:
		"""Provide NPK and fertilizer quantities per acre."""
		crop = crop.lower()
		recommendations = {
			"wheat": {"n": 60, "p": 30, "k": 20},
			"rice": {"n": 80, "p": 40, "k": 40},
			"maize": {"n": 90, "p": 40, "k": 30},
		}
		npk = recommendations.get(crop, {"n": 50, "p": 25, "k": 20})

		urea_kg = round((npk["n"] / 46) * 100 * land_size_acres / 100, 2)
		dap_kg = round((npk["p"] / 46) * 100 * land_size_acres / 100, 2)
		mop_kg = round((npk["k"] / 60) * 100 * land_size_acres / 100, 2)

		return {
			"crop": crop.title(),
			"land_size_acres": land_size_acres,
			"npk_required_kg_per_acre": npk,
			"fertilizers": {
				"urea_kg": urea_kg,
				"dap_kg": dap_kg,
				"mop_kg": mop_kg,
			},
			"estimated_cost_inr": round((urea_kg * 7.5) + (dap_kg * 27) + (mop_kg * 18), 2),
		}

	def get_organic_alternatives(self, crop: str) -> list[str]:
		"""Return organic alternatives for fertilizer."""
		return [
			f"{crop.title()}: Vermicompost 1-2 tons/acre",
			f"{crop.title()}: Jeevamrut 200 liters/acre",
			f"{crop.title()}: Neem cake 100 kg/acre",
		]

	def search_soil_info(self, query: str, n_results: int = 3) -> str:
		"""Search the soil and farming practices knowledge base."""
		if not self._rag:
			return ""
		try:
			return self._rag.get_relevant_context(
				query,
				collection_names=["soil_data", "farming_practices"],
				n_results=n_results,
			)
		except Exception as exc:
			logger.warning("RAG soil search failed: %s", exc)
			return ""

	def suggest_crop_rotation(self, crop: str) -> list[str]:
		"""Suggest a 3-year crop rotation plan for Telangana."""
		crop = crop.lower()
		if crop == "rice":
			return ["Year 1: Rice (Kharif)", "Year 2: Bengal Gram / Maize (Rabi)", "Year 3: Green Gram / Groundnut"]
		if crop == "cotton":
			return ["Year 1: Cotton", "Year 2: Red Gram / Soybean", "Year 3: Maize / Sorghum"]
		if crop == "maize":
			return ["Year 1: Maize", "Year 2: Bengal Gram / Chickpea", "Year 3: Groundnut / Sunflower"]
		if crop == "chilli":
			return ["Year 1: Chilli", "Year 2: Maize / Jowar", "Year 3: Red Gram / Green Gram"]
		return ["Year 1: Main Crop", "Year 2: Legume (Red Gram / Bengal Gram)", "Year 3: Oilseed (Groundnut / Sunflower)"]
