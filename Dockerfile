FROM python:3.11-slim

WORKDIR /app

# Copy project metadata first for better layer caching
COPY mud/pyproject.toml /app/mud/pyproject.toml

# Copy the mud package including a lock file if present
COPY mud/ /app/mud/

# Install Poetry and project dependencies. If no lock file is
# present, generate one during the build.
RUN pip install --no-cache-dir poetry \
    && if [ ! -f /app/mud/poetry.lock ]; then \
         poetry -C /app/mud lock; \
       fi \
    && poetry -C /app/mud install --no-interaction --no-ansi

# Copy the rest of the repository
COPY . /app

CMD ["poetry", "run", "mud", "socketserver"]
