# Student Evaluation System - Core Agent Instructions

## Purpose
This is the main development guide and guardrail document for coding agents.
Do not guess implementation details. Use the `@` references below to read specific domain knowledge on demand.

## Context Pointers (Read strictly on demand)
- **Frontend Architecture & UI Design System:** `@docs/architecture/FRONTEND.md`
- **Development Workflow, Testing & Env Vars:** `@docs/DEVELOPMENT.md`
- **API Routes, Auth & Roles:** `@docs/api/ROUTES.md`
- **Semester 2 Roadmap & Compliance:** `@docs/ROADMAP.md`
- **Database & PostgreSQL:** `@docs/POSTGRESQL.md`
- **API Contract:** `@docs/api/API_CONTRACT_V1.md`

## Project Goal
Student Evaluation System (SES) is an outcome-based assessment platform for higher education tracking student achievement from Assessment -> Learning Outcome (LO) -> Program Outcome (PO).

## Core Domain Model
- **Academic Structure:** University, Department, DegreeLevel, Program, Term, Course
- **Outcomes:** ProgramOutcome (PO), LearningOutcome (LO), LO->PO Mapping
- **Evaluation:** Assessment, Assessment->LO Mapping, StudentGrade, CourseEnrollment
- **Score Flow:** Grades -> Assessment Weights -> Course LO Scores -> Program PO Scores. (Currently synchronous in `backend/evaluation/services.py`).

## Agent Guardrails (CRITICAL)
1. Preserve backward-compatible API routes unless migration plan is explicit.
2. Keep generated API code auto-generated; avoid manual edits in generated folders.
3. Include migrations for model changes and run checks before finishing.
4. Ensure implemented versus planned status is always explicit in commits and PRs.
5. Prefer minimal, targeted changes aligned with existing architecture.

## Known Gaps & Constraints (Active Tasks)
- Score calculation service is synchronous today.
- Real-time messaging stack is not fully integrated yet.
- Frontend API generation config appears partially stale versus current folder layout.
- `run.bat` still assumes backend/venv activation; local preferred backend workflow is `uv`.
