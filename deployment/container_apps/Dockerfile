FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_ENVIRONMENT=dev \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_BACKEND_MODE=synthetic \
    MCP_AUTH_MODE=development

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

USER appuser
EXPOSE 8000
CMD ["python", "-m", "agent_harness.mcp_server.app"]
