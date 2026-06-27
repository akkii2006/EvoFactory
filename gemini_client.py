"""
gemini_client.py
----------------
Thin wrapper around the Gemini API (google-generativeai) used by all agents.
Centralizes model selection, generation config, and JSON response parsing.
"""

import json
import re
import google.generativeai as genai

DEFAULT_MODEL = "gemini-2.5-flash-lite"


class GeminiClient:
    def __init__(self, api_key, model_name=DEFAULT_MODEL):
        genai.configure(api_key=api_key)
        self.model_name = model_name

    def generate(self, prompt, system_instruction=None, json_mode=False, temperature=0.7):
        """Run a single generation call and return the raw text response."""
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction,
        )

        generation_config = {"temperature": temperature}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text

    def generate_json(self, prompt, system_instruction=None, temperature=0.4, max_retries=2):
        """
        Run a generation call expecting a JSON object back.
        Retries a couple of times if parsing fails (flash-lite occasionally
        wraps output in markdown fences or adds stray text).
        """
        last_error = None
        text = ""
        for _ in range(max_retries + 1):
            text = self.generate(prompt, system_instruction, json_mode=True, temperature=temperature)
            try:
                return json.loads(_extract_json(text))
            except json.JSONDecodeError as e:
                last_error = e
                continue

        raise ValueError(
            f"Failed to parse JSON from Gemini after {max_retries + 1} attempt(s): {last_error}\n"
            f"Last raw response:\n{text}"
        )


def _extract_json(text):
    """Strip markdown code fences (```json ... ```) if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()
