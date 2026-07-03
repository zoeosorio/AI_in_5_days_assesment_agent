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


from google.adk.tools import ToolContext

# A rich, illustrative recipe dataset in the spirit of Nigella Lawson
RECIPES: list[dict] = [
    {
        "name": "Luscious Chocolate Guinness Cake",
        "description": "A dark, damp, and altogether magnificent chocolate cake, topped with a thick, cloud-like cream cheese frosting to resemble a pint of the black stuff.",
        "prep_time": 20,
        "cook_time": 45,
        "equipment": ["springform tin", "saucepan", "whisk", "bowl"],
        "ingredients": [
            "250ml Guinness",
            "250g unsalted butter",
            "75g cocoa powder",
            "400g caster sugar",
            "150ml sour cream",
            "2 large eggs",
            "1 tablespoon vanilla extract",
            "275g plain flour",
            "2.5 teaspoons bicarbonate of soda",
        ],
        "dietary_tags": ["vegetarian"],
        "instructions": "Melt butter in Guinness in a saucepan. Whisk in cocoa and sugar. Beat sour cream with eggs and vanilla, then pour into the pan. Whisk in flour and bicarb. Bake at 180°C for 45 minutes. Top with sweetened cream cheese frosting once cool.",
    },
    {
        "name": "Cosy Lemon Garlic Chicken",
        "description": "A comforting, fragrant traybake. The chicken thighs become crisp-skinned and tender, bathed in sweet lemon juice, aromatic rosemary, and caramelized garlic cloves.",
        "prep_time": 15,
        "cook_time": 50,
        "equipment": ["roasting tin", "knife", "cutting board"],
        "ingredients": [
            "4 chicken thighs (skin-on, bone-in)",
            "2 lemons (quartered)",
            "500g new potatoes (halved)",
            "1 head of garlic (cloves separated, unpeeled)",
            "2 tablespoons olive oil",
            "3 sprigs of fresh rosemary",
            "salt and pepper",
        ],
        "dietary_tags": ["gluten-free"],
        "instructions": "Toss potatoes and garlic cloves in olive oil, salt, and pepper in a roasting tin. Nestle the chicken thighs and lemon quarters among them. Scatter rosemary sprigs on top. Roast at 200°C for 50 minutes until chicken is golden and crispy.",
    },
    {
        "name": "Divine Tomato and Mozzarella Pasta Bake",
        "description": "A gooey, bubbly pasta bake that smells of garlic and fresh basil. It is pure, warm, carbohydrate comfort.",
        "prep_time": 15,
        "cook_time": 30,
        "equipment": ["large pot", "colander", "ovenproof dish"],
        "ingredients": [
            "300g penne pasta",
            "500g tomato passata",
            "2 cloves of garlic (minced)",
            "2 tablespoons olive oil",
            "125g fresh mozzarella (sliced or torn)",
            "50g grated parmesan cheese",
            "1 bunch of fresh basil leaves",
        ],
        "dietary_tags": ["vegetarian"],
        "instructions": "Cook penne until al dente. Warm passata with olive oil, minced garlic, and salt in a pan. Mix pasta with sauce and half the basil. Transfer to an ovenproof dish. Top with mozzarella and parmesan. Bake at 200°C for 30 minutes until bubbling.",
    },
]


def get_recipes(
    query: str | None = None,
    max_prep_time: int | None = None,
    max_cook_time: int | None = None,
    dietary_restrictions: list[str] | None = None,
    tool_context: ToolContext | None = None,
) -> dict:
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

    results = []
    for recipe in RECIPES:
        # Check query match
        if query:
            q = query.lower()
            if (
                q not in recipe["name"].lower()
                and q not in recipe["description"].lower()
            ):
                continue

        # Check prep time
        if max_prep_time is not None and recipe["prep_time"] > max_prep_time:
            continue

        # Check cook time
        if max_cook_time is not None and recipe["cook_time"] > max_cook_time:
            continue

        # Check dietary restrictions match (all active restrictions must be met by recipe tags)
        # Note: If a user is vegetarian, the recipe must have the "vegetarian" tag.
        # If a user is gluten-free, the recipe must have "gluten-free".
        tags = [t.lower() for t in recipe["dietary_tags"]]
        match_failed = False
        for restriction in active_restrictions:
            if restriction not in tags:
                match_failed = True
                break
        if match_failed:
            continue

        results.append(recipe)

    return {"status": "success", "recipes": results}


def set_user_preferences(
    dietary_restrictions: list[str], tool_context: ToolContext
) -> dict:
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


def get_user_preferences(tool_context: ToolContext) -> dict:
    """Retrieves the user's saved dietary preferences.

    Returns:
        A dictionary with user dietary restrictions.
    """
    prefs = tool_context.state.get("user:dietary_restrictions", [])
    return {"status": "success", "dietary_restrictions": prefs}
