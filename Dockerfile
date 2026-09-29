# Use a slim Python image
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . .

RUN uv pip install --system .

# Cloud Run default port
EXPOSE 8080

CMD ["google-ads-mcp"]
