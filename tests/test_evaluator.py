import pytest
from app.db.session import init_db, get_session
from app.models.flag import FeatureFlag


@pytest.fixture(autouse=True)
def prepare_db(tmp_path, monkeypatch):
    # use a temporary sqlite file
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    yield


def test_percentage_rollout_deterministic():
    from app.services.evaluator import Evaluator
    ev = Evaluator()
    # create flag in DB
    with get_session() as s:
        f = FeatureFlag(name="rollout", default=False, rules=[{
            "rule_type": "percentage_rollout",
            "parameters": {"attribute": "user_id", "percentage": 50},
            "on": True,
            "priority": 10,
            "id": "r1"
        }])
        s.add(f)
        s.commit()
    # deterministic mapping: same user_id should always evaluate the same
    r1 = ev.evaluate("rollout", {"user_id": "user-123"})
    r2 = ev.evaluate("rollout", {"user_id": "user-123"})
    assert r1["value"] == r2["value"]


def test_attribute_match_rule():
    from app.services.evaluator import Evaluator
    ev = Evaluator()
    with get_session() as s:
        f = FeatureFlag(name="region-flag", default=False, rules=[{
            "rule_type": "attribute_match",
            "parameters": {"attribute": "region", "operator": "in", "values": ["us", "eu"]},
            "on": True,
            "priority": 5,
            "id": "r2"
        }])
        s.add(f)
        s.commit()

    r = ev.evaluate("region-flag", {"region": "us"})
    assert r["value"] is True
