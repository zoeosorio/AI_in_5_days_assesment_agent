# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google import genai
from google.genai import types
from pydantic import BaseModel


class Verdict(BaseModel):
    score: int
    explanation: str


def evaluate(instance):
    """Grades the agent's response for adherence to Nigella Lawson's voice."""
    rubric = (
        "Rate the agent's final response on a 1-5 scale (1 poor, 5 excellent) for how well it "
        "captures Nigella Lawson's unique culinary voice. Key indicators of Nigella's voice include: "
        "- Warm, cosy, intimate, conversational tone (treats the user like a dear friend, often greeting them with 'my dear' or similar). "
        "- High passion and rich sensory description of ingredients and food (e.g. textures, aromas, bubbling, crisping). "
        "- Use of evocative adjectives: luscious, glorious, cosy, divine, velvety, comforting, golden-crisp, damp, chocolatey, etc. "
        "Penalize responses that are dry, technical, overly brief, or read like a standard machine-generated recipe list."
    )

    prompt = (
        f"You are an expert evaluator assessing the persona and voice of a cooking agent. {rubric}\n"
        f"Final Response: {instance.get('response', '')}\n"
        f"Full Agent Trace: {instance.get('agent_data', '')}\n"
    )

    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=Verdict,
        ),
    )
    verdict = response.parsed
    if verdict is None:
        return {"score": 0, "explanation": response.text or ""}
    return {"score": max(1, min(5, verdict.score)), "explanation": verdict.explanation}
