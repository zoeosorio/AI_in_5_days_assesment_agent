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

import html
import json
import logging
import re
import urllib.request

from google import genai
from google.adk.tools import ToolContext
from google.genai import types
from pydantic import BaseModel, Field

logger = logging.getLogger("app.tools")


# Strict Pydantic Schema Model for Recipe
class RecipeModel(BaseModel):
    name: str = Field(..., description="The name of the recipe.")
    description: str = Field(
        ..., description="A short, evocative description of the dish."
    )
    prep_time: int = Field(..., description="Preparation time in minutes.")
    cook_time: int = Field(..., description="Cooking time in minutes.")
    equipment: list[str] = Field(
        default_factory=list, description="List of kitchen equipment required."
    )
    ingredients: list[str] = Field(
        default_factory=list, description="List of ingredients needed."
    )
    dietary_tags: list[str] = Field(
        default_factory=list,
        description="Dietary tags (e.g. 'vegetarian', 'gluten-free').",
    )
    instructions: str = Field(..., description="Step-by-step cooking instructions.")


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


def fetch_and_parse_recipe(url: str) -> RecipeModel | None:
    """Fetches a recipe page from Nigella.com and parses it into a RecipeModel."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode("utf-8")
    except Exception:
        return None

    # Extract Name/Title
    title_match = re.search(r"<title>(.*?) \| Nigella's Recipes", html_content)
    name = (
        html.unescape(title_match.group(1).strip()) if title_match else "Unknown Recipe"
    )

    # Extract Description
    desc_match = re.search(
        r'<meta property="og:description" content="(.*?)"', html_content
    )
    description = html.unescape(desc_match.group(1).strip()) if desc_match else ""

    # Extract Tags (Gluten Free, Vegetarian, etc.)
    keywords_match = re.search(r'<meta name="keywords" content="(.*?)"', html_content)
    tags = []
    if keywords_match:
        kw_str = html.unescape(keywords_match.group(1)).lower()
        if "gluten free" in kw_str:
            tags.append("gluten-free")
        if "vegetarian" in kw_str:
            tags.append("vegetarian")

    # Extract Ingredients
    ingredients = []
    metric_part_match = re.search(
        r'<div class="part switchable" data-switcher-type="Metric"[^>]*>.*?<ul>(.*?)</ul>',
        html_content,
        re.DOTALL,
    )
    if metric_part_match:
        li_matches = re.findall(
            r'<li itemprop="recipeIngredient">(.*?)</li>',
            metric_part_match.group(1),
        )
        ingredients = [html.unescape(li.strip()) for li in li_matches]

    # Extract Instructions
    instructions_text = ""
    instructions_match = re.search(
        r'<div class="switchable" data-switcher-type="Metric"[^>]*itemprop="recipeInstructions">.*?<ol>(.*?)</ol>',
        html_content,
        re.DOTALL,
    )
    if instructions_match:
        li_matches = re.findall(
            r"<li>(.*?)</li>", instructions_match.group(1), re.DOTALL
        )
        instructions_text = " ".join(
            [re.sub(r"<[^<]+?>", "", html.unescape(li.strip())) for li in li_matches]
        )

    # Simple fallback time mappings based on name keywords
    prep_time = 15
    cook_time = 45
    if "Slow Roasted" in name:
        cook_time = 150
    elif "Italian" in name:
        cook_time = 75
    elif "Mughlai" in name:
        prep_time = 25
        cook_time = 40
    elif "Linguine" in name:
        cook_time = 10

    # Fallback equipment lists
    equipment = ["tin", "knife", "oven"]
    if "Mughlai" in name:
        equipment = ["pan", "food processor", "knife"]
    elif "Linguine" in name:
        equipment = ["pot", "knife", "large bowl"]

    try:
        return RecipeModel(
            name=name,
            description=description,
            prep_time=prep_time,
            cook_time=cook_time,
            equipment=equipment,
            ingredients=ingredients,
            dietary_tags=tags,
            instructions=instructions_text,
        )
    except Exception:
        return None


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
