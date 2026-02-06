"""Market Agent - Provides market prices and trading information."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from backend.knowledge_base.rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class MarketAgent:
	"""Provides mandi prices, trends, and recommendations."""

	def __init__(self, rag_engine: RAGEngine | None = None) -> None:
		self._data = self._load_mandi_prices()
		self._rag = rag_engine

	def get_current_prices(self, crop: str) -> list[dict[str, Any]]:
		"""Return current prices for a crop across mandis."""
		crop_lower = crop.lower()
		results = [
			item
			for item in self._data.get("mandi_prices", [])
			if item.get("crop", "").lower() == crop_lower
		]
		return results

	def get_price_trend(self, crop: str, days: int = 7) -> list[dict[str, Any]]:
		"""Return mock trend data for last N days."""
		base_prices = self.get_current_prices(crop)
		base_price = None
		if base_prices:
			base_price = (base_prices[0].get("price_min", 0) + base_prices[0].get("price_max", 0)) / 2
		else:
			base_price = 2000

		trend = []
		for i in range(days):
			day = datetime.utcnow().date() - timedelta(days=days - i - 1)
			fluctuation = ((i % 3) - 1) * 15
			trend.append(
				{
					"date": day.isoformat(),
					"price": max(0, round(base_price + fluctuation, 2)),
				}
			)

		return trend

	def recommend_best_mandi(self, crop: str) -> dict[str, Any]:
		"""Recommend the best mandi for selling a crop."""
		prices = self.get_current_prices(crop)
		if not prices:
			return {
				"crop": crop,
				"recommendation": "No mandi price data available.",
			}

		best = max(prices, key=lambda x: x.get("price_max", 0))
		return {
			"crop": crop,
			"market": best.get("market"),
			"price_min": best.get("price_min"),
			"price_max": best.get("price_max"),
			"reason": "Highest available price today.",
		}

	def predict_price(self, crop: str, days_ahead: int = 7) -> dict[str, Any]:
		"""Provide a simple price prediction based on recent trends."""
		trend = self.get_price_trend(crop, days=days_ahead)
		if not trend:
			return {
				"crop": crop,
				"prediction": "Insufficient data for prediction.",
			}

		predicted = trend[-1]["price"] * 1.02
		return {
			"crop": crop,
			"days_ahead": days_ahead,
			"predicted_price": round(predicted, 2),
			"note": "Based on recent trend; actual prices may vary.",
		}

	def search_market_info(self, query: str, n_results: int = 5) -> str:
		"""Search the market knowledge base for crop-related market intelligence."""
		if not self._rag:
			return ""
		try:
			return self._rag.get_relevant_context(
				query,
				collection_names=["market_data"],
				n_results=n_results,
			)
		except Exception as exc:
			logger.warning("RAG market search failed: %s", exc)
			return ""

	def _load_mandi_prices(self) -> dict[str, Any]:
		"""Load mandi price data from JSON file."""
		data_path = os.path.join(
			os.path.dirname(os.path.dirname(__file__)),
			"data",
			"mandi_prices.json",
		)
		try:
			with open(data_path, "r", encoding="utf-8") as file:
				return json.load(file)
		except FileNotFoundError:
			return {"mandi_prices": []}
