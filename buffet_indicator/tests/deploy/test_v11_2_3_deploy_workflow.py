"""Stage 0 - verify deploy.yml correctness.

deploy.yml lives at the GIT REPO ROOT (D:/macro/.github/workflows/deploy.yml),
NOT inside buffet_indicator/. We walk up from this test file to find the .git
directory and resolve paths relative to it.
"""
import pathlib

import yaml


def _repo_root() -> pathlib.Path:
    p = pathlib.Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("could not locate git repo root")


def _load_workflow():
    p = _repo_root() / ".github" / "workflows" / "deploy.yml"
    with open(p) as f:
        return yaml.safe_load(f)


def _get_on(data):
    # YAML 1.1: bare `on:` parses to bool True. Handle both.
    return data.get("on", data.get(True, {}))


def test_deploy_yml_exists():
    p = _repo_root() / ".github" / "workflows" / "deploy.yml"
    assert p.exists(), f"deploy.yml not at expected path: {p}"


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
    assert (_repo_root() / "buffet_indicator" / "Dockerfile").exists()


def test_dockerignore_excludes_sensitive():
    p = _repo_root() / "buffet_indicator" / ".dockerignore"
    assert p.exists()
    content = p.read_text()
    for sensitive in [".env", "config.yaml", "data/raw"]:
        assert sensitive in content, f"{sensitive} missing from .dockerignore"
