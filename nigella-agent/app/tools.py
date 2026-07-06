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

import json
import logging

from google import genai
from google.adk.tools import ToolContext
from google.genai import types
from pydantic import BaseModel, Field

from .database import (
    RecipeModel,
    fetch_and_parse_recipe,
    insert_recipe,
    query_recipes_db,
)

logger = logging.getLogger("app.tools")


# Strict Output Schemas
class GetRecipesOutput(BaseModel):
    status: str = Field(
        ..., description="The status of the operation (e.g. 'success')."
    )
    recipes: list[RecipeModel] = Field(
        ..., description="A list of matching recipe models."
    )


class SetUserPreferencesOutput(BaseModel):
    status: str = Field(
        ..., description="The status of the operation (e.g. 'success')."
    )
    message: str = Field(
        ...,
        description="A confirmation message or detailed troubleshooting/recovery instructions.",
    )


class GetUserPreferencesOutput(BaseModel):
    status: str = Field(
        ..., description="The status of the operation (e.g. 'success')."
    )
    dietary_restrictions: list[str] = Field(
        ..., description="The user's currently stored dietary restrictions."
    )


class SearchAndAddRecipesOutput(BaseModel):
    status: str = Field(
        ..., description="The status of the operation ('success' or 'error')."
    )
    message: str = Field(
        ...,
        description="Descriptive outcome status with clear troubleshooting/recovery actions if no recipes were added.",
    )
    added_recipes: list[str] = Field(
        ..., description="The list of recipe titles successfully imported."
    )


def get_recipes(
    query: str | None = None,
    max_prep_time: int | None = None,
    max_cook_time: int | None = None,
    dietary_restrictions: list[str] | None = None,
    tool_context: ToolContext | None = None,
) -> GetRecipesOutput:
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
        A structured GetRecipesOutput with query results.
    """
    # Log Intent
    logger.info(
        json.dumps(
            {
                "event": "tool_intent",
                "tool": "get_recipes",
                "params": {
                    "query": query,
                    "max_prep_time": max_prep_time,
                    "max_cook_time": max_cook_time,
                    "dietary_restrictions": dietary_restrictions,
                },
            }
        )
    )

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

        filtered_recipes.append(recipe)

    output = GetRecipesOutput(status="success", recipes=filtered_recipes)

    # Log Outcome
    logger.info(
        json.dumps(
            {
                "event": "tool_outcome",
                "tool": "get_recipes",
                "status": "success",
                "results_count": len(filtered_recipes),
            }
        )
    )

    return output


def set_user_preferences(
    dietary_restrictions: list[str], tool_context: ToolContext
) -> SetUserPreferencesOutput:
    """Saves user dietary restrictions to the persistent user profile.

    Args:
        dietary_restrictions: A list of dietary restrictions (e.g., ['vegetarian', 'gluten-free']).

    Returns:
        A structured SetUserPreferencesOutput.
    """
    # Log Intent
    logger.info(
        json.dumps(
            {
                "event": "tool_intent",
                "tool": "set_user_preferences",
                "params": {"dietary_restrictions": dietary_restrictions},
            }
        )
    )

    clean_restrictions = [r.strip() for r in dietary_restrictions if r.strip()]
    tool_context.state["user:dietary_restrictions"] = clean_restrictions

    output = SetUserPreferencesOutput(
        status="success",
        message=(
            f"Successfully updated your dietary preferences to: {clean_restrictions}. "
            "To reset or clear your preferences, pass an empty list [] as input."
        ),
    )

    # Log Outcome
    logger.info(
        json.dumps(
            {
                "event": "tool_outcome",
                "tool": "set_user_preferences",
                "status": "success",
                "restrictions_count": len(clean_restrictions),
            }
        )
    )

    return output


def get_user_preferences(tool_context: ToolContext) -> GetUserPreferencesOutput:
    """Retrieves the user's saved dietary preferences.

    Returns:
        A structured GetUserPreferencesOutput.
    """
    # Log Intent
    logger.info(json.dumps({"event": "tool_intent", "tool": "get_user_preferences"}))

    prefs = tool_context.state.get("user:dietary_restrictions", [])

    output = GetUserPreferencesOutput(status="success", dietary_restrictions=prefs)

    # Log Outcome
    logger.info(
        json.dumps(
            {
                "event": "tool_outcome",
                "tool": "get_user_preferences",
                "status": "success",
                "preferences": prefs,
            }
        )
    )

    return output


class _URLList(BaseModel):
    urls: list[str]


def search_and_add_recipes(
    query: str, max_results: int = 1, tool_context: ToolContext | None = None
) -> SearchAndAddRecipesOutput:
    """Searches Nigella.com for recipes matching the query and adds them to the SQLite database.

    Args:
        query: The search query (e.g. 'lemon cake', 'chocolate cookies').
        max_results: The maximum number of recipe matches to add. Default is 1.

    Returns:
        A structured SearchAndAddRecipesOutput.
    """
    # Log Intent
    logger.info(
        json.dumps(
            {
                "event": "tool_intent",
                "tool": "search_and_add_recipes",
                "params": {"query": query, "max_results": max_results},
            }
        )
    )

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
        err_msg = (
            f"Failed during web search: {e}. "
            "Troubleshooting: Please check your internet connectivity, confirm that "
            "the Google GenAI client is authenticated, and verify that the Vertex AI "
            "Search service is enabled."
        )
        logger.error(
            json.dumps(
                {
                    "event": "tool_outcome",
                    "tool": "search_and_add_recipes",
                    "status": "error",
                    "error": str(e),
                }
            )
        )
        return SearchAndAddRecipesOutput(
            status="error", message=err_msg, added_recipes=[]
        )

    if not urls:
        warn_msg = (
            f"No recipes matching '{query}' were found on Nigella.com. "
            "Recovery: Try expanding your search term (e.g., search for 'chicken' instead of "
            "'spatchcock chicken') or verify spelling."
        )
        logger.info(
            json.dumps(
                {
                    "event": "tool_outcome",
                    "tool": "search_and_add_recipes",
                    "status": "success",
                    "added_recipes_count": 0,
                }
            )
        )
        return SearchAndAddRecipesOutput(
            status="success", message=warn_msg, added_recipes=[]
        )

    added = []
    for url in urls:
        recipe = fetch_and_parse_recipe(url)
        if recipe:
            if insert_recipe(recipe):
                added.append(recipe.name)

    if added:
        msg = f"Successfully fetched and added {len(added)} recipe(s) to the local database."
        status = "success"
    else:
        msg = (
            "Found matching URLs, but they were already present in the database "
            "or could not be parsed. Recovery: Try searching for a different dish."
        )
        status = "success"

    output = SearchAndAddRecipesOutput(status=status, message=msg, added_recipes=added)

    # Log Outcome
    logger.info(
        json.dumps(
            {
                "event": "tool_outcome",
                "tool": "search_and_add_recipes",
                "status": status,
                "added_recipes": added,
            }
        )
    )

    return output
