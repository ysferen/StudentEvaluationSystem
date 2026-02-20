# Student Evaluation System - Essential Commands

.PHONY: help
help: ## Show available commands
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-15s %s\n", $$1, $$2}'

# Development
.PHONY: run
run: ## Start both backend and frontend
	start cmd /k "cd backend/student_evaluation_system && python manage.py runserver"
	start cmd /k "cd frontend && npm run dev"

.PHONY: run-backend
run-backend: ## Start Django server only
	cd backend/student_evaluation_system && python manage.py runserver

.PHONY: run-frontend
run-frontend: ## Start React dev server only
	cd frontend && npm run dev

# Database
.PHONY: migrate
migrate: ## Run Django migrations
	cd backend/student_evaluation_system && python manage.py migrate

.PHONY: makemigrations
makemigrations: ## Create Django migrations
	cd backend/student_evaluation_system && python manage.py makemigrations

# Testing
.PHONY: test-backend
test-backend: ## Run backend tests
	cd backend/student_evaluation_system && pytest

# Code Quality (Manual - Run when ready)
.PHONY: format-backend
format-backend: ## Format Python code with black
	cd backend/student_evaluation_system && black . --line-length=100

.PHONY: lint-backend
lint-backend: ## Check Python code with flake8
	cd backend/student_evaluation_system && flake8 --max-line-length=100 --extend-ignore=E203,W503

# Git Workflow
.PHONY: pr-ready
pr-ready: ## Run checks before creating PR
	cd backend/student_evaluation_system && pytest -q
