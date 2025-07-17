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
# package directory, so use a lightweight setup.py for installation.
RUN printf "from setuptools import setup, find_packages\n"\
          "packages=['mud']+[f'mud.{p}' for p in find_packages('mud')]\n"\
          "setup(name='quickmud', version='0.1.0', packages=packages, \"\
package_dir={'mud':'mud'}, entry_points={'console_scripts':['mud=mud.__main__:cli']})\n" \
    > setup.py \
    && pip install -e . \
    && rm setup.py

CMD ["mud", "socketserver"]
