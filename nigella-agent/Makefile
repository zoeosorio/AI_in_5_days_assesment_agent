# Makefile for "What Would Nigella Do?" ADK Agent

.PHONY: setup lint test playground deploy

# 1. Setup local python virtualenv and install ADK dependencies
setup:
	uvx google-agents-cli setup
	agents-cli install

# 2. Run static analysis, code linting, and type checking
lint:
	agents-cli lint

# 3. Execute the unit test suite
test:
	uv run pytest

# 4. Start the interactive web playground to chat with Nigella locally
playground:
	GOOGLE_GENAI_USE_VERTEXAI=True agents-cli playground

# 5. Deploy the agent to Google Cloud Vertex AI Agent Runtime
# Usage: make deploy PROJECT_ID=your-gcp-project-id [REGION=us-central1]
deploy:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: PROJECT_ID is required."; \
		echo "Usage: make deploy PROJECT_ID=your-gcp-project-id [REGION=us-central1]"; \
		exit 1; \
	fi
	$(eval REGION ?= us-central1)
	@echo "Deploying to project $(PROJECT_ID) in region $(REGION)..."
	GOOGLE_GENAI_USE_VERTEXAI=True agents-cli deploy \
		--project $(PROJECT_ID) \
		--region $(REGION) \
		--no-confirm-project
