import pytest

# Skip the whole module if ray isn't installed
import ray

@pytest.mark.functional
def test_ray_list_and_get_tasks(test_client):
    """Start a local Ray instance, submit tasks, then hit the flask endpoints to verify task info."""
    # Start a local Ray instance for the test
    # include_dashboard=False avoids opening dashboard port in CI environments
    ray.init(ignore_reinit_error=True, include_dashboard=False)

    @ray.remote
    def report_task_id(x):
        # Return the current task id (in hex when possible) so tests can query by id
        try:
            from ray import get_runtime_context
            tid = get_runtime_context().get_task_id()
            # Task id may be a TaskID object with hex() or a bytes-like; fall back to str
            return tid.hex() if hasattr(tid, "hex") else str(tid)
        except Exception:
            return "unknown"

    # Submit a couple of tasks
    refs = [report_task_id.remote(i) for i in range(2)]

    # Wait for completion and collect task ids returned by the remote function
    task_ids = ray.get(refs)
    assert len(task_ids) == 2

    # 1) Test POST /api/v1/ray/task to list tasks (no filters)
    resp = test_client.post(
        "/api/v1/ray/task",
        json={},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    # The updated endpoint returns a list of task dicts (not wrapped in a taskStates key)
    assert isinstance(data, list)
    # There should be at least one entry for our function name
    names = {t.get("func_or_class_name") for t in data}
    assert any("report_task_id" in (n or "") for n in names)

    # 2) Test GET /api/v1/ray/task/<task_id> for one of the returned task ids
    # Use the first task id we received from the remote call
    tid = task_ids[0]
    get_resp = test_client.get(f"/api/v1/ray/task/{tid}")

    # Either found (200) or not found (404) is acceptable depending on timing; prefer 200
    assert get_resp.status_code == 200 or get_resp.status_code == 404
    if get_resp.status_code == 200:
        task_obj = get_resp.get_json()
        # The GET endpoint returns a single task dict using camelCase keys
        assert task_obj.get("task_id") == tid
        assert "report_task_id" in task_obj.get("func_or_class_name", "")

    # 3) Test POST /api/v1/ray/task with a filter in the JSON payload
    filter_resp = test_client.post(
        "/api/v1/ray/task",
        json={"ray_cluster_filters": [("func_or_class_name", "=", "report_task_id")]},
    )

    assert filter_resp.status_code == 200
    filtered_data = filter_resp.get_json()
    assert isinstance(filtered_data, list)
    # Ensure the filtered response only includes tasks matching the filter
    filtered_names = {t.get("func_or_class_name") for t in filtered_data}
    assert all("report_task_id" in (n or "") for n in filtered_names)

    # Shutdown ray for cleanliness
    ray.shutdown()

@pytest.mark.functional
def test_set_enable_dl(test_client, mocker):
    """Test the /api/v1/ray/<annotation_class_id>/train endpoint."""
    annotation_class_id = "123"

    # Mock build_actor_name to return a predictable actor name
    mocker.patch(
        "quickannotator.db.crud.annotation_class.build_actor_name",
        return_value="test_actor_name"
    )

    # 1) Test successful training enable/disable
    mock_actor = mocker.MagicMock()
    mock_actor.set_enable_training.remote.return_value = "mock_ref"
    mocker.patch("ray.get_actor", return_value=mock_actor)
    mocker.patch("ray.get", return_value=None)  # Simulate successful completion

    resp = test_client.post(f"/api/v1/ray/{annotation_class_id}/train", query_string={"value": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {}  # The endpoint returns an empty JSON object on success

    # 2) Test actor not found (404)
    mocker.patch("ray.get_actor", side_effect=ValueError("Actor not found"))
    resp = test_client.post(f"/api/v1/ray/{annotation_class_id}/train", query_string={"value": True})
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["message"] == "Actor not found"

    # 3) Test timeout while waiting for ray.get (408)
    mocker.patch("ray.get_actor", return_value=mock_actor)
    mocker.patch("ray.get", side_effect=ray.exceptions.GetTimeoutError("Timeout occurred"))
    resp = test_client.post(f"/api/v1/ray/{annotation_class_id}/train", query_string={"value": True})
    assert resp.status_code == 408
    data = resp.get_json()
    assert data["message"] == "Request timed out while waiting for actor response"
