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
import os
import re
import sqlite3
import urllib.request
from typing import Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipes.db")

RECIPE_URLS = [
    "https://www.nigella.com/recipes/slow-roasted-garlic-and-lemon-chicken",
    "https://www.nigella.com/recipes/italian-roast-chicken-with-peppers-and-olives",
    "https://www.nigella.com/recipes/mughlai-chicken",
    "https://www.nigella.com/recipes/linguine-with-lemon-garlic-and-thyme-mushrooms",
]


def fetch_and_parse_recipe(url: str) -> dict[str, Any] | None:
    """Fetches a recipe page from Nigella.com and parses it into a dictionary."""
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

    # Extract Ingredients (Metric list is inside switcher)
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

    # Extract Instructions (Metric)
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

    return {
        "name": name,
        "description": description,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "equipment": equipment,
        "ingredients": ingredients,
        "dietary_tags": tags,
        "instructions": instructions_text,
    }


def init_db() -> None:
    """Initializes the SQLite database and dynamically seeds recipes from Nigella.com."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            prep_time INTEGER,
            cook_time INTEGER,
            equipment TEXT,
            ingredients TEXT,
            dietary_tags TEXT,
            instructions TEXT
        )
    """)

    # Check if database is already seeded
    cursor.execute("SELECT COUNT(*) FROM recipes")
    if cursor.fetchone()[0] == 0:
        for url in RECIPE_URLS:
            recipe = fetch_and_parse_recipe(url)
            if recipe:
                try:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO recipes
                        (name, description, prep_time, cook_time, equipment, ingredients, dietary_tags, instructions)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            recipe["name"],
                            recipe["description"],
                            recipe["prep_time"],
                            recipe["cook_time"],
                            json.dumps(recipe["equipment"]),
                            json.dumps(recipe["ingredients"]),
                            json.dumps(recipe["dietary_tags"]),
                            recipe["instructions"],
                        ),
                    )
                except sqlite3.Error:
                    pass
    conn.commit()
    conn.close()


def get_all_recipes() -> list[dict[str, Any]]:
    """Retrieves all recipes from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, description, prep_time, cook_time, equipment, ingredients, dietary_tags, instructions FROM recipes"
    )
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append(
            {
                "name": row[0],
                "description": row[1],
                "prep_time": row[2],
                "cook_time": row[3],
                "equipment": json.loads(row[4]),
                "ingredients": json.loads(row[5]),
                "dietary_tags": json.loads(row[6]),
                "instructions": row[7],
            }
        )
    return results


def insert_recipe(recipe: dict[str, Any]) -> bool:
    """Inserts a single recipe into the database. Returns True if inserted, False otherwise."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    success = False
    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO recipes
            (name, description, prep_time, cook_time, equipment, ingredients, dietary_tags, instructions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                recipe["name"],
                recipe["description"],
                recipe["prep_time"],
                recipe["cook_time"],
                json.dumps(recipe["equipment"]),
                json.dumps(recipe["ingredients"]),
                json.dumps(recipe["dietary_tags"]),
                recipe["instructions"],
            ),
        )
        if cursor.rowcount > 0:
            success = True
    except sqlite3.Error:
        pass
    conn.commit()
    conn.close()
    return success


# Run DB initialization when module is imported
init_db()
