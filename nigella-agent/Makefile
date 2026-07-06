# Makefile for "What Would Nigella Do?" ADK Agent

.PHONY: setup lint test playground playground-persist deploy tf-init tf-apply teardown

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

# 4. Initialize Terraform infrastructure configuration
tf-init:
	terraform init

# 5. Provision all required GCP resources using Terraform
# Usage: make tf-apply PROJECT_ID=your-gcp-project-id [REGION=us-east1]
tf-apply:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: PROJECT_ID is required."; \
		echo "Usage: make tf-apply PROJECT_ID=your-gcp-project-id [REGION=us-east1]"; \
		exit 1; \
	fi
	$(eval REGION ?= us-east1)
	terraform apply -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)" -auto-approve

# 6. Start the interactive web playground to chat with Nigella locally (in-memory sessions)
playground:
	GOOGLE_GENAI_USE_VERTEXAI=True agents-cli playground

# 7. Start the interactive web playground using Vertex AI Session Service (persistent preferences)
# Usage: make playground-persist PROJECT_ID=your-gcp-project-id [REGION=us-central1]
playground-persist:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: PROJECT_ID is required."; \
		echo "Usage: make playground-persist PROJECT_ID=your-gcp-project-id [REGION=us-central1]"; \
		exit 1; \
	fi
	$(eval REGION ?= us-central1)
	GOOGLE_GENAI_USE_VERTEXAI=True \
	SESSION_SERVICE_URI=agentengine://$(PROJECT_ID)/$(REGION) \
	agents-cli playground

# 8. Deploy the agent to Google Cloud Vertex AI Agent Runtime
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

# 9. Clean up all deployed cloud resources (Reasoning Engine instance & Terraform resources)
# Usage: make teardown PROJECT_ID=your-gcp-project-id
teardown:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: PROJECT_ID is required."; \
		echo "Usage: make teardown PROJECT_ID=your-gcp-project-id"; \
		exit 1; \
	fi
	@if [ -f deployment_metadata.json ]; then \
		RESOURCE_ID=$$(jq -r '.remote_agent_runtime_id' deployment_metadata.json | awk -F'/' '{print $$NF}'); \
		echo "Deleting Reasoning Engine $$RESOURCE_ID in $(PROJECT_ID)..."; \
		curl -X DELETE \
			-H "Authorization: Bearer $$(gcloud auth print-access-token)" \
			-H "Content-Type: application/json" \
			"https://us-central1-aiplatform.googleapis.com/v1/projects/$(PROJECT_ID)/locations/us-central1/reasoningEngines/$$RESOURCE_ID"; \
		rm -f deployment_metadata.json; \
	else \
		echo "No deployment_metadata.json found. Skipping Reasoning Engine deletion."; \
	fi
	@echo "Destroying Terraform infrastructure..."
	terraform destroy -var="project_id=$(PROJECT_ID)" -auto-approve

