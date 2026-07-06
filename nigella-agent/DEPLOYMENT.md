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

## 🛠️ Enable APIs

Ensure the Vertex AI and Logging APIs are enabled in your target GCP project:

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  logging.googleapis.com \
  --project=YOUR_PROJECT_ID
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

## 📊 Observability & Logs

To check runtime logs or trace errors:
1. Open the [Google Cloud Console](https://console.cloud.google.com).
2. Go to **Logging > Logs Explorer**.
3. Filter by the resource type `Vertex AI Reasoning Engine` (or search for trace logs matching your project id).
