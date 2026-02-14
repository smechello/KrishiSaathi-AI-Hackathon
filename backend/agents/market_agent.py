"""Market Agent - Provides market prices and trading information."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from backend.knowledge_base.rag_engine import RAGEngine
from backend.services.llm_helper import llm

logger = logging.getLogger(__name__)


class MarketAgent:
	"""Provides mandi prices, trends, and recommendations with RAG-powered insights."""

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
			base_price = base_prices[0].get("price_per_quintal", base_prices[0].get("price_max", 2000))
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

		best = max(prices, key=lambda x: x.get("price_per_quintal", x.get("price_max", 0)))
		price = best.get("price_per_quintal", best.get("price_max", "?"))
		return {
			"crop": crop,
			"market": best.get("market"),
			"price_per_quintal": price,
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

	def get_price_summary(self, crop: str, query: str) -> dict[str, Any]:
		"""Generate a RAG-powered market summary.

		Called by the Supervisor for market-related queries.
		Returns: {"summary": str, "sources": list[str]}
		"""
		# Gather local mandi price data
		local_data = ""
		if crop:
			prices = self.get_current_prices(crop)
			if prices:
				lines = [f"Mandi prices for {crop.title()}:"]
				for p in prices:
					price_val = p.get('price_per_quintal', p.get('price_max', '?'))
					unit = p.get('unit', 'INR/quintal')
					lines.append(
						f"  - {p.get('market', 'Unknown')}: ₹{price_val}/{unit}"
					)
				best = self.recommend_best_mandi(crop)
				if best.get("market"):
					lines.append(f"  Best mandi: {best['market']} (₹{best.get('price_per_quintal', '?')})")
				local_data = "\n".join(lines)

		# Gather RAG context
		rag_context = ""
		sources: list[str] = []
		if self._rag:
			try:
				search_q = query or f"{crop} market price Telangana"
				hits = self._rag.query(search_q, collection_names=["market_data"], n_results=5)
				for h in hits:
					src = self._build_source_label(h)
					if src not in sources:
						sources.append(src)
				rag_context = self._rag.get_relevant_context(
					search_q, collection_names=["market_data"], n_results=5,
				)
			except Exception as exc:
				logger.warning("RAG market retrieval failed: %s", exc)

		context_parts = []
		if local_data:
			context_parts.append(f"Current mandi prices:\n{local_data}")
		if rag_context:
			context_parts.append(f"Knowledge base market data:\n{rag_context}")

		context_block = "\n\n".join(context_parts)

		prompt = (
			"You are a Market Intelligence Expert for KrishiSaathi, serving Telangana farmers.\n\n"
			"Answer the farmer's market question with:\n"
			"- Current prices (mention mandi name and unit)\n"
			"- MSP (Minimum Support Price) if known\n"
			"- Best selling recommendation\n"
			"- Price trends or outlook\n"
			"- Practical tips for getting the best price\n\n"
			"Cite sources where applicable as [Source: market_data].\n"
			f"\n{context_block}\n\n"
			f"Farmer's question: {query}"
		)
		summary = llm.generate(prompt, role="agent")
		return {
			"summary": summary,
			"sources": sources,
		}

	@staticmethod
	def _build_source_label(hit: dict[str, Any]) -> str:
		"""Build a human-readable source label from a RAG hit."""
		meta = hit.get("metadata", {})
		name = meta.get("crop", meta.get("category", ""))
		collection = hit.get("collection", meta.get("source", ""))
		if name:
			return f"{collection}: {name}"
		return collection

	def _load_mandi_prices(self) -> dict[str, Any]:
		"""Load mandi price data from JSON file."""
		data_path = os.path.join(
			os.path.dirname(os.path.dirname(__file__)),
			"data",
			"mandi_prices.json",
		)
		try:
			with open(data_path, "r", encoding="utf-8") as file:
				raw = json.load(file)
				# Handle both formats: flat list or {"mandi_prices": [...]}
				if isinstance(raw, list):
					return {"mandi_prices": raw}
				return raw
		except FileNotFoundError:
			return {"mandi_prices": []}
