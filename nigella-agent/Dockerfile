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

FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# Copy dependency files
COPY pyproject.toml README.md uv.lock* ./
COPY app ./app

# Install dependencies using uv sync
RUN uv sync --frozen --no-dev

# Expose port (Reasoning Engine runtime passes PORT env var)
EXPOSE 8080

# Start the ADK API server with A2A enabled
CMD ["uv", "run", "adk", "api_server", "--port", "8080", "--host", "0.0.0.0", "--a2a", "--gemini_enterprise_app_name=app", "app"]
