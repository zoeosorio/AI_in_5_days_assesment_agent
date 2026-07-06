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

import math
import re

from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from pydantic import BaseModel, Field


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
    embedding: list[float] = Field(
        default_factory=list,
        description="768-dimension vector embedding of the recipe name and description.",
    )


# Initialize Firestore Client
db = firestore.Client()


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    dot_product = sum(x * y for x, y in zip(v1, v2, strict=True))
    magnitude1 = math.sqrt(sum(x * x for x in v1))
    magnitude2 = math.sqrt(sum(y * y for y in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)


def query_recipes_db(
    query_vector: list[float] | None = None,
    max_prep_time: int | None = None,
    max_cook_time: int | None = None,
) -> list[RecipeModel]:
    """Queries Firestore using vector similarity search with a local cosine fallback."""
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

        if query_vector:
            try:
                # Native Firestore Vector Search (Requires vector index on 'embedding')
                vector_query = ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_vector),
                    distance_measure=DistanceMeasure.COSINE,
                    limit=5,
                )
                docs = vector_query.stream()
                return [RecipeModel(**doc.to_dict()) for doc in docs]
            except Exception as ve:
                # Fallback to local Python cosine similarity
                print(
                    f"Warning: Firestore vector index query failed ({ve}). Falling back to local cosine calculation."
                )
                docs = ref.stream()
                candidate_recipes = []
                for doc in docs:
                    data = doc.to_dict()
                    recipe = RecipeModel(**data)
                    if recipe.embedding:
                        similarity = _cosine_similarity(recipe.embedding, query_vector)
                        candidate_recipes.append((similarity, recipe))
                # Sort candidates by similarity descending
                candidate_recipes.sort(key=lambda x: x[0], reverse=True)
                return [recipe for sim, recipe in candidate_recipes[:5]]

        # Fallback to standard query if no query vector
        docs = ref.stream()
        return [RecipeModel(**doc.to_dict()) for doc in docs]
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
