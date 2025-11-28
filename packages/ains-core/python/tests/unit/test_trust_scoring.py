import datetime as dt

import pytest

from ains.trust import (
    compute_trust_score,
    TrustInputs,
)


def test_new_agent_default_trust():
    inputs = TrustInputs(
        total_tasks_completed=0,
        total_tasks_failed=0,
        last_task_completed_at=None,
        last_assigned_at=None,
        current_trust_score=None,
    )

    score = compute_trust_score(inputs)

    assert 0.0 <= score <= 1.0
    # Expect something close to neutral (e.g., 0.5); adjust threshold as per your spec.
    assert score == pytest.approx(0.5, rel=0.25)


def test_trust_increases_with_successes():
    now = dt.datetime.utcnow()
    inputs = TrustInputs(
        total_tasks_completed=50,
        total_tasks_failed=2,
        last_task_completed_at=now,
        last_assigned_at=now,
        current_trust_score=0.6,
    )

    score = compute_trust_score(inputs)

    assert score > 0.6
    assert score <= 1.0


def test_trust_decreases_with_failures():
    now = dt.datetime.utcnow()
    inputs = TrustInputs(
        total_tasks_completed=10,
        total_tasks_failed=20,
        last_task_completed_at=now,
        last_assigned_at=now,
        current_trust_score=0.7,
    )

    score = compute_trust_score(inputs)

    assert score < 0.7
    assert score >= 0.0


def test_trust_penalizes_stale_agents():
    old = dt.datetime.utcnow() - dt.timedelta(days=7)
    inputs = TrustInputs(
        total_tasks_completed=30,
        total_tasks_failed=0,
        last_task_completed_at=old,
        last_assigned_at=old,
        current_trust_score=0.9,
    )

    score = compute_trust_score(inputs)

    # High success history but stale should reduce score somewhat.
    assert score < 0.9
    assert 0.0 <= score <= 1.0
