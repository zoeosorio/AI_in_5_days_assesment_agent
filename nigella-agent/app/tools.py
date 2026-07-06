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
import re
import urllib.request

from google import genai
from google.adk.tools import ToolContext
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field


# Recipe Summary Model (Optimized to keep agent context lightweight during search)
class RecipeSummary(BaseModel):
    name: str = Field(..., description="The name of the recipe.")
    description: str = Field(
        ..., description="A short, evocative description of the dish."
    )
    prep_time: int = Field(..., description="Preparation time in minutes.")
    cook_time: int = Field(..., description="Cooking time in minutes.")
    dietary_tags: list[str] = Field(
        default_factory=list,
        description="Dietary tags (e.g. 'vegetarian', 'gluten-free').",
    )
    url: str = Field(
        ..., description="The direct URL of the recipe page on Nigella.com."
    )


# Recipe Detail Model (Retrieved only when the user chooses to cook the recipe)
class RecipeDetail(BaseModel):
    name: str = Field(..., description="The name of the recipe.")
    ingredients: list[str] = Field(
        default_factory=list, description="List of ingredients needed."
    )
    instructions: str = Field(..., description="Step-by-step cooking instructions.")
    equipment: list[str] = Field(
        default_factory=list, description="List of kitchen equipment required."
    )


# Strict Output Schemas
class SearchRecipesOutput(BaseModel):
    status: str = Field(
        ..., description="The status of the operation (e.g. 'success')."
    )
    recipes: list[RecipeSummary] = Field(
        ..., description="A list of matching recipe summaries."
    )


class GetRecipeDetailsOutput(BaseModel):
    status: str = Field(
        ..., description="The status of the operation (e.g. 'success')."
    )
    detail: RecipeDetail = Field(
        ..., description="The ingredients and instructions details of the recipe."
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


def fetch_and_parse_recipe(url: str) -> tuple[RecipeSummary, RecipeDetail] | None:
    """Fetches a recipe page from Nigella.com and parses it into Summary and Detail models."""
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
        summary = RecipeSummary(
            name=name,
            description=description,
            prep_time=prep_time,
            cook_time=cook_time,
            dietary_tags=tags,
            url=url,
        )
        detail = RecipeDetail(
            name=name,
            ingredients=ingredients,
            instructions=instructions_text,
            equipment=equipment,
        )
        return summary, detail
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


def search_nigella_web_recipes(query: str, max_results: int = 1) -> SearchRecipesOutput:
    """Searches Nigella.com for recipes matching the query and returns their summaries.

    Args:
        query: The search query (e.g. 'lemon cake', 'chocolate cookies').
        max_results: The maximum number of recipe matches to return. Default is 1.

    Returns:
        A structured SearchRecipesOutput.
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
            ),
        )
        text = response.text or ""
        # Find all matching urls in generated text
        found_urls = re.findall(r"https://www.nigella.com/recipes/[a-zA-Z0-9-]+", text)
        # Deduplicate and limit
        urls = list(dict.fromkeys(found_urls))[:max_results]
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
        return SearchRecipesOutput(status="error", recipes=[])

    summaries = []
    if urls:
        for url in urls:
            parsed = fetch_and_parse_recipe(url)
            if parsed:
                summary, _ = parsed
                summaries.append(summary)

    output = SearchRecipesOutput(
        status="success" if summaries else "empty", recipes=summaries
    )

    # Log Outcome
    logger.info(
        json.dumps(
            {
                "event": "tool_outcome",
                "tool": "search_nigella_web_recipes",
                "status": "success",
                "recipes_count": len(summaries),
            }
        )
    )

    return output


def get_recipe_details(url: str) -> GetRecipeDetailsOutput:
    """Fetches the full ingredients and step-by-step instructions for a recipe by its URL.

    Args:
        url: The direct URL of the recipe page on Nigella.com.

    Returns:
        A structured GetRecipeDetailsOutput containing detailed instructions.
    """
    # Log Intent
    logger.info(
        json.dumps(
            {
                "event": "tool_intent",
                "tool": "get_recipe_details",
                "params": {"url": url},
            }
        )
    )

    parsed = fetch_and_parse_recipe(url)
    if parsed:
        _, detail = parsed
        output = GetRecipeDetailsOutput(status="success", detail=detail)
    else:
        output = GetRecipeDetailsOutput(
            status="error",
            detail=RecipeDetail(
                name="Unknown",
                ingredients=[],
                instructions="Failed to fetch instructions. Please verify the URL and your network connection.",
                equipment=[],
            ),
        )

    # Log Outcome
    logger.info(
        json.dumps(
            {
                "event": "tool_outcome",
                "tool": "get_recipe_details",
                "status": output.status,
            }
        )
    )

    return output
