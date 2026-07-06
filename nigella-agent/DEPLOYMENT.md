# 🚀 Deploying to Google Cloud Platform

This guide outlines the steps to deploy the "What Would Nigella Do?" cooking assistant agent to Vertex AI Agent Runtime (formerly Reasoning Engine) on Google Cloud.

---

## 📋 Prerequisites

Before deploying, ensure you have the following CLI tools installed:
1. [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install)
2. [uv](https://docs.astral.sh/uv/getting-started/installation/) (fast Python package installer)
3. `agents-cli` (installed via `make setup`)

---

## 🔐 Authentication Setup

To authorize deployment and runtime calls to Vertex AI, set up your Application Default Credentials (ADC) locally:

```bash
# Log in with your user credentials
gcloud auth login

# Configure application credentials for API client libraries (like Vertex AI)
gcloud auth application-default login
```

---

## 🛠️ Provision Infrastructure via Terraform

We use Terraform to automatically enable the required Google Cloud APIs (Vertex AI, Logging, Cloud Trace), create a dedicated Service Account for the agent (`nigella-agent-sa`), and configure all necessary IAM permissions.

1. **Initialize Terraform**:
   ```bash
   make tf-init
   ```

2. **Provision Resources**:
   Apply the configuration to your project:
   ```bash
   make tf-apply PROJECT_ID=your-gcp-project-id [REGION=us-east1]
   ```

---


## 💾 Using Vertex AI Session Service Locally

By default, running the standard `make playground` command uses in-memory session storage (preferences are lost when the process exits).

To test persistent user preferences locally across playground and command line restarts, you can run the playground connected directly to Vertex AI's managed Session Service. Ensure you have completed the **Authentication Setup** and **Enable APIs** sections above, then run:

```bash
# Start playground connected to Vertex AI Session Service
make playground-persist PROJECT_ID=your-gcp-project-id [REGION=us-central1]
```

This configures the ADK runner via the environment variable `SESSION_SERVICE_URI=agentengine://YOUR_PROJECT_ID/YOUR_REGION`. All user preference settings and conversation histories will be saved in Google Cloud's managed session storage.

---

## 🚀 Deployment Steps


You can deploy the agent using the provided `Makefile`:

```bash
# Run the deployment target command
make deploy PROJECT_ID=your-gcp-project-id [REGION=us-central1]
```

### Under the Hood
This triggers the native ADK deployment command:
```bash
GOOGLE_GENAI_USE_VERTEXAI=True agents-cli deploy \
  --project your-gcp-project-id \
  --region us-central1 \
  --no-confirm-project
```

The command packages your local agent code inside `app/`, creates a zipped bundle, uploads it, and registers a Reasoning Engine instance in Vertex AI. The deployment usually takes **2–5 minutes**.

---

## 🧪 Testing the Deployed Agent

Once deployed, the command will output your Reasoning Engine Resource ID. You can query your remote agent directly from the command line using `agents-cli run`:

```bash
# Query the deployed agent remotely
agents-cli run \
  --url "https://us-central1-aiplatform.googleapis.com/v1/projects/YOUR_PROJECT_ID/locations/us-central1/reasoningEngines/YOUR_RESOURCE_ID" \
  --mode adk \
  "Hi Nigella, what should I cook tonight?"
```

---

## 📊 Observability & Distributed Tracing

This ADK agent includes built-in OpenTelemetry instrumentation and structured logging:

### 1. Cloud Trace (Distributed Tracing)
* **Vertex AI Reasoning Engine**: Distributed tracing is automatically configured and enabled when you deploy. Execution flows (agent runs, LLM calls, and tool calls) are exported as OpenTelemetry spans directly to GCP Cloud Trace.
* **Local Testing**: To export traces to Cloud Trace when executing commands locally, add the `--trace-to-cloud` flag to the run command:
  ```bash
  GOOGLE_GENAI_USE_VERTEXAI=True agents-cli run "Hi Nigella, what should I cook tonight?" --trace-to-cloud
  ```

### 2. Structured Cloud Logging
Standard Python logs output to `stdout` are automatically captured by GCP and routed to Cloud Logging.

To check runtime logs or trace errors:
1. Open the [GCP Console Log Explorer](https://console.cloud.google.com/logs).
2. Go to **Logging > Logs Explorer**.
3. Filter by the resource type `Vertex AI Reasoning Engine` (or search for logs matching your project id).
4. For trace details, view the [GCP Trace Explorer](https://console.cloud.google.com/gcloud/trace) to inspect latencies and span call trees.
