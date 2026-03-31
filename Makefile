PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

.PHONY: install api run-jboss run-tomcat loop-jboss loop-tomcat validate benchmark-smoke clean

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt

api:
	$(PY) -m uvicorn middleware_control_plane.api:app --host 0.0.0.0 --port $${PORT:-8000}

run-jboss:
	$(PY) mcp.py --config configs/jboss-local.yaml --once --dry-run

run-tomcat:
	$(PY) mcp.py --config configs/tomcat-local.yaml --once --dry-run

loop-jboss:
	$(PY) mcp.py --config configs/jboss-local.yaml

loop-tomcat:
	$(PY) mcp.py --config configs/tomcat-local.yaml

validate:
	./scripts/validate_repo.sh

benchmark-smoke:
	$(PY) benchmarks/run_benchmark.py --url http://127.0.0.1:8080/ --concurrency 5 --requests 25 --output-dir docs/evidence

clean:
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache
