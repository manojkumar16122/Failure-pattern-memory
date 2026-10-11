from typing import List, Optional

from fpm.models import FailureEvent, WarningResult
from fpm.storage import FailureStore


class FailurePatternMemory:
    """The main FPM engine - record failures, get warnings.

    `classifier` and `embedder` can be injected (used by the offline tests).
    """

    def __init__(self, db_path: str = "failures.db", groq_api_key: Optional[str] = None,
                 classifier=None, embedder=None):
        self.store = FailureStore(db_path, embedder=embedder)
        if classifier is None:
            from fpm.classifier import FailureClassifier
            classifier = FailureClassifier(groq_api_key)
        self.classifier = classifier

    def record_failure(
        self,
        raw_log: str,
        task_type: str = "unknown",
        agent_id: str = "default",
        severity: Optional[str] = None,
    ) -> str:
        classified = self.classifier.classify(raw_log, task_type)

        event = FailureEvent(
            error_category=classified.get("error_category", "UNKNOWN"),
            description=classified.get("description") or raw_log[:100],
            task_type=task_type,
            agent_id=agent_id,
            context_pattern=classified.get("context_pattern") or "unknown pattern",
            root_cause=classified.get("root_cause", ""),
            resolution="pending",
            prevention=classified.get("prevention", ""),
            severity=severity or classified.get("severity", "medium"),
        )
        return self.store.record(event)

    def check_before_task(self, task_description: str, top_k: int = 5) -> List[WarningResult]:
        return self.store.find_warnings(task_description, top_k)

    def get_failure_history(self) -> List[dict]:
        return self.store.get_all()
