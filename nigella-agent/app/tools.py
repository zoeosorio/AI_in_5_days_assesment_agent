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
    insert_recipe,
    query_recipes_db,
)
from .scraper import fetch_and_parse_recipe

logger = logging.getLogger("app.tools")
ai_client = genai.Client()


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


class AddRecipeToDatabaseOutput(BaseModel):
    status: str = Field(
        ..., description="The status of the operation ('success' or 'error')."
    )
    message: str = Field(
        ..., description="Outcome details with troubleshooting instructions."
    )


def _get_embedding(text: str) -> list[float]:
    """Generates 768-dimension text embedding using Vertex AI text-embedding-004 model."""
    try:
        response = ai_client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embeddings[0].values
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []


def search_database_recipes(
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
                "tool": "search_database_recipes",
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

    # Generate Query Vector Embedding
    query_vector = None
    if query:
        query_vector = _get_embedding(query)

    # Perform filtered query
    results = query_recipes_db(
        query_vector=query_vector,
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
                "tool": "search_database_recipes",
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


def search_nigella_web_recipes(query: str, max_results: int = 1) -> GetRecipesOutput:
    """Searches Nigella.com for recipes matching the query and returns the parsed recipes directly.

    Args:
        query: The search query (e.g. 'lemon cake', 'chocolate cookies').
        max_results: The maximum number of recipe matches to return. Default is 1.

    Returns:
        A structured GetRecipesOutput.
    """
    # Log Intent
    logger.info(
        json.dumps(
            {
                "event": "tool_intent",
                "tool": "search_nigella_web_recipes",
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
        logger.error(
            json.dumps(
                {
                    "event": "tool_outcome",
                    "tool": "search_nigella_web_recipes",
                    "status": "error",
                    "error": str(e),
                }
            )
        )
        return GetRecipesOutput(status="error", recipes=[])

    recipes = []
    if urls:
        for url in urls:
            recipe = fetch_and_parse_recipe(url)
            if recipe:
                recipes.append(recipe)

    output = GetRecipesOutput(status="success" if recipes else "empty", recipes=recipes)

    # Log Outcome
    logger.info(
        json.dumps(
            {
                "event": "tool_outcome",
                "tool": "search_nigella_web_recipes",
                "status": "success",
                "recipes_count": len(recipes),
            }
        )
    )

    return output


def add_recipe_to_database(recipe: RecipeModel) -> AddRecipeToDatabaseOutput:
    """Saves a parsed recipe into the persistent database.

    Args:
        recipe: The RecipeModel object representing the recipe to save.

    Returns:
        A structured AddRecipeToDatabaseOutput.
    """
    # Log Intent
    logger.info(
        json.dumps(
            {
                "event": "tool_intent",
                "tool": "add_recipe_to_database",
                "recipe": recipe.name,
            }
        )
    )

    # Generate Embeddings for Recipe
    if not recipe.embedding:
        recipe.embedding = _get_embedding(f"{recipe.name}: {recipe.description}")

    success = insert_recipe(recipe)
    if success:
        status = "success"
        msg = f"Successfully saved recipe '{recipe.name}' to the database."
    else:
        status = "error"
        msg = (
            f"Failed to save recipe '{recipe.name}' to the database. "
            "Troubleshooting: Please check database connection parameters."
        )

    # Log Outcome
    logger.info(
        json.dumps(
            {
                "event": "tool_outcome",
                "tool": "add_recipe_to_database",
                "status": status,
            }
        )
    )

    return AddRecipeToDatabaseOutput(status=status, message=msg)
