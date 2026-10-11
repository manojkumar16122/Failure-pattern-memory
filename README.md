# Failure Pattern Memory

Learn from AI agent failures. Record patterns, get pre-emptive warnings.

## The Problem

Agent systems usually handle errors reactively. An agent hits an error, retries or a human
fixes it, and the lesson is lost. The next run or the next agent repeats the same mistake.
Multi-agent setups make this worse, because one agent's bad output can spread to the others.

## What It Does

1. **Records failures**: a raw error log is classified by an LLM (Groq) into category,
   description, root cause, prevention, and severity.
2. **Stores patterns**: records go into SQLite, with the context pattern embedded and
   indexed by sqlite-vec for vector search. No separate database server is needed.
3. **Warns before a task**: a new task description is matched against stored patterns, and
   similar past failures come back with prevention advice.
4. **Shows results**: a CLI, a REST API, and a generated HTML dashboard.

## Project Layout

```
fpm/            core package (models, storage, classifier, engine, cli)
api.py          FastAPI server
dashboard.py    builds dashboard.html from the failure database
demo.py         sample run
tests/          offline tests (no API key, no model download)
```

## Quick Start (Windows PowerShell)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env          # then put your GROQ_API_KEY in .env
python demo.py
python dashboard.py demo.db
start dashboard.html
```

Linux / macOS: use `python3 -m venv venv`, `source venv/bin/activate`, and `cp .env.example .env`.

## Usage

```powershell
fpm record "ModuleNotFoundError: No module named 'requests'" --task script_run
fpm check "run python script that imports requests"
fpm history
uvicorn api:app --reload        # then open http://127.0.0.1:8000/docs
```

## Tests

Tests run offline with a fake classifier and embedder:

```powershell
pytest -q
```

## Requirements

- Python 3.10+
- A Python build whose `sqlite3` supports loadable extensions (python.org and conda builds do)
- A Groq API key for `demo.py`, `fpm record`, and the API's record endpoint

## Limitations

- The `resolution` field is stored as "pending". Recording how a failure was fixed would
  make warnings more useful.
- Classification quality depends on the LLM. Review records before relying on them.
- Similarity uses a general sentence embedding, so the threshold may need tuning on real logs.
