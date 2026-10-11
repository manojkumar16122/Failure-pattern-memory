from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel

from fpm.engine import FailurePatternMemory

app = FastAPI(title="Failure Pattern Memory API")


@lru_cache(maxsize=1)
def get_fpm() -> FailurePatternMemory:
    return FailurePatternMemory()


class FailureInput(BaseModel):
    raw_log: str
    task_type: str = "unknown"
    agent_id: str = "default"


class TaskQuery(BaseModel):
    task_description: str
    top_k: int = 5


@app.post("/failure")
def record_failure(payload: FailureInput):
    failure_id = get_fpm().record_failure(
        payload.raw_log, task_type=payload.task_type, agent_id=payload.agent_id
    )
    return {"failure_id": failure_id}


@app.post("/warnings")
def get_warnings(query: TaskQuery):
    warnings = get_fpm().check_before_task(query.task_description, top_k=query.top_k)
    return {"warnings": [w.model_dump() for w in warnings]}


@app.get("/history")
def get_history():
    return {"failures": get_fpm().get_failure_history()}
