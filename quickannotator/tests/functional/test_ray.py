import pytest
import ray

@pytest.mark.functional
def test_ray_list_and_get_tasks(test_client, monkeypatch):
    """Test the Ray task listing and retrieval endpoints with mocked Ray state."""
    
    # Mock task data
    mock_task_1 = type('MockTask', (), {
        'task_id': 'task_abc123',
        'func_or_class_name': 'test_function',
        'state': 'RUNNING',
        'creation_time_ms': 1234567890000,
        'end_time_ms': None,
        'error_message': None
    })()
    
    mock_task_2 = type('MockTask', (), {
        'task_id': 'task_def456',
        'func_or_class_name': 'test_function',
        'state': 'FINISHED',
        'creation_time_ms': 1234567890000,
        'end_time_ms': 1234567891000,
        'error_message': None
    })()
    
    # Mock state.list_tasks to return our mock tasks
    monkeypatch.setattr(
        "quickannotator.api.v1.ray.routes.state.list_tasks",
        lambda filters=None, detail=True, limit=None: [mock_task_1, mock_task_2]
    )
    
    # Mock state.get_task to return a specific task
    monkeypatch.setattr(
        "quickannotator.api.v1.ray.routes.state.get_task",
        lambda task_id: mock_task_1 if task_id == 'task_abc123' else None
    )

    # 1) Test POST /api/v1/ray/task to list tasks (no filters)
    resp = test_client.post(
        "/api/v1/ray/task",
        json={},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]['task_id'] == 'task_abc123'
    assert data[0]['func_or_class_name'] == 'test_function'
    assert data[0]['state'] == 'RUNNING'

    # 2) Test GET /api/v1/ray/task/<task_id>
    get_resp = test_client.get(f"/api/v1/ray/task/task_abc123")
    assert get_resp.status_code == 200
    task_obj = get_resp.get_json()
    assert task_obj['task_id'] == 'task_abc123'
    assert task_obj['func_or_class_name'] == 'test_function'

    # 3) Test GET with non-existent task ID
    get_resp = test_client.get(f"/api/v1/ray/task/nonexistent")
    assert get_resp.status_code == 404

    # 4) Test POST /api/v1/ray/task with filters
    # Mock filtered results
    monkeypatch.setattr(
        "quickannotator.api.v1.ray.routes.state.list_tasks",
        lambda filters=None, detail=True, limit=None: [mock_task_1]
    )
    
    filter_resp = test_client.post(
        "/api/v1/ray/task",
        json={"ray_cluster_filters": [("state", "=", "RUNNING")]},
    )
    assert filter_resp.status_code == 200
    filtered_data = filter_resp.get_json()
    assert len(filtered_data) == 1
    assert filtered_data[0]['state'] == 'RUNNING'

    # 5) Test POST /api/v1/ray/task when no tasks are found
    monkeypatch.setattr(
        "quickannotator.api.v1.ray.routes.state.list_tasks",
        lambda filters=None, detail=True, limit=None: []
    )
    
    resp = test_client.post("/api/v1/ray/task", json={})
    assert resp.status_code == 404

