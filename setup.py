from setuptools import setup, find_packages

setup(
    name='quickmud',
    version='0.1.0',
    packages=['mud'] + [f'mud.{p}' for p in find_packages('mud')],
    package_dir={'mud': 'mud'},
    install_requires=[
        "SQLAlchemy>=2.0,<3",
        "typer>=0.9",
        "python-dotenv>=1.0",
        "fastapi",
        "uvicorn",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
            "pytest-cov>=6.0",
            "mypy",
            "ruff",
            "flake8",
            "jsonschema",
        ],
    },
    entry_points={
        'console_scripts': [
            'mud=mud.__main__:cli',
        ],
    },
)
