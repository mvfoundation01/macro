"""Stage 0 - verify deploy.yml correctness."""
import pathlib

import yaml


def _load_workflow():
    p = pathlib.Path(".github/workflows/deploy.yml")
    with open(p) as f:
        return yaml.safe_load(f)


def _get_on(data):
    # YAML 1.1: bare `on:` parses to bool True. Handle both.
    return data.get("on", data.get(True, {}))


def test_deploy_yml_exists():
    p = pathlib.Path(".github/workflows/deploy.yml")
    assert p.exists(), "deploy.yml not at expected path"


def test_deploy_yml_valid_yaml():
    data = _load_workflow()
    assert "name" in data
    assert _get_on(data), "missing 'on:' trigger config"
    assert "jobs" in data


def test_deploy_yml_has_test_job():
    data = _load_workflow()
    assert "test" in data["jobs"]
    steps = data["jobs"]["test"]["steps"]
    step_names = [s.get("name", "") for s in steps]
    assert any("pytest" in n.lower() for n in step_names)
    assert any("ruff" in n.lower() for n in step_names)
    assert any("bandit" in n.lower() for n in step_names)


def test_deploy_yml_triggers_on_main_push():
    data = _load_workflow()
    triggers = _get_on(data)
    assert "push" in triggers
    assert "main" in triggers["push"].get("branches", [])


def test_dockerfile_exists():
    assert pathlib.Path("Dockerfile").exists()


def test_dockerignore_excludes_sensitive():
    p = pathlib.Path(".dockerignore")
    assert p.exists()
    content = p.read_text()
    for sensitive in [".env", "config.yaml", "data/raw"]:
        assert sensitive in content, f"{sensitive} missing from .dockerignore"
