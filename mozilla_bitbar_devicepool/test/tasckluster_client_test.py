import pytest

from mozilla_bitbar_devicepool.taskcluster_client import TaskclusterClient


@pytest.fixture
def client():
    return TaskclusterClient(verbose=False)


def test_get_quarantined_worker_names(client):
    # Injecting results directly
    results = [
        {"workerId": "worker-2"},
        {"workerId": "worker-1"},
        {"workerId": "worker-3"},
    ]
    result = client.get_quarantined_worker_names("prov", "type", results=results)
    assert result == ["worker-1", "worker-2", "worker-3"]


def test_get_quarantined_workers(client):
    # Injecting results directly
    results = {
        "workers": [
            {"workerId": "worker-1", "quarantineUntil": None},
            {"workerId": "worker-2", "quarantineUntil": "2099-01-01T00:00:00Z"},
            {"workerId": "worker-3"},
            {"workerId": "worker-4", "quarantineUntil": "2099-01-01T00:00:00Z"},
        ]
    }
    result = client.get_quarantined_workers("prov", "type", results=results)
    assert [w["workerId"] for w in result] == ["worker-2", "worker-4"]
    for w in result:
        assert w["quarantined"]
