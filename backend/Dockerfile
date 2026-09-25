FROM python:3.11-slim AS base

WORKDIR /app

# Install dependencies for mysqlclient
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

# Migrations run on every start, so a clean volume boots to a working API.
ENTRYPOINT ["/app/entrypoint.sh"]

# No --reload here: hot reload is a development concern and lives in
# docker-compose.override.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Development image: the production one deliberately carries no test tooling,
# but installing pytest by hand into a running container loses it on the next
# rebuild. docker-compose.override.yml targets this stage.
FROM base AS dev

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
