"""Tests for department and employee API."""
import pytest
from fastapi.testclient import TestClient


def test_create_department(client: TestClient) -> None:
    """POST /departments/ creates a department."""
    r = client.post(
        "/departments/",
        json={"name": "Engineering", "parent_id": None},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Engineering"
    assert data["parent_id"] is None
    assert "id" in data
    assert "created_at" in data


def test_create_department_trim_name(client: TestClient) -> None:
    """Name is trimmed."""
    r = client.post(
        "/departments/",
        json={"name": "  Backend  ", "parent_id": None},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Backend"


def test_create_department_validation_empty_name(client: TestClient) -> None:
    """Empty name is rejected."""
    r = client.post(
        "/departments/",
        json={"name": "  ", "parent_id": None},
    )
    assert r.status_code == 422


def test_create_employee(client: TestClient) -> None:
    """POST /departments/{id}/employees/ creates an employee."""
    cr = client.post("/departments/", json={"name": "HR", "parent_id": None})
    assert cr.status_code == 200
    dept_id = cr.json()["id"]
    r = client.post(
        f"/departments/{dept_id}/employees/",
        json={
            "full_name": "John Doe",
            "position": "Manager",
            "hired_at": "2024-01-15",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["full_name"] == "John Doe"
    assert data["position"] == "Manager"
    assert data["department_id"] == dept_id
    assert data["hired_at"] == "2024-01-15"


def test_create_employee_nonexistent_department(client: TestClient) -> None:
    """Creating employee in non-existent department returns 404."""
    r = client.post(
        "/departments/99999/employees/",
        json={"full_name": "Jane", "position": "Dev"},
    )
    assert r.status_code == 404


def test_get_department_not_found(client: TestClient) -> None:
    """GET /departments/{id} returns 404 for non-existent department."""
    r = client.get("/departments/99999")
    assert r.status_code == 404


def test_get_department_tree(client: TestClient) -> None:
    """GET /departments/{id} returns department with employees and children."""
    cr = client.post("/departments/", json={"name": "Root", "parent_id": None})
    assert cr.status_code == 200
    root_id = cr.json()["id"]
    client.post(
        f"/departments/{root_id}/employees/",
        json={"full_name": "Alice", "position": "Lead"},
    )
    r = client.get(f"/departments/{root_id}?depth=1&include_employees=true")
    assert r.status_code == 200
    data = r.json()
    assert data["department"]["id"] == root_id
    assert data["department"]["name"] == "Root"
    assert len(data["employees"]) == 1
    assert data["employees"][0]["full_name"] == "Alice"
    assert data["children"] == []


def test_patch_department(client: TestClient) -> None:
    """PATCH /departments/{id} updates name and parent."""
    cr = client.post("/departments/", json={"name": "Old", "parent_id": None})
    assert cr.status_code == 200
    dept_id = cr.json()["id"]
    r = client.patch(
        f"/departments/{dept_id}",
        json={"name": "New Name"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


def test_patch_department_self_parent_conflict(client: TestClient) -> None:
    """PATCH with parent_id = self returns 409."""
    cr = client.post("/departments/", json={"name": "Dept", "parent_id": None})
    assert cr.status_code == 200
    dept_id = cr.json()["id"]
    r = client.patch(
        f"/departments/{dept_id}",
        json={"parent_id": dept_id},
    )
    assert r.status_code == 409


def test_patch_department_cycle_conflict(client: TestClient) -> None:
    """PATCH moving department into its own subtree returns 409."""
    cr = client.post("/departments/", json={"name": "Parent", "parent_id": None})
    assert cr.status_code == 200
    parent_id = cr.json()["id"]
    cr2 = client.post("/departments/", json={"name": "Child", "parent_id": parent_id})
    assert cr2.status_code == 200
    child_id = cr2.json()["id"]
    # Move Parent under Child (would create cycle: Parent -> Child -> Parent)
    r = client.patch(
        f"/departments/{parent_id}",
        json={"parent_id": child_id},
    )
    assert r.status_code == 409


def test_delete_department_cascade(client: TestClient) -> None:
    """DELETE with mode=cascade removes department and employees."""
    cr = client.post("/departments/", json={"name": "ToDelete", "parent_id": None})
    assert cr.status_code == 200
    dept_id = cr.json()["id"]
    client.post(
        f"/departments/{dept_id}/employees/",
        json={"full_name": "Bob", "position": "Dev"},
    )
    r = client.delete(f"/departments/{dept_id}?mode=cascade")
    assert r.status_code == 204
    get_r = client.get(f"/departments/{dept_id}")
    assert get_r.status_code == 404


def test_delete_reassign_without_target_returns_400(client: TestClient) -> None:
    """DELETE with mode=reassign without reassign_to_department_id returns 400."""
    cr = client.post("/departments/", json={"name": "X", "parent_id": None})
    assert cr.status_code == 200
    dept_id = cr.json()["id"]
    r = client.delete(f"/departments/{dept_id}?mode=reassign")
    assert r.status_code == 400


def test_delete_invalid_mode(client: TestClient) -> None:
    """DELETE with invalid mode returns 422."""
    cr = client.post("/departments/", json={"name": "Y", "parent_id": None})
    assert cr.status_code == 200
    dept_id = cr.json()["id"]
    r = client.delete(f"/departments/{dept_id}?mode=invalid")
    assert r.status_code == 422


def test_delete_department_reassign(client: TestClient) -> None:
    """DELETE with mode=reassign moves employees to target department."""
    cr1 = client.post("/departments/", json={"name": "A", "parent_id": None})
    cr2 = client.post("/departments/", json={"name": "B", "parent_id": None})
    assert cr1.status_code == 200 and cr2.status_code == 200
    id_a, id_b = cr1.json()["id"], cr2.json()["id"]
    client.post(
        f"/departments/{id_a}/employees/",
        json={"full_name": "Bob", "position": "Dev"},
    )
    r = client.delete(
        f"/departments/{id_a}?mode=reassign&reassign_to_department_id={id_b}"
    )
    assert r.status_code == 204
    tree = client.get(f"/departments/{id_b}").json()
    assert len(tree["employees"]) == 1
    assert tree["employees"][0]["full_name"] == "Bob"


def test_duplicate_department_name_under_same_parent(client: TestClient) -> None:
    """Two departments with same name under same parent return 409."""
    cr = client.post("/departments/", json={"name": "IT", "parent_id": None})
    assert cr.status_code == 200
    parent_id = cr.json()["id"]
    client.post("/departments/", json={"name": "Backend", "parent_id": parent_id})
    r = client.post(
        "/departments/",
        json={"name": "Backend", "parent_id": parent_id},
    )
    assert r.status_code == 409


def test_health(client: TestClient) -> None:
    """GET /health returns ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
