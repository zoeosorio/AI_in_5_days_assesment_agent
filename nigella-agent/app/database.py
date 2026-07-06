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
import re
import urllib.request

from google.cloud import firestore
from pydantic import BaseModel, Field

RECIPE_URLS = [
    "https://www.nigella.com/recipes/slow-roasted-garlic-and-lemon-chicken",
    "https://www.nigella.com/recipes/italian-roast-chicken-with-peppers-and-olives",
    "https://www.nigella.com/recipes/mughlai-chicken",
    "https://www.nigella.com/recipes/linguine-with-lemon-garlic-and-thyme-mushrooms",
]


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


# Initialize Firestore client (synchronous for tools execution compatibility)
db = firestore.Client()


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


def init_db() -> None:
    """Initializes the Firestore database and dynamically seeds recipes if the collection is empty."""
    try:
        recipes_ref = db.collection("recipes")
        docs = list(recipes_ref.limit(1).stream())
        if not docs:
            print("Database empty, seeding 4 recipes from Nigella.com...")
            for url in RECIPE_URLS:
                recipe = fetch_and_parse_recipe(url)
                if recipe:
                    insert_recipe(recipe)
    except Exception as e:
        print(f"Error seeding Firestore: {e}")


def query_recipes_db(
    query: str | None = None,
    max_prep_time: int | None = None,
    max_cook_time: int | None = None,
) -> list[RecipeModel]:
    """Queries Firestore and returns matching RecipeModel list."""
    try:
        ref = db.collection("recipes")
        if max_prep_time is not None:
            ref = ref.where(
                filter=firestore.FieldFilter("prep_time", "<=", max_prep_time)
            )
        if max_cook_time is not None:
            ref = ref.where(
                filter=firestore.FieldFilter("cook_time", "<=", max_cook_time)
            )

        docs = ref.stream()
        recipes = []
        for doc in docs:
            data = doc.to_dict()
            recipe = RecipeModel(**data)
            if query:
                q = query.lower()
                if q not in recipe.name.lower() and q not in recipe.description.lower():
                    continue
            recipes.append(recipe)
        return recipes
    except Exception as e:
        print(f"Error querying Firestore: {e}")
        return []


def insert_recipe(recipe: RecipeModel) -> bool:
    """Inserts a single RecipeModel into Firestore recipes collection. Returns True if successful."""
    try:
        # Create a document ID based on lowercase recipe name to prevent duplicates
        doc_id = re.sub(r"[^a-zA-Z0-9]+", "-", recipe.name.lower()).strip("-")
        doc_ref = db.collection("recipes").document(doc_id)
        doc_ref.set(recipe.model_dump())
        return True
    except Exception as e:
        print(f"Error inserting into Firestore: {e}")
        return False


# Seeding database
init_db()
