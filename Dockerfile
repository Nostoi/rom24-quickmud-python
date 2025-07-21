FROM python:3.11-slim

WORKDIR /app

# Disable Poetry's virtualenv creation so everything installs into the
# container's Python environment.
ENV POETRY_VIRTUALENVS_CREATE=false

# Install Poetry and project dependencies from the mud directory.
RUN pip install --no-cache-dir poetry
COPY mud/pyproject.toml mud/pyproject.toml
RUN poetry -C mud install --no-interaction --no-ansi --no-root

# Copy the rest of the repository
COPY . .

# Install the quickmud package itself so the "mud" entry point is available.
# Poetry cannot discover the package because the project name differs from the
# package directory, so we provide our own setup.py.
COPY setup.py ./
RUN pip install -e .

CMD ["mud", "socketserver"]
