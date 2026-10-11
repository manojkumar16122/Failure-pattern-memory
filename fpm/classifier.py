import json
import os
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

CATEGORIES = {
    "TOOL_FAILURE", "AGENT_FAILURE", "BUILD_ERROR", "TEST_FAILURE",
    "VALIDATION_ERROR", "EXTERNAL_ERROR", "UNKNOWN",
}
SEVERITIES = {"low", "medium", "high", "critical"}

SYSTEM_PROMPT = """You are a failure analysis expert for AI agent systems.
Given a raw failure log, extract structured information.

Return ONLY a valid JSON object with these fields:
- error_category: one of TOOL_FAILURE, AGENT_FAILURE, BUILD_ERROR, TEST_FAILURE, VALIDATION_ERROR, EXTERNAL_ERROR, UNKNOWN
- description: brief 1-sentence summary
- task_type: what was the agent trying to do?
- context_pattern: searchable pattern (3-6 words, e.g. "docker deploy port conflict")
- root_cause: technical explanation
- prevention: how to avoid this next time
- severity: low, medium, high, or critical

Be concise. No markdown. No explanation."""


class FailureClassifier:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY not set. Copy .env.example to .env and add your key.")
        self.client = Groq(api_key=key)
        # Override with GROQ_MODEL in .env if Groq retires this model.
        self.model = model or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    def classify(self, raw_log: str, task_type: str = "unknown") -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Task type: {task_type}\n\nFailure log:\n{raw_log}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from Groq")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Groq returned invalid JSON: {content[:200]}") from e

        if not isinstance(data, dict):
            raise ValueError("Groq returned JSON that is not an object")

        # Normalise so downstream code never gets surprises
        data["error_category"] = str(data.get("error_category", "UNKNOWN")).upper()
        if data["error_category"] not in CATEGORIES:
            data["error_category"] = "UNKNOWN"
        data["severity"] = str(data.get("severity", "medium")).lower()
        if data["severity"] not in SEVERITIES:
            data["severity"] = "medium"
        return data
