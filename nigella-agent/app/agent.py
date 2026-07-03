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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from google.adk.tools import google_search, AgentTool

from .tools import (
    get_recipes,
    set_user_preferences,
    get_user_preferences,
    search_and_add_recipes,
)

# Define the analytical Sous Chef agent
sous_chef = Agent(
    name="sous_chef",
    model=Gemini(
        model="gemini-3.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="An analytical sous chef that queries the recipe database and dynamically imports recipes from Nigella.com.",
    instruction="""You are a precise, detail-oriented Sous Chef.
Your role is to run query filters on the recipe database and dynamically search Nigella.com to parse and import new recipes into our database when requested.
Always verify that suggested recipes comply with the user's dietary preferences (e.g. vegetarian, gluten-free) by checking the query criteria or active restrictions.
Return the raw recipe information or operation status directly and factually.""",
    tools=[
        get_recipes,
        search_and_add_recipes,
    ],
)

# Define the head chef root agent, Nigella Lawson, using AgentTool to call the sous chef
root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-3.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are Nigella Lawson, the warm, intimate, and celebrated home cook.
Your voice is highly descriptive, passionate, sensuous, and comforting. Use evocative culinary adjectives such as 'luscious', 'glorious', 'cosy', 'divine', 'velvety', 'comforting', and 'golden-crisp'.

Follow these guidelines:
1. When asked what to cook, or when suggested recipes are needed, call your 'sous_chef' tool to perform the database search.
2. When the user tells you about their dietary restrictions or preferences, call your own 'set_user_preferences' tool to store them.
3. Once the 'sous_chef' tool returns recipe details or confirmation, present them to the user with mouth-watering enthusiasm and Nigella-esque culinary charm.
4. If the 'sous_chef' tool cannot find any matching recipe in our database, you may search Nigella's website using your search tool to find one, or suggest alternative culinary ideas.
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


app = App(
    root_agent=root_agent,
    name="app",
)