@pytest.mark.functional
def test_set_enable_dl(test_client, monkeypatch):
    """Test the /api/v1/ray/train/<annotation_class_id> endpoint."""
    annotation_class_id = "123"

    # Mock build_actor_name to return a predictable actor name
    monkeypatch.setattr(
        "quickannotator.api.v1.ray.routes.build_actor_name",
        lambda x: "test_actor_name"
    )

    # 1) Test successful training enable/disable
    mock_state = {
        "annotation_class_id": 123,
        "enable_training": True,
        "allow_pred": False,
        "proc_running_since": None
    }
    
    class RemoteMethod:
        def remote(self, value=None):
            return "mock_ref"
    
    class MockActor:
        set_enable_training = RemoteMethod()
        get_detailed_state = RemoteMethod()
    
    mock_actor = MockActor()
    monkeypatch.setattr("ray.get_actor", lambda name: mock_actor)
    
    def mock_ray_get(ref, timeout=None):
        if timeout is not None:
            # This is the set_enable_training call
            return None
        else:
            # This is the get_detailed_state call
            return mock_state
    
    monkeypatch.setattr("ray.get", mock_ray_get)

    resp = test_client.post(f"/api/v1/ray/train/{annotation_class_id}", query_string={"enable": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["annotation_class_id"] == 123
    assert data["enable_training"] is True
    assert data["allow_pred"] is False

    # 2) Test actor not found (404)
    def raise_value_error(name):
        raise ValueError("Actor not found")
    
    monkeypatch.setattr("ray.get_actor", raise_value_error)
    resp = test_client.post(f"/api/v1/ray/train/{annotation_class_id}", query_string={"enable": True})
    assert resp.status_code == 404

    # 3) Test timeout while waiting for ray.get (408)
    monkeypatch.setattr("ray.get_actor", lambda name: mock_actor)
    
    def raise_timeout_error(ref, timeout=None):
        raise ray.exceptions.GetTimeoutError("Timeout occurred")
    
    monkeypatch.setattr("ray.get", raise_timeout_error)
    resp = test_client.post(f"/api/v1/ray/train/{annotation_class_id}", query_string={"enable": True})
    assert resp.status_code == 408

@pytest.mark.functional
def test_get_dl_actor_status(test_client, monkeypatch):
    """Test the /api/v1/ray/train/status/<annotation_class_id> endpoint."""
    annotation_class_id = "123"

    # Mock build_actor_name to return a predictable actor name
    monkeypatch.setattr(
        "quickannotator.api.v1.ray.routes.build_actor_name",
        lambda x: "test_actor_name"
    )

    # 1) Test successful status retrieval
    mock_state = {
        "annotation_class_id": 123,
        "enable_training": True,
        "allow_pred": False,
        "proc_running_since": None
    }
    
    class RemoteMethod:
        def remote(self):
            return "mock_ref"
    
    class MockActor:
        get_detailed_state = RemoteMethod()
    
    mock_actor = MockActor()
    monkeypatch.setattr("ray.get_actor", lambda name: mock_actor)
    monkeypatch.setattr("ray.get", lambda ref: mock_state)

    resp = test_client.get(f"/api/v1/ray/train/status/{annotation_class_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["annotation_class_id"] == 123
    assert data["enable_training"] is True
    assert data["allow_pred"] is False

    # 2) Test actor not found (404)
    def raise_value_error(name):
        raise ValueError("Actor not found")
    
    monkeypatch.setattr("ray.get_actor", raise_value_error)
    resp = test_client.get(f"/api/v1/ray/train/status/{annotation_class_id}")
    assert resp.status_code == 404

@pytest.mark.functional
def test_get_dl_actors_status(test_client, monkeypatch):
    """Test the /api/v1/ray/train/status endpoint for multiple actors."""
    
    # Mock build_actor_name to return predictable actor names
    monkeypatch.setattr(
        "quickannotator.api.v1.ray.routes.build_actor_name",
        lambda x: f"test_actor_{x}"
    )

    # 1) Test successful status retrieval for multiple actors
    mock_state_1 = {
        "annotation_class_id": 123,
        "enable_training": True,
        "allow_pred": False,
        "proc_running_since": None
    }
    mock_state_2 = {
        "annotation_class_id": 456,
        "enable_training": False,
        "allow_pred": True,
        "proc_running_since": None
    }
    
    class RemoteMethod1:
        def remote(self):
            return "mock_ref_1"
    
    class RemoteMethod2:
        def remote(self):
            return "mock_ref_2"
    
    class MockActor1:
        get_detailed_state = RemoteMethod1()
    
    class MockActor2:
        get_detailed_state = RemoteMethod2()
    
    def mock_get_actor(name):
        if name == "test_actor_123":
            return MockActor1()
        elif name == "test_actor_456":
            return MockActor2()
        raise ValueError("Actor not found")
    
    def mock_ray_get(ref):
        if ref == "mock_ref_1":
            return mock_state_1
        elif ref == "mock_ref_2":
            return mock_state_2
        return None
    
    monkeypatch.setattr("ray.get_actor", mock_get_actor)
    monkeypatch.setattr("ray.get", mock_ray_get)

    resp = test_client.get("/api/v1/ray/train/status", query_string={"annotation_class_ids": ["123", "456"]})
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert any(d["annotation_class_id"] == 123 for d in data)
    assert any(d["annotation_class_id"] == 456 for d in data)

    # 2) Test with no annotation_class_ids provided (404)
    resp = test_client.get("/api/v1/ray/train/status")
    assert resp.status_code == 404
