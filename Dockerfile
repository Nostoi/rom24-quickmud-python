FROM python:3.10

# Set the working directory inside the container
WORKDIR /app/mud

# Copy only the project files
COPY mud/pyproject.toml ./
COPY mud ./

# Install dependencies with Poetry
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

CMD ["python", "mud.py"]
