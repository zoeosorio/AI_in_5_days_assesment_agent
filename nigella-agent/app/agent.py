# ruff: noqa
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

import os
import re
from typing import Optional

from google.adk.agents import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.events import Event
from google.adk.models import Gemini
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools import google_search, AgentTool, FunctionTool
from google.genai import types

from .tools import (
    search_database_recipes,
    search_nigella_web_recipes,
    add_recipe_to_database,
    set_user_preferences,
    get_user_preferences,
)


# Custom PII Redaction Plugin
class PIIRedactionPlugin(BasePlugin):
    """Scans agent responses and redacts potential PII (emails and phone numbers)."""

    def __init__(self) -> None:
        super().__init__("pii_redaction_plugin")
        self.email_regex = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
        self.phone_regex = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")

    def _redact(self, text: str) -> str:
        text = self.email_regex.sub("[REDACTED_EMAIL]", text)
        text = self.phone_regex.sub("[REDACTED_PHONE]", text)
        return text

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ) -> Optional[Event]:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    part.text = self._redact(part.text)
        return event


# Determine the running environment (defaults to development 'dev')
is_dev = os.environ.get("ENVIRONMENT", "dev").lower() == "dev"

# Human-In-The-Loop Confirmation Gate (Production only)
add_recipe_tool = FunctionTool(add_recipe_to_database, require_confirmation=True)

if is_dev:
    # Dev Mode: Search Nigella.com directly, do not use/modify the database
    sous_chef_tools = [search_nigella_web_recipes]
    sous_chef_instruction = """You are a precise, detail-oriented Sous Chef running in a DEVELOPMENT environment.
Your role is to search Nigella.com using the 'search_nigella_web_recipes' tool to query recipes directly from the web and parse them.
Since this is a development environment, you must bypass the database and NEVER attempt to save recipes or read from the database.
Always verify that suggested recipes comply with the user's dietary preferences (e.g. vegetarian, gluten-free) by checking the query criteria or active restrictions.
Return the parsed recipe information directly and factually."""
else:
    # Production Mode: Search database, fall back to web query, insert with user approval
    sous_chef_tools = [
        search_database_recipes,
        search_nigella_web_recipes,
        add_recipe_tool,
    ]
    sous_chef_instruction = """You are a precise, detail-oriented Sous Chef running in a PRODUCTION environment.
Your role is to query our recipe database using the 'search_database_recipes' tool first to find matching recipes.
If no matches are found in the database, call 'search_nigella_web_recipes' to find matching recipes on the web.
If you find a recipe on the web that is not in our database, you should save it to the database using the 'add_recipe_to_database' tool.
Always verify that suggested recipes comply with the user's dietary preferences (e.g. vegetarian, gluten-free) by checking the query criteria or active restrictions.
Return the recipe information or operation status directly and factually."""


# Define the analytical Sous Chef agent
sous_chef = Agent(
    name="sous_chef",
    model=Gemini(
        model="gemini-3.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="An analytical sous chef that queries the recipe database and dynamically imports recipes from Nigella.com.",
    instruction=sous_chef_instruction,
    tools=sous_chef_tools,
)

# Define the head chef root agent (Uses Gemini 3.5 Pro for rich persona writing and strict instructions compliance)
root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-3.5-pro",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are Nigella Lawson, the warm, intimate, and celebrated home cook.
Your voice is highly descriptive, passionate, sensuous, and comforting. Use evocative culinary adjectives such as 'luscious', 'glorious', 'cosy', 'divine', 'velvety', 'comforting', and 'golden-crisp'.

Follow these guidelines:
1. When asked what to cook, or when suggested recipes are needed, call your 'sous_chef' tool to perform the search.
2. When the user tells you about their dietary restrictions or preferences, call your own 'set_user_preferences' tool to store them.
3. Once the 'sous_chef' tool returns recipe details or confirmation, present them to the user with mouth-watering enthusiasm and Nigella-esque culinary charm.
4. If the 'sous_chef' tool cannot find any matching recipe, you may search Nigella's website using your search tool to find one, or suggest alternative culinary ideas.
5. Always address the user warmly, as if they are a dear friend sharing a cosy kitchen conversation.
6. Make sure to query the user's preferences using your 'get_user_preferences' tool if you need to check their restrictions.
""",
    tools=[
        google_search,
        AgentTool(sous_chef),
        set_user_preferences,
        get_user_preferences,
    ],
)


# Define and configure the main app
app = App(
    root_agent=root_agent,
    name="app",
    plugins=[PIIRedactionPlugin()],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=15,  # Summarize older events when conversation exceeds 15 steps
        overlap_size=3,  # Keep last 3 events for continuity
        summarizer=LlmEventSummarizer(llm=Gemini(model="gemini-3.5-flash")),
    ),
)
