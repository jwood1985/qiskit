.PHONY: install backend frontend test test-backend dev-backend dev-frontend

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

test: test-backend

test-backend:
	cd backend && PYTHONPATH=. python -m pytest

dev-backend:
	cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build
