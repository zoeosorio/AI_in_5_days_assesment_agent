# "What Would Nigella Do?" Agent - Developer Guide

Welcome to the culinary assistant codebase. This guide details the architecture, data models, tools, and operational workflows of our multi-agent cooking assistant.

---

## 🍽️ Agent Architecture

The agent is designed as a ReAct multi-agent hierarchy to preserve the strict persona of Nigella Lawson while delegating data-intensive operations to a precise specialist.

```mermaid
graph TD
    User([User]) <--> Root[Nigella Voice Agent (Root)]
    Root <--> |AgentTool| SousChef[Sous Chef Agent]
    SousChef <--> Web[Nigella.com / Google Search]
```

### 1. Nigella Voice Agent (Root)
* **Role**: The warm, intimate, and celebrated home cook.
* **Persona**: Speak in a highly descriptive, sensuous, and comforting voice using Nigella's signature culinary terms ('luscious', 'glorious', 'velvety').
* **Responsibility**: Manages direct user interaction, stores/retrieves user dietary preferences, and wraps all recipe suggestions in Nigella's voice.
* **Tools**: `google_search` (web grounding), `set_user_preferences`, `get_user_preferences`, `request_input`, `AgentTool(sous_chef)`.

### 2. Sous Chef Agent (Sub-agent)
* **Role**: Precise, detail-oriented backend assistant.
* **Responsibility**: Queries Nigella.com directly and performs web scraping of recipe pages.
* **Tools**: `search_nigella_web_recipes`.

---

## 💾 Data Architecture & Schema

To prevent bloat and keep the system lightweight, we do not store recipe documents in a persistent database catalog. Instead, recipe payloads scraped dynamically from Nigella.com are parsed and validated in memory using Pydantic.

### Recipe Document Schema

Scraped recipes are validated against the following schema:

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
No recipe data is hardcoded or committed to the repository. The agent fetches and parses recipe content dynamically from Nigella.com at query runtime.

### 2. Search Tool (`search_nigella_web_recipes`)
Exposed to the `sous_chef`, this tool allows the agent to dynamically search for recipes on Nigella.com using Google Search grounding, download the HTML, parse out ingredients and instructions, validate them using the `RecipeModel` Pydantic class, and return them to the agent.

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
