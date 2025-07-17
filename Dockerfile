FROM python:3.11-slim

WORKDIR /app/mud

COPY mud/pyproject.toml ./pyproject.toml
RUN pip install poetry && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . /app

CMD ["poetry", "run", "mud", "socketserver"]
