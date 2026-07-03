# "What Would Nigella Do?" Cooking Assistant

This is an agentic cooking assistant that speaks in the warm, intimate, and celebrated voice of Nigella Lawson. It helps users decide what to cook tonight by searching a local database of favorites, dynamically importing new recipes from Nigella's website, and remembering user dietary preferences.

---

## 📂 Project Structure

```
nigella-agent/
├── app/
│   ├── agent.py         # Root Nigella agent & Sous Chef sub-agent configuration
│   ├── database.py      # SQLAlchemy DB schema, parser, and SQLite helper operations
│   ├── tools.py         # Exposed ADK tools (recipe query, session state preferences)
│   ├── fast_api_app.py  # FastAPI backend server
│   └── app_utils/       # App utilities and session lifecycle hooks
├── tests/               # Unit, integration, and evaluation suites
├── AGENTS.md            # Comprehensive developer and architecture guide
└── pyproject.toml       # Project configuration and package dependencies
```

> 💡 **Tip:** Detailed architectural patterns, Pydantic/SQLAlchemy schemas, and developer workflows are fully documented in [AGENTS.md](file:///usr/local/google/home/zoeo/Projects/jetski-cli-projects/AI_in_5_days_assesment_agent/nigella-agent/AGENTS.md).

---

## 🚀 Key Features

* **Warm, Sensuous Voice**: Captures Nigella Lawson's unique personality using LLM-as-judge voice fidelity testing.
* **Separation of Voice & Detail**: Uses an `AgentTool` multi-agent delegation structure so that the backend `sous_chef` processes raw data while Nigella remains in full control of the conversational persona.
* **Zero-Bloat Database**: No recipe text is committed to the repository. The SQLite database is created and seeded dynamically on first import by scraping recipe pages directly from Nigella.com.
* **Dynamic Search & Ingestion**: The agent can search Nigella.com using Google Search grounding, extract, parse, validate (via Pydantic), and insert new recipes into SQLite at runtime.
* **Persistent Session State**: Remembers user dietary restrictions across multiple turns using shared session memory.

---

## 🛠️ Getting Started

### 1. Installation
Install the project dependencies and the development tools:
```bash
# Setup CLI environment
uvx google-agents-cli setup

# Install packages
agents-cli install
```

### 2. Run the Playground
Launch the interactive web UI to test and converse with Nigella:
```bash
agents-cli playground
```

### 3. Run Quality Evaluations
Run the local LLM-as-judge evaluation dataset (compares response quality and voice fidelity):
```bash
agents-cli eval run
```

---

## 🧪 Testing

Execute the test suites locally using pytest:
```bash
uv run pytest
```
* **Unit Tests**: Test tools, database operations, and state variables in isolation.
* **Integration Tests**: Verify end-to-end multi-agent messaging flow (requires a valid `GEMINI_API_KEY` or active Google Cloud CLI ADC credentials).
