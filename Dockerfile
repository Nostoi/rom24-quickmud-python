FROM python:3.11-slim

WORKDIR /app

COPY mud/pyproject.toml mud/poetry.lock ./mud/
RUN pip install --no-cache-dir poetry \
    && poetry -C mud config virtualenvs.create false \
    && poetry -C mud install --no-interaction --no-ansi

COPY . /app

CMD ["poetry", "-C", "mud", "run", "mud", "socketserver"]
