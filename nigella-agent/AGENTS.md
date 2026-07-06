# "What Would Nigella Do?" Agent - Developer Guide

Welcome to the culinary assistant codebase. This guide details the architecture, data models, tools, and operational workflows of our multi-agent cooking assistant.

---

## 🍽️ Agent Architecture

The agent is designed as a ReAct multi-agent hierarchy to preserve the strict persona of Nigella Lawson while delegating data-intensive operations to a precise specialist.

```mermaid
graph TD
    User([User]) <--> Root[Nigella Voice Agent (Root)]
    Root <--> |AgentTool| SousChef[Sous Chef Agent]
    SousChef <--> DB[(Google Cloud Firestore)]
    SousChef <--> Web[Nigella.com / Google Search]
```

### 1. Nigella Voice Agent (Root)
* **Role**: The warm, intimate, and celebrated home cook.
* **Persona**: Speak in a highly descriptive, sensuous, and comforting voice using Nigella's signature culinary terms ('luscious', 'glorious', 'velvety').
* **Responsibility**: Manages direct user interaction, stores/retrieves user dietary preferences, and wraps all recipe suggestions in Nigella's voice.
* **Tools**: `google_search` (web grounding), `set_user_preferences`, `get_user_preferences`, `AgentTool(sous_chef)`.

### 2. Sous Chef Agent (Sub-agent)
* **Role**: Precise, detail-oriented backend assistant.
* **Responsibility**: Queries the recipe database and performs dynamic web scraping of recipe pages.
* **Tools**: `get_recipes`, `search_and_add_recipes`.

---

## 💾 Data Architecture & Schema

We use **Google Cloud Firestore** as a serverless database to store session history and the recipe catalog, and **Pydantic** to validate all parsed and imported recipe payloads.

### Recipe Document Schema

The recipe documents are stored in the `recipes` collection and contain the following fields:

| Field | Type | Description | Validation (Pydantic) |
|---|---|---|---|
| `name` | string | Unique recipe title | `name: str` |
| `description` | string | Short, sensory description | `description: str` |
| `prep_time` | integer | Prep duration in minutes | `prep_time: int` |
| `cook_time` | integer | Cook duration in minutes | `cook_time: int` |
| `equipment` | array | List of kitchen tools | `equipment: list[str]` |
| `ingredients` | array | List of ingredients | `ingredients: list[str]` |
| `dietary_tags` | array | List of tags (e.g., 'vegetarian') | `dietary_tags: list[str]` |
| `instructions` | string | Step-by-step instructions | `instructions: str` |

---

## 🔌 Core Capabilities & Custom Tools

### 1. Dynamic Web Ingestion
No recipe data is hardcoded or committed to the repository. On first startup, the Firestore collection `recipes` is dynamically seeded by scraping four recipes from Nigella.com.

### 2. Search & Import Tool (`search_and_add_recipes`)
Exposed to the `sous_chef`, this tool allows the agent to dynamically search for new recipes on Nigella.com using Google Search grounding, download the HTML, parse out ingredients and instructions, validate them using the `RecipeModel` Pydantic class, and save them directly to Google Cloud Firestore.

### 3. Session State Preference Store
User dietary preferences are persisted across turns using the `tool_context.state` dictionary.
* **Prefix**: Stored using the `user:dietary_restrictions` namespace.
* **Sharing**: Updated directly by Nigella's `set_user_preferences` tool and automatically read by the `sous_chef` during query filtering.

---

## 🛠️ Development & Quality Commands

### Running Unit & Integration Tests
Before deploying, verify the backend functionality:
```bash
uv run pytest
```
> [!NOTE]
> Integration tests require Google Cloud Application Default Credentials (ADC) or a valid `GEMINI_API_KEY` environment variable to execute live model runs.

### Linting & Formatting
Ensure code formatting and style guidelines are checked:
```bash
agents-cli lint
```

### Playground Testing
To chat with the agent interactively in your browser:
```bash
agents-cli playground
```

### Evaluation & Metrics
Run the local LLM-as-judge quality suite:
```bash
agents-cli eval run
```
This runs custom metrics configured in `tests/eval/eval_config.yaml`:
* `custom_response_quality`: Evaluates accuracy and recipe instruction coherence.
* `nigella_voice_fidelity`: Scores the response on how well it captures Nigella Lawson's sensory, intimate voice.
