# MCP container image

Build locally:

```bash
docker build -f deployment/container_apps/Dockerfile -t agent-harness-mcp:v1 .
```

Run the synthetic MCP service:

```bash
docker run --rm --name agent-harness-mcp -p 8000:8000 \
  -e MCP_ENVIRONMENT=dev -e MCP_HOST=0.0.0.0 -e MCP_PORT=8000 \
  -e MCP_BACKEND_MODE=synthetic -e MCP_AUTH_MODE=development \
  agent-harness-mcp:v1
```

Validate health and the client:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
python scripts/test_mcp_client.py
```

Publish after Azure CLI authentication:

```bash
az account show --output table
az acr build --registry acragentharnessdev \
  --image agent-harness-mcp:v1 --image agent-harness-mcp:dev \
  --file deployment/container_apps/Dockerfile .
az acr repository list --name acragentharnessdev --output table
az acr repository show-tags --name acragentharnessdev \
  --repository agent-harness-mcp --output table
```

The image contains no `.env`; use runtime environment injection or managed
identity/Key Vault references in a future Azure Container Apps deployment.

Published references:

```text
acragentharnessdev.azurecr.io/agent-harness-mcp:v1
acragentharnessdev.azurecr.io/agent-harness-mcp:dev
```
