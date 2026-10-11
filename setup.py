from setuptools import setup, find_packages

setup(
    name="failure-pattern-memory",
    version="0.1.0",
    description="Learn from AI agent failures - record patterns, get pre-emptive warnings.",
    author="Manoj Kumar",
    author_email="manojkumarvelusamy2003@gmail.com",
    url="https://github.com/manojkumar16122/failure-pattern-memory",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "fastapi",
        "uvicorn",
        "groq",
        "sqlite-vec",
        "sentence-transformers",
        "numpy",
        "pydantic>=2",
        "typer",
        "rich",
        "python-dotenv",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "fpm=fpm.cli:app",
        ],
    },
)
