"""Crop Doctor Agent - Diagnoses crop diseases and health issues."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from PIL import Image
import google.generativeai as genai

from backend.config import Config
from backend.knowledge_base.rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class CropDoctorAgent:
	"""Diagnose crop diseases and provide treatment guidance."""

	def __init__(self, rag_engine: RAGEngine | None = None) -> None:
		if not Config.GEMINI_API_KEY:
			raise ValueError("GEMINI_API_KEY is missing in environment.")
		genai.configure(api_key=Config.GEMINI_API_KEY)
		self._model = genai.GenerativeModel(Config.GEMINI_MODEL)
		self._rag = rag_engine

	def diagnose_from_text(self, query: str) -> dict[str, Any]:
		"""Diagnose crop issues from a text description."""
		# Retrieve relevant context from knowledge base via RAG
		rag_context = ""
		if self._rag:
			try:
				rag_context = self._rag.get_relevant_context(
					query,
					collection_names=["crop_diseases", "farming_practices"],
					n_results=5,
				)
			except Exception as exc:
				logger.warning("RAG retrieval failed: %s", exc)

		context_block = ""
		if rag_context:
			context_block = (
				"\n\nRelevant knowledge base information (use this to give precise advice):\n"
				f"{rag_context}\n\n"
			)

		prompt = (
			"You are Dr. Krishi, an expert plant pathologist specialized in Telangana agriculture.\n\n"
			"When diagnosing crop diseases:\n"
			"1. Identify the disease name in English (include Telugu name if known)\n"
			"2. Severity assessment (Low/Medium/High/Critical)\n"
			"3. Immediate treatment steps with specific product names and dosage\n"
			"4. Estimated treatment cost in INR\n"
			"5. Recovery timeline\n"
			"6. Organic/natural alternatives\n"
			"7. Prevention tips for future\n\n"
			"Format your response clearly with emojis for easy reading.\n"
			"Always provide actionable, practical advice that a rural farmer can follow.\n"
			f"{context_block}"
			f"Farmer query: {query}"
		)

		response = self._model.generate_content(prompt)
		return {
			"query": query,
			"diagnosis": response.text.strip(),
		}

	def diagnose_from_image(self, image_path: str, context: str | None = None) -> dict[str, Any]:
		"""Diagnose crop disease from an image path."""
		if not os.path.exists(image_path):
			raise FileNotFoundError(f"Image not found: {image_path}")

		# Retrieve RAG context if crop name provided in context
		rag_context = ""
		if self._rag and context:
			try:
				rag_context = self._rag.get_relevant_context(
					context,
					collection_names=["crop_diseases"],
					n_results=3,
				)
			except Exception as exc:
				logger.warning("RAG retrieval failed: %s", exc)

		image = Image.open(image_path)
		prompt = (
			"You are Dr. Krishi, an expert plant pathologist specialized in Telangana agriculture.\n\n"
			"Analyze the crop image and provide:\n"
			"1. Disease name in English (Telugu name if known) or 'Unknown'\n"
			"2. Severity (Low/Medium/High/Critical)\n"
			"3. Likely cause\n"
			"4. Treatment steps with dosage\n"
			"5. Estimated cost in INR\n"
			"6. Organic alternatives\n"
			"7. Prevention tips\n\n"
			"Keep it concise and farmer-friendly with emojis.\n"
		)
		if rag_context:
			prompt += f"\nRelevant knowledge base information:\n{rag_context}\n\n"
		if context:
			prompt += f"Additional context: {context}\n"

		response = self._model.generate_content([prompt, image])
		return {
			"image_path": image_path,
			"diagnosis": response.text.strip(),
		}

	def get_treatment(self, crop: str, disease_name: str) -> dict[str, Any]:
		"""Retrieve treatment guidance from the local knowledge base."""
		kb = self._load_knowledge_base()
		for entry in kb.get("diseases", []):
			if entry.get("crop", "").lower() == crop.lower() and entry.get("name", "").lower() == disease_name.lower():
				return {
					"crop": crop,
					"disease": disease_name,
					"treatment": entry.get("treatment", []),
					"prevention": entry.get("prevention", []),
				}

		return {
			"crop": crop,
			"disease": disease_name,
			"treatment": ["Consult local agriculture officer for exact dosage."],
			"prevention": ["Use disease-resistant varieties and follow crop rotation."],
		}

	def get_preventive_measures(self, crop: str) -> list[str]:
		"""Return general prevention measures for a crop."""
		kb = self._load_knowledge_base()
		measures: list[str] = []
		for entry in kb.get("diseases", []):
			if entry.get("crop", "").lower() == crop.lower():
				measures.extend(entry.get("prevention", []))

		if not measures:
			return [
				"Use certified seeds.",
				"Maintain proper spacing and airflow.",
				"Avoid over-watering and monitor humidity.",
			]

		return sorted(set(measures))

	def _load_knowledge_base(self) -> dict[str, Any]:
		"""Load crop disease knowledge base from JSON."""
		kb_path = os.path.join(
			os.path.dirname(os.path.dirname(__file__)),
			"knowledge_base",
			"documents",
			"crop_diseases.json",
		)
		try:
			with open(kb_path, "r", encoding="utf-8") as file:
				return json.load(file)
		except FileNotFoundError:
			return {"diseases": []}
