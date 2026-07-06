# "What Would Nigella Do?" Cooking Assistant

This is an agentic cooking assistant that speaks in the warm, intimate, and celebrated voice of Nigella Lawson. It helps users decide what to cook tonight by dynamically searching and parsing recipes directly from Nigella.com, all while remembering user dietary preferences.

---

## 📂 Project Structure

```
nigella-agent/
├── app/
│   ├── agent.py         # Root Nigella agent & Sous Chef sub-agent configuration
│   └── tools.py         # Exposed ADK tools (web scraper, preferences store)
├── tests/               # Unit, integration, and evaluation suites
├── AGENTS.md            # Comprehensive developer and architecture guide
└── pyproject.toml       # Project configuration and package dependencies
```

> 💡 **Tip:** Detailed architectural patterns, Pydantic validation schemas, and developer workflows are fully documented in [AGENTS.md](file:///usr/local/google/home/zoeo/Projects/jetski-cli-projects/AI_in_5_days_assesment_agent/nigella-agent/AGENTS.md).

---

## 🚀 Key Features

* **Warm, Sensuous Voice**: Captures Nigella Lawson's unique personality using LLM-as-judge voice fidelity testing.
* **Separation of Voice & Detail**: Uses an `AgentTool` multi-agent delegation structure so that the backend `sous_chef` processes raw data while Nigella remains in full control of the conversational persona.
* **Zero-Repository Bloat**: No recipe content or databases are stored locally or in the repository. All recipes are dynamically fetched, parsed, and validated in memory using Pydantic at query runtime.
* **Conversational Human-in-the-Loop**: Nigella uses the built-in `request_input` tool to ask the user to clarify or confirm their dietary preferences whenever they are unspecified or unsure before suggesting recipes.
* **Dynamic Search & Ingestion**: The agent searches Nigella.com using Google Search grounding, extracts and parses matching recipe pages, and validates them (via Pydantic) at runtime.
* **Persistent Session State**: Remembers user dietary restrictions across multiple turns using shared session state.

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
Launch the interactive native ADK web UI to test and converse with Nigella:
```bash
agents-cli playground
```

### 3. Run the CLI Debugger
Query the agent directly from the command line using a single prompt:
```bash
# Run initial request (starts a background server for session tracking)
agents-cli run "Hi Nigella, could you recommend a slow roasted chicken recipe?"

# Resume/Continue the conversation using session ID
agents-cli run "No, I don't have any dietary restrictions" --session-id <session_id>
```

### 4. Run Quality Evaluations
Run the local LLM-as-judge evaluation dataset (compares response quality and voice fidelity):
```bash
agents-cli eval run
```

### 5. Deployment & Production Setup
The assistant is packaged for containerized deployment on **Vertex AI Agent Runtime (Reasoning Engine)**:

* **Production Server**: The container executes the native ADK API server running with the `--a2a` protocol enabled:
  ```bash
  adk api_server --port=8080 --host=0.0.0.0 --a2a --gemini_enterprise_app_name=app app
  ```
* **Managed Session Persistence**: Uses `agentengine://` (Vertex AI's managed database backend) to automatically persist user preferences between separate runs.
* **Distributed Tracing & Structured Logging**: Traces and metrics are automatically instrumented and exported directly to Google Cloud Trace and Cloud Logging using the `--otel_to_cloud` flag.
* **Asynchronous Operations**: Decouples heavy memory operations from user response latency using the `AsyncMemoryBackupPlugin` to back up states in a non-blocking `asyncio.create_task` thread.

To deploy the agent to your Google Cloud Project:
```bash
make deploy PROJECT_ID=YOUR_PROJECT_ID
```

---

## 🧪 Testing


Execute the test suites locally using pytest:
```bash
uv run pytest
```
