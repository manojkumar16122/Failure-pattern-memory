"""Offline tests: no Groq key, no model download, no network."""
import hashlib
import re

import numpy as np

from fpm.engine import FailurePatternMemory


class FakeEmbedder:
    """Deterministic bag-of-words embedder (384-dim, unit length)."""

    def encode(self, text, normalize_embeddings=True):
        vec = np.zeros(384, dtype=np.float32)
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % 384
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec


class FakeClassifier:
    def classify(self, raw_log, task_type="unknown"):
        return {
            "error_category": "TOOL_FAILURE",
            "description": raw_log[:80],
            "context_pattern": "docker deploy port conflict",
            "root_cause": "port already bound",
            "prevention": "check free ports before deploy",
            "severity": "high",
        }


def make_fpm():
    return FailurePatternMemory(
        db_path=":memory:", classifier=FakeClassifier(), embedder=FakeEmbedder()
    )


def test_record_and_check():
    fpm = make_fpm()
    failure_id = fpm.record_failure(
        raw_log="Docker container failed to start: port 8080 already in use",
        task_type="deployment",
        agent_id="test_agent",
    )
    assert failure_id.startswith("fail_")

    warnings = fpm.check_before_task("docker deploy application port conflict")
    assert len(warnings) == 1
    assert warnings[0].failure_id == failure_id
    assert "port" in warnings[0].context_pattern.lower()
    assert warnings[0].similarity > 0.8


def test_unrelated_task_gets_no_warning():
    fpm = make_fpm()
    fpm.record_failure("port clash", task_type="deployment")
    assert fpm.check_before_task("summarize quarterly sales report") == []


def test_history():
    fpm = make_fpm()
    fpm.record_failure("a", task_type="x")
    fpm.record_failure("b", task_type="y")
    assert len(fpm.get_failure_history()) == 2
