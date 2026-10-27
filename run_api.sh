#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PYTHONPATH="$PWD"
echo "REST API on http://localhost:8000  (docs: http://localhost:8000/docs)"
uvicorn core.api:app --host 127.0.0.1 --port 8000
