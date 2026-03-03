#!/bin/bash
# Start the backend development server
cd "$(dirname "$0")/../backend" || exit 1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
