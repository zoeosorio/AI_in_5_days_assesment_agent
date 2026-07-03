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
import urllib.request

from pydantic import BaseModel, Field
from sqlalchemy import (
    Integer,
    String,
    Text,
    and_,
    create_engine,
    or_,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipes.db")

RECIPE_URLS = [
    "https://www.nigella.com/recipes/slow-roasted-garlic-and-lemon-chicken",
    "https://www.nigella.com/recipes/italian-roast-chicken-with-peppers-and-olives",
    "https://www.nigella.com/recipes/mughlai-chicken",
    "https://www.nigella.com/recipes/linguine-with-lemon-garlic-and-thyme-mushrooms",
]


# Pydantic Schema Model
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


# SQLAlchemy Configuration
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    prep_time: Mapped[int] = mapped_column(Integer, nullable=False)
    cook_time: Mapped[int] = mapped_column(Integer, nullable=False)
    equipment: Mapped[str] = mapped_column(Text, nullable=False)
    ingredients: Mapped[str] = mapped_column(Text, nullable=False)
    dietary_tags: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)


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
    """Initializes the SQLite database and dynamically seeds recipes from Nigella.com."""
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        count = session.query(Recipe).count()
        if count == 0:
            for url in RECIPE_URLS:
                recipe = fetch_and_parse_recipe(url)
                if recipe:
                    try:
                        db_recipe = Recipe(
                            name=recipe.name,
                            description=recipe.description,
                            prep_time=recipe.prep_time,
                            cook_time=recipe.cook_time,
                            equipment=json.dumps(recipe.equipment),
                            ingredients=json.dumps(recipe.ingredients),
                            dietary_tags=json.dumps(recipe.dietary_tags),
                            instructions=recipe.instructions,
                        )
                        session.add(db_recipe)
                    except Exception:
                        pass
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def query_recipes_db(
    query: str | None = None,
    max_prep_time: int | None = None,
    max_cook_time: int | None = None,
) -> list[RecipeModel]:
    """Queries the SQLite database using SQLAlchemy and returns matching RecipeModel list."""
    session = SessionLocal()
    try:
        stmt = select(Recipe)
        conditions = []
        if query:
            q = f"%{query}%"
            conditions.append(or_(Recipe.name.like(q), Recipe.description.like(q)))
        if max_prep_time is not None:
            conditions.append(Recipe.prep_time <= max_prep_time)
        if max_cook_time is not None:
            conditions.append(Recipe.cook_time <= max_cook_time)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        results = session.execute(stmt).scalars().all()

        recipes = []
        for r in results:
            recipes.append(
                RecipeModel(
                    name=r.name,
                    description=r.description,
                    prep_time=r.prep_time,
                    cook_time=r.cook_time,
                    equipment=json.loads(r.equipment),
                    ingredients=json.loads(r.ingredients),
                    dietary_tags=json.loads(r.dietary_tags),
                    instructions=r.instructions,
                )
            )
        return recipes
    finally:
        session.close()


def insert_recipe(recipe: RecipeModel) -> bool:
    """Inserts a single RecipeModel into the database. Returns True if inserted, False otherwise."""
    session = SessionLocal()
    success = False
    try:
        db_recipe = Recipe(
            name=recipe.name,
            description=recipe.description,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            equipment=json.dumps(recipe.equipment),
            ingredients=json.dumps(recipe.ingredients),
            dietary_tags=json.dumps(recipe.dietary_tags),
            instructions=recipe.instructions,
        )
        session.add(db_recipe)
        session.commit()
        if db_recipe.id is not None:
            success = True
    except Exception:
        session.rollback()
    finally:
        session.close()
    return success


# Run DB initialization when module is imported
init_db()
