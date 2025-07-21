FROM python:3.11-slim

WORKDIR /app

# Disable Poetry's virtualenv creation so everything installs into the
# container's Python environment.
ENV POETRY_VIRTUALENVS_CREATE=false

# Install Poetry and project dependencies from the mud directory.
RUN pip install --no-cache-dir poetry
COPY mud/pyproject.toml mud/pyproject.toml
RUN poetry -C mud install --no-interaction --no-ansi --no-root

# Copy only the source and setup script first so the package installs
# correctly even when the build context is not the repository root.
COPY setup.py ./
COPY mud/ mud/
RUN pip install .

# Copy the rest of the repository (areas, docs, etc.).
COPY . .

CMD ["mud", "socketserver"]
