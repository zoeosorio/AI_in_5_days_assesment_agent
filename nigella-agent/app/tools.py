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

from typing import Any

from google import genai
from google.adk.tools import ToolContext
from google.genai import types
from pydantic import BaseModel

from .database import (
    fetch_and_parse_recipe,
    insert_recipe,
    query_recipes_db,
)


def get_recipes(
    query: str | None = None,
    max_prep_time: int | None = None,
    max_cook_time: int | None = None,
    dietary_restrictions: list[str] | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Searches the database of favorite recipes.

    Filters recipes by search terms in name/description, preparation time,
    cooking time, and dietary tags. If dietary_restrictions is not provided,
    it automatically attempts to load them from the user's preferences.

    Args:
        query: Search string to match in recipe name or description.
        max_prep_time: Maximum prep time allowed in minutes.
        max_cook_time: Maximum cook time allowed in minutes.
        dietary_restrictions: List of dietary restrictions (e.g. ['vegetarian']).

    Returns:
        A dictionary with "status" and a list of matching "recipes".
    """
    active_restrictions = []
    if dietary_restrictions is not None:
        active_restrictions = [r.lower().strip() for r in dietary_restrictions]
    elif tool_context is not None:
        active_restrictions = [
            r.lower().strip()
            for r in tool_context.state.get("user:dietary_restrictions", [])
        ]

    # Perform filtered query using SQLAlchemy
    results = query_recipes_db(
        query=query,
        max_prep_time=max_prep_time,
        max_cook_time=max_cook_time,
    )

    filtered_recipes = []
    for recipe in results:
        # Filter by dietary tags in Python
        tags = [t.lower() for t in recipe.dietary_tags]
        match_failed = False
        for restriction in active_restrictions:
            if restriction not in tags:
                match_failed = True
                break
        if match_failed:
            continue

        # Convert RecipeModel to dictionary for tool return
        filtered_recipes.append(recipe.model_dump())

    return {"status": "success", "recipes": filtered_recipes}


def set_user_preferences(
    dietary_restrictions: list[str], tool_context: ToolContext
) -> dict[str, Any]:
    """Saves user dietary restrictions to the persistent user profile.

    Args:
        dietary_restrictions: A list of dietary restrictions (e.g., ['vegetarian', 'gluten-free']).

    Returns:
        A status dictionary.
    """
    clean_restrictions = [r.strip() for r in dietary_restrictions if r.strip()]
    tool_context.state["user:dietary_restrictions"] = clean_restrictions
    return {
        "status": "success",
        "message": f"Successfully updated your dietary preferences to: {clean_restrictions}.",
    }


def get_user_preferences(tool_context: ToolContext) -> dict[str, Any]:
    """Retrieves the user's saved dietary preferences.

    Returns:
        A dictionary with user dietary restrictions.
    """
    prefs = tool_context.state.get("user:dietary_restrictions", [])
    return {"status": "success", "dietary_restrictions": prefs}


class _URLList(BaseModel):
    urls: list[str]


def search_and_add_recipes(
    query: str, max_results: int = 1, tool_context: ToolContext | None = None
) -> dict[str, Any]:
    """Searches Nigella.com for recipes matching the query and adds them to the SQLite database.

    Args:
        query: The search query (e.g. 'lemon cake', 'chocolate cookies').
        max_results: The maximum number of recipe matches to add. Default is 1.

    Returns:
        A dictionary with a success/error message and list of added recipe names.
    """
    client = genai.Client()
    prompt = (
        f"Search for recipe URLs for query '{query}' on nigella.com. "
        f"Return a list of up to {max_results} unique recipe URLs from nigella.com. "
        "Each URL must start with 'https://www.nigella.com/recipes/'."
    )
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                response_mime_type="application/json",
                response_schema=_URLList,
            ),
        )
        urls = (
            response.parsed.urls if (response.parsed and response.parsed.urls) else []
        )
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed during web search: {e}",
        }

    if not urls:
        return {
            "status": "success",
            "message": f"No recipes matching '{query}' were found on Nigella.com.",
            "added_recipes": [],
        }

    added = []
    for url in urls:
        recipe = fetch_and_parse_recipe(url)
        if recipe:
            if insert_recipe(recipe):
                added.append(recipe.name)

    if added:
        return {
            "status": "success",
            "message": f"Successfully fetched and added {len(added)} recipe(s) to the local database.",
            "added_recipes": added,
        }
    else:
        return {
            "status": "success",
            "message": "Found matching URLs, but they were already present in the database or could not be parsed.",
            "added_recipes": [],
        }
