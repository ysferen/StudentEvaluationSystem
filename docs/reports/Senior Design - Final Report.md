# Student Evaluation System (SES)
## Senior Design Project — Final Report

**CSE 401/402 Senior Design**

**Team Members:**
- Tarık Ziya Aykut — 210402001
- Ammar Yasir Bayır — 221401042
- Vefa Mert Toker — 221401046
- Yusuf Eren Arı — 221401010

**Project Customer:**
Department of Computer Engineering, Acıbadem University
Prof. Dr. Ahmet Bulut

**Date:** May 2026

---

## Abstract

The Student Evaluation System (SES) is an outcome-based assessment platform that transforms how higher education institutions track student achievement. Moving beyond traditional grade-point averages, SES maps individual assessment scores through Learning Outcomes (LOs) to Program Outcomes (POs), providing granular, data-driven insight into student competency. The system serves five distinct user roles — Administrator, Instructor, Program Head, Student, and Guest — each with tailored dashboards and workflows. Built on a modern decoupled architecture (Django REST Framework backend, React/TypeScript frontend, PostgreSQL, Redis, Celery), the platform supports bulk Excel-based grade imports with intelligent validation, automated asynchronous score recomputation, and AI-assisted assessment-to-outcome weight suggestions using sentence embedding models. SES addresses the critical needs of ABET accreditation, outcome-based education compliance, and institutional analytics, replacing error-prone manual spreadsheet workflows with a secure, scalable web application.

**Keywords:** education, outcome-based assessment, evaluation, grading, Django, React, Celery, embedding models, ABET, program outcomes

---

## 1. Executive Summary

Traditional academic evaluation systems reduce student performance to a single letter grade. This approach obscures which specific skills a student has mastered and where deficiencies remain. For engineering programs subject to ABET accreditation, the inability to systematically track outcome achievement creates significant administrative burden and compliance risk.

The Student Evaluation System directly addresses this gap. Instructors define Learning Outcomes for each course and map them to institutional Program Outcomes. Every assessment — midterm, project, quiz, or final — is linked to the outcomes it measures with configurable weights. When grades are entered (manually or via bulk Excel import), the system automatically computes per-student LO scores and aggregates them into PO scores across all enrolled courses. The result is a complete, auditable chain from a single exam question to an institution-wide accreditation report.

The system was developed across two semesters following an iterative methodology. Semester 1 delivered the Minimum Viable Product: core academic structure models, role-based authentication, manual grade entry, synchronous score calculation, and basic dashboards. Semester 2 transformed this foundation into a production-ready platform by adding asynchronous processing (Celery + Redis), AI-assisted weight suggestions using SentenceTransformers, course template cloning for multi-term reuse, instructor permission management, bulk file import with validation pipelines, a dedicated Program Head role, and a public-facing landing page with guest exploration.

SES currently supports 28 backend test suites with 70%+ coverage and 16 frontend test suites using Vitest. The entire stack runs containerized via Docker Compose with five services (PostgreSQL, Redis, backend, Celery worker, frontend), enabling consistent deployment from development to production.

---

## 2. Problem Statement and Goals

### 2.1 The Assessment Gap

Universities worldwide are shifting toward outcome-based education (OBE), where the central question is not "what grade did the student get?" but "what can the student actually do?" Accreditation bodies such as ABET require demonstrable evidence that graduates achieve specific program outcomes. Yet the tools available to most instructors — spreadsheets, generic gradebooks, Learning Management Systems designed for content delivery rather than outcome tracking — make this evidence gathering tedious, error-prone, and inconsistent.

The specific problems are:

1. **Manual mapping burden.** An instructor with 4 assessments and 5 learning outcomes must define and maintain 20+ weight relationships. These weights must sum correctly across dimensions, and errors cascade into institution-level reports.

2. **No automated aggregation.** Individual scores live in disconnected spreadsheets. Rolling them up to LO scores and then PO scores requires complex manual formulas that few instructors have time to build or validate.

3. **Missing institutional visibility.** Program heads and accreditation committees cannot easily see how their programs are performing against stated outcomes. They rely on ad-hoc reports compiled weeks before accreditation visits.

4. **Data entry friction.** Importing grades from existing university systems (OBS/Student Information Systems) should be seamless, with automatic validation that catches mismatched student IDs, out-of-range scores, and missing data before it corrupts the database.

5. **No real-time awareness.** Students have no dashboard showing their progress toward learning outcomes. They receive final grades without understanding which competencies they demonstrated and which need improvement.

### 2.2 Project Goals

The SES was designed to address all five problems in a single, integrated platform:

| Goal | How SES Addresses It |
|---|---|
| Eliminate manual weight calculations | AI-assisted weight suggestion using sentence embeddings; instructor-approved before application |
| Automate outcome score aggregation | Weighted calculation engine: Grades → LO Scores → PO Scores; async via Celery for large datasets |
| Provide institutional visibility | Program Head dashboard with PO achievement heatmaps, trend analytics, and export-ready views |
| Streamline data import | Excel file upload with multi-stage validation (structure, students, assessments, scores); guided resolution UI |
| Empower students with transparency | Personal competency radar charts, per-assessment score history, LO achievement tracking |

---

## 3. Final System Architecture

### 3.1 High-Level Architecture

SES follows a **decoupled monolithic** design: the backend is a single Django application exposing a RESTful API, while the frontend is an independent React application communicating exclusively through that API. This architecture combines the development simplicity of a monolith with the deployment flexibility and responsive user experience of a separate frontend.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              React 18 + TypeScript + Vite                 │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │  Auth    │ │ Courses  │ │Dashboard │ │   Landing    │  │  │
│  │  │  Pages   │ │  Pages   │ │  Pages   │ │    Page      │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  │  React Query · Tailwind CSS · shadcn/ui · ApexCharts      │  │
│  │  Orval-generated API clients (OpenAPI → TypeScript)       │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (JWT cookies)
┌──────────────────────────▼──────────────────────────────────────┐
│                   Django REST Framework                         │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────────────────┐ │
│  │  users   │ │     core     │ │         evaluation           │ │
│  │  Auth    │ │ Universities │ │  Assessments · Grades        │ │
│  │  JWT     │ │ Departments  │ │  LO/PO Mappings              │ │
│  │  Roles   │ │ Programs · PO│ │  Score Recompute Jobs        │ │
│  │  Profiles│ │ Courses · LO │ │  Enrollments                 │ │
│  └──────────┘ └──────────────┘ └──────────────────────────────┘ │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
┌──────▼──────┐  ┌────────▼────────┐  ┌──────▼──────────────┐
│  PostgreSQL │  │     Redis       │  │   Celery Worker     │
│  (primary)  │  │ (broker + cache │  │ Score recomputation │
│             │  │  + result BE)   │  │ Weight suggestion   │
└─────────────┘  └─────────────────┘  │ SentenceTransformers│
                                      └─────────────────────┘
```

### 3.2 Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Backend Framework** | Django + DRF | 5.2.8 / 3.16.1 | REST API, ORM, admin panel |
| **Authentication** | SimpleJWT | — | JWT with cookie-based transport, refresh rotation, token blacklisting |
| **Async Tasks** | Celery | — | Background score recomputation, weight suggestion |
| **Message Broker** | Redis | 7.x | Celery broker, result backend, caching layer |
| **Database** | PostgreSQL | 15 | Primary data store (SQLite for development) |
| **Frontend Framework** | React + TypeScript | 18 | UI components, routing, state |
| **Build Tool** | Vite | — | Dev server, production builds |
| **State Management** | React Query (TanStack) | — | Server state caching, mutation, polling |
| **API Client Gen** | Orval | — | Auto-generates TypeScript clients from OpenAPI schema |
| **Styling** | Tailwind CSS | — | Utility-first CSS |
| **UI Components** | shadcn/ui | — | Accessible, customizable component primitives |
| **Charts** | ApexCharts | — | Radar charts, bar charts, heatmaps |
| **AI/ML** | SentenceTransformers | — | all-MiniLM-L6-v2 for weight suggestion |
| **API Docs** | drf-spectacular | — | OpenAPI 3.0 schema generation |
| **Testing (BE)** | pytest + pytest-django | — | Unit, integration, workflow tests |
| **Testing (FE)** | Vitest + Testing Library | — | Component, integration tests |
| **Containerization** | Docker Compose | — | 5-service stack for consistent environments |
| **Package Mgmt (BE)** | uv | — | Fast Python dependency management |
| **Linting (BE)** | Ruff | — | Python linting and formatting |
| **Linting (FE)** | ESLint | — | TypeScript/React linting |

### 3.3 Core Domain Model

The data model is organized into three conceptual layers:

**Academic Structure Layer** — Defines the institutional hierarchy:

```
University (1) ──→ (*) Department (1) ──→ (*) Program (1) ──→ (*) Course
                                                       │
                                            DegreeLevel  Term
```

- **University:** Top-level institution (supports multi-tenancy via foreign key isolation)
- **Department:** Academic department within a university (e.g., Computer Engineering)
- **DegreeLevel:** Degree classification (BS, MS, PhD)
- **Program:** A degree program (e.g., Computer Science BS)
- **Term:** Academic semester (e.g., Fall 2025) — only one active at a time
- **Course:** A specific course offering within a program and term, with assigned instructors

**Outcomes Layer** — Defines educational objectives and their relationships:

```
ProgramOutcome (PO) ←──→ LearningOutcome (LO)
      │                        │
  (Program-level          (Course-level
   goals)                  objectives)
```

- **ProgramOutcome:** High-level skill defined for a program (e.g., "Ability to design and conduct experiments")
- **LearningOutcome:** Course-specific objective (e.g., "Implement CRUD operations using Django ORM")
- **LO↔PO Mapping:** Weighted link defining how much an LO contributes to each PO

**Evaluation Layer** — Captures assessment instruments and student performance:

```
Assessment ←──→ LearningOutcome    (Assessment↔LO Mapping)
    │
    └──→ StudentGrade    (per-student, per-assessment score)

CourseEnrollment    (student ↔ course)

StudentLearningOutcomeScore    (computed: Grade × Weight)
StudentProgramOutcomeScore     (aggregated: LO Score × LO↔PO Weight)
```

- **Assessment:** A graded item (midterm, final, project, homework, quiz, attendance, other)
- **StudentGrade:** Raw score a student received on an assessment
- **CourseEnrollment:** Links a student to a course (active/pending/dropped)
- **StudentLearningOutcomeScore:** Computed LO-level achievement per student
- **StudentProgramOutcomeScore:** Aggregated PO-level achievement across all enrolled courses

### 3.4 Score Calculation Flow

The calculation engine follows a deterministic weighted-aggregation pipeline:

```
Step 1: Per-Assessment Normalization
  For each Assessment A and Learning Outcome LO:
    mapping_weight = AssessmentLO_Mapping(A, LO).weight
    normalized_weight = mapping_weight / Σ(all mapping_weights for A)

Step 2: Learning Outcome Score per Student
  LO_Score(student, LO) = Σ [ grade(student, A) × assessment_weight(A) × normalized_weight(A, LO) ]
                           ────────────────────────────────────────────────────────────────
                           Σ [ assessment_weight(A) × normalized_weight(A, LO) ]
  (for all assessments A where mapping exists)

Step 3: Program Outcome Score per Student
  PO_Score(student, PO) = Σ [ LO_Score(student, LO) × LO_PO_Mapping(LO, PO).weight ]
                          ──────────────────────────────────────────────────────────
                          Σ [ LO_PO_Mapping(LO, PO).weight ]
  (for all LOs across all enrolled courses that map to PO)
```

This calculation is performed asynchronously via Celery. When grades are imported or modified, a `ScoreRecomputeJob` is created and dispatched. The Celery worker executes the computation and stores results in the `StudentLearningOutcomeScore` and `StudentProgramOutcomeScore` tables. The frontend polls job status and refreshes dashboards upon completion.

---

## 4. Core Functionality and Features

SES is designed around five user roles, each with distinct permissions, workflows, and dashboards.

### 4.1 Administrator

The Administrator is responsible for system setup and global management.

| Capability | Description |
|---|---|
| **User Management** | Create, view, update, and delete users; assign roles (student, instructor, program_head, admin) |
| **Academic Structure** | Define universities, departments, degree levels, programs, and academic terms |
| **Program Outcomes** | Create and maintain POs for each program and term with configurable weights |
| **Course Management** | Create courses, assign instructors, define terms |
| **File Import** | Bulk import program outcomes, learning outcomes, and student grades from Excel files |
| **System Monitoring** | View all score recomputation jobs, weight suggestion jobs, error logs |

The admin dashboard provides overview statistics: total users by role, active term information, recent import activity, and job status summaries.

### 4.2 Instructor

The Instructor is the primary content creator and evaluator.

| Capability | Description |
|---|---|
| **Course Dashboard** | View only courses they teach, with enrollment counts and assessment summaries |
| **Learning Outcomes** | Define LOs for each course with codes and descriptions |
| **LO↔PO Mapping** | Link course LOs to program-level POs with contribution weights (bulk-save modal) |
| **Assessment Management** | Create assessments (type, date, total score, weight); edit and delete |
| **Assessment↔LO Mapping** | Map each assessment to the LOs it evaluates with contribution weights |
| **AI Weight Suggestion** | Trigger AI-powered weight recommendations for assessment-LO and LO-PO mappings; review and approve before applying |
| **Grade Entry** | Enter scores manually or import via Excel; view grade distributions |
| **Student Analytics** | Per-student competency radar chart; per-LO heatmaps for entire class |
| **Course Templates** | Clone a course (with its LOs, assessments, and mappings) to a new term via template instantiation |

The instructor workflow is streamlined: from the course detail page, an instructor can see a radar grid showing class-wide LO achievement, identify weak outcomes, drill into specific assessments, and adjust weights or teaching strategies accordingly.

**AI Weight Suggestion Detail:**

When an instructor clicks "Suggest Weights," the system:
1. Extracts LO descriptions and assessment descriptions from the course
2. Creates a `WeightSuggestionJob` record (status: pending)
3. Dispatches a Celery task that loads the `all-MiniLM-L6-v2` SentenceTransformer model
4. Computes cosine similarity between assessment descriptions and LO descriptions
5. Normalizes similarity scores into suggested weight distributions
6. Optionally suggests LO↔PO weights using the same approach against Program Outcome descriptions
7. Returns results to the frontend, where the instructor can review, adjust, and approve

The embedding model is loaded once at Celery worker startup (via `worker_process_init` signal), eliminating ~8 seconds of cold-start latency on subsequent invocations. If the AI service is unavailable, the system degrades gracefully with a clear error message; instructors can always enter weights manually.

### 4.3 Program Head

The Program Head role was added in Semester 2 to provide institutional-level visibility.

| Capability | Description |
|---|---|
| **Program Dashboard** | View all courses and outcomes within their assigned program |
| **PO Achievement Overview** | Aggregated PO scores across all students and courses in the program |
| **Instructor Permissions** | Grant/revoke view, edit, or full-control permissions to instructors for specific resource areas (courses, programs, LOs, POs, assessments, students) |
| **Trend Analysis** | Term-over-term PO score comparison |
| **Accreditation Support** | Export-ready views of outcome achievement for ABET reporting |

### 4.4 Student

The Student role provides personal performance transparency.

| Capability | Description |
|---|---|
| **Enrollment Dashboard** | View all enrolled courses with current LO achievement status |
| **Grade History** | See scores on all completed assessments |
| **Competency Profile** | Interactive radar chart showing achievement level for each LO in a course |
| **PO Progress** | Aggregated PO scores across all enrolled courses for the current term |

### 4.5 Guest

The Guest role enables public exploration without authentication — valuable for prospective students researching programs.

| Capability | Description |
|---|---|
| **Public Landing Page** | Hero section, feature overview, role descriptions, live statistics |
| **Program Browser** | Browse available programs and their descriptions |
| **Course Explorer** | View public course details: description, learning outcomes, associated program outcomes |
| **No Student Data Access** | Guests cannot view any student information, scores, or performance data |

---

## 5. Key Technical Achievements

### 5.1 Asynchronous Score Processing with Celery + Redis

**Problem:** The Semester 1 MVP performed score calculation synchronously within the HTTP request cycle. For courses with hundreds of students and dozens of assessments, this could exceed request timeout thresholds and block the web server.

**Solution:** In Semester 2, we implemented a Celery-based asynchronous processing pipeline:

- A `ScoreRecomputeJob` model tracks each computation request with status (pending → running → success/failed), timestamps, and error information
- When grades are imported or modified, the system creates a job record and dispatches a Celery task (`recompute_course_scores_task`)
- The Celery worker picks up the task from the Redis broker, executes the calculation, and updates the job status
- The frontend polls job status via the `ScoreRecomputeJobViewSet` API and displays a global notification when the recomputation completes
- Jobs are retried up to 3 times with exponential backoff on failure

**Outcome:** The web server remains responsive during computation. Large file imports (thousands of grades) are processed reliably without timeout concerns.

### 5.2 AI-Assisted Weight Suggestion with Sentence Embeddings

**Problem:** Instructors must manually assign weights between assessments and learning outcomes — a tedious and error-prone task. For a course with 4 assessments and 5 LOs, that's 20 weight decisions. For LO↔PO mappings with 5 LOs and 7 POs, that's another 35. Design decisions in the Continuation Report initially considered a local LLM (Ollama), but practical constraints led to a more targeted approach.

**Solution:** We implemented a weight suggestion service using SentenceTransformers, an embedding-based approach:

- The `all-MiniLM-L6-v2` model (80 MB, 384-dimensional embeddings) is loaded once at Celery worker startup
- Assessment descriptions and LO descriptions are embedded into vector space
- Cosine similarity between embeddings produces initial weight suggestions
- The same pipeline handles LO↔PO suggestions by embedding LO descriptions against PO descriptions
- Suggestions are normalized to ensure weights sum appropriately
- The instructor always reviews and approves before weights are applied

**Why embeddings over LLM:**
- **Deterministic:** Same inputs produce same suggestions — reproducible and auditable
- **Lightweight:** 80 MB model vs multi-GB LLM; no GPU required
- **Privacy-preserving:** No data leaves the server; fully on-premise
- **Fast:** Single-digit millisecond inference after model load
- **Task-appropriate:** Weight suggestion is fundamentally a semantic similarity problem, which embedding models solve directly

The `WeightSuggestionJob` model provides full traceability — who requested, when, what was suggested, and whether the instructor applied or dismissed the suggestion.

### 5.3 File Import with Multi-Stage Validation

**Problem:** Instructors need to import grades from Excel files exported by university student information systems. These files often contain inconsistencies: missing student records, assessments not yet defined in the system, scores exceeding maximum values, or duplicate entries.

**Solution:** We built a comprehensive import pipeline:

| Stage | Description |
|---|---|
| **Structure Validation** | Verifies the Excel file has required columns (student ID, assessment columns) and is parseable |
| **Student Resolution** | Matches student IDs against the database; flags unknown students for resolution |
| **Assessment Resolution** | Matches assessment column headers against defined assessments; flags unknown assessments |
| **Score Validation** | Checks scores are non-negative and do not exceed assessment maximums |
| **Duplicate Detection** | Identifies duplicate rows and conflicting entries |
| **Resolution Flow** | Interactive modal UI where instructors resolve conflicts: create new students, map columns to assessments, correct scores |

The frontend resolution modal presents issues in categorized tabs with clear action buttons. Resolved data is persisted in a single transaction. After import, the system automatically triggers a score recomputation job.

Supported file imports:
- `POST /core/file-import/assignment-scores/` — Student grades
- `POST /core/file-import/learning-outcomes/` — Learning outcome definitions
- `POST /core/file-import/program-outcomes/` — Program outcome definitions

### 5.4 Course Template System

**Problem:** The same course is offered in multiple terms. Manually recreating learning outcomes, assessments, and outcome mappings each term is repetitive and error-prone.

**Solution:** We implemented a template cloning system:

1. **CourseTemplate** stores the canonical definition: name, code, credits, program
2. **CourseTemplateLearningOutcome** and **CourseTemplateAssessment** store template-level LOs and assessments
3. **CourseTemplateAssessmentLOMapping** and **CourseTemplateLOPOMapping** store mapping relationships
4. The `instantiate` API endpoint clones a template into a new Course with all associated LOs, assessments, and mappings for a target term
5. The cloned Course maintains a `course_template` foreign key for traceability

### 5.5 Instructor Permission Management

**Problem:** By default, instructors could only access their own courses. Some institutional workflows require instructors to view or edit resources across courses (e.g., a senior instructor reviewing all program outcomes).

**Solution:** We implemented a granular permission system:

- **Resource Areas:** courses, programs, learning_outcomes, program_outcomes, students, lo_po_weights, assessment_lo_weights, assessments, course_templates
- **Permission Tiers:** view, edit, full (full control includes delete)
- **Granting Authority:** Program heads grant permissions to instructors for their program's resources
- **Auto-creation:** When a course is created and instructors are assigned, view permissions are automatically created for those instructors on that course
- **API Enforcement:** Custom DRF permission classes (`IsInstructorOrAdmin`, `IsOwnerOrInstructorOrAdmin`) check granted permissions before allowing access

### 5.6 Authentication and Security

| Feature | Implementation |
|---|---|
| **JWT Authentication** | SimpleJWT with 1-hour access tokens, 7-day refresh tokens |
| **Cookie-based Transport** | Tokens stored in HTTP-only cookies (not localStorage) for XSS protection |
| **Token Blacklisting** | Refresh token rotation with blacklisting on use |
| **Role-Based Access** | Five roles enforced at view, serializer, and permission class levels |
| **CORS Configuration** | Environment-controlled allowed origins |
| **File Upload Limits** | Configurable maximum upload size via `MAX_UPLOAD_SIZE_MB` |
| **Rate Limiting** | Login: 5/min; file uploads: 10/min; general API: 60/min per user |
| **Data Isolation** | All models scoped via foreign keys; multi-tenant ready |

---

## 6. Evolution from MVP

The system underwent significant transformation between Semester 1 (MVP) and Semester 2. This section documents the key design evolution.

### 6.1 Architectural Changes

| Aspect | Semester 1 MVP | Semester 2 Final |
|---|---|---|
| **Score Calculation** | Synchronous in request cycle | Async via Celery + Redis |
| **Database** | SQLite (dev only) | PostgreSQL (production-ready) |
| **AI Assistance** | Not implemented | SentenceTransformers embedding model |
| **Course Reuse** | Manual recreation per term | Template system with one-click cloning |
| **Instructor Permissions** | Basic role checks only | Granular resource-area × tier matrix |
| **File Import** | Basic upload with minimal validation | Multi-stage pipeline with resolution UI |
| **User Roles** | admin, instructor, student, guest | Added program_head with dedicated dashboard |
| **API Documentation** | Manual | Auto-generated OpenAPI 3.0 schema; Orval TypeScript clients |

### 6.2 Design Decisions

**Embedding Model vs. LLM for Weight Suggestion**

The Continuation Report proposed using a local LLM (Ollama) for weight recommendations. During Semester 2 implementation, we evaluated this against an embedding-based approach and chose SentenceTransformers for the following reasons:

1. **Deterministic outputs:** Embedding-based similarity produces consistent results for the same inputs, which is important for an academic tool where reproducibility matters. LLMs produce variable outputs even with the same prompt.
2. **Resource efficiency:** The `all-MiniLM-L6-v2` model is 80 MB compared to 4+ GB for a usable LLM. It runs on CPU with no GPU requirement.
3. **Task fit:** Weight suggestion is a semantic similarity problem (how related is "Midterm Exam: Tests algorithm design skills" to "LO3: Apply algorithmic problem solving"?). Embedding models are purpose-built for this.
4. **Privacy:** No data leaves the server. The model runs entirely within the Celery worker process.

**Program Head Role Introduction**

The Semester 1 MVP had a flat role structure (admin, instructor, student, guest). Analysis of real academic workflows revealed a missing role: the department/program head who needs program-wide visibility without full admin privileges. We added:

- A `ProgramHeadProfile` model linked one-to-one with a program
- A dedicated dashboard showing PO achievement across all courses
- The ability to grant granular permissions to instructors

**Course Template Design**

Rather than implementing a full versioning system (which would add significant complexity), we chose a simple clone-on-instantiate pattern. Templates store canonical definitions; instantiating creates a fully independent copy. This is sufficient for the primary use case (offering the same course in a new term) while avoiding complex merge/update semantics.

---

## 7. Testing and Validation

### 7.1 Testing Strategy

SES employs a multi-layered testing strategy:

| Layer | Technology | Scope |
|---|---|---|
| **Backend Unit Tests** | pytest + pytest-django | Models, serializers, services, validators |
| **Backend Integration Tests** | pytest + pytest-django | API endpoints, authentication workflows, file import pipeline |
| **Backend Workflow Tests** | pytest | End-to-end scenarios: course creation → enrollment → grade entry → score calculation |
| **Frontend Component Tests** | Vitest + React Testing Library | Page rendering, user interactions, form submissions |
| **Frontend Integration Tests** | Vitest + MSW | API mocking, routing, state management |
| **Frontend Workflow Tests** | Vitest | Import modal flow, resolution modal interaction |

### 7.2 Test Coverage

**Backend:** 28 test files covering:

| Test Module | Focus Area |
|---|---|
| `test_models.py` | Model constraints, validations, unique constraints |
| `test_serializers.py` | Serializer validation, nested serializers |
| `test_views.py` | API endpoint responses, status codes, pagination |
| `test_auth_workflow.py` | Login, refresh, role-based access |
| `test_course_setup_workflow.py` | Course → LO → Assessment → Mapping creation |
| `test_grade_workflow.py` | Grade entry, validation, score computation |
| `test_evaluation.py` | Assessment-LO mapping, score recalculation |
| `test_file_import_parser.py` | Excel parsing, column detection |
| `test_file_import_validator.py` | Structure, student, assessment, score validation |
| `test_file_import_service.py` | End-to-end import pipeline |
| `test_file_import_endpoints.py` | Import API endpoints |
| `test_file_import_policy.py` | Role-based import access |
| `test_weight_suggestion.py` | Suggestion computation logic |
| `test_weight_suggestion_tasks.py` | Celery task dispatch and result handling |
| `test_weight_suggestion_endpoint.py` | Suggestion API endpoints |
| `test_course_templates.py` | Template creation and instantiation |
| `test_permission_workflow.py` | Permission granting and enforcement |
| `test_permissions.py` | Custom permission class logic |
| `test_head_api.py` | Program Head API endpoints |
| `test_analytics.py` | Analytics calculation and endpoints |
| `test_seed_data.py` | Seed data integrity |
| `test_api_versioning.py` | API version routing |
| `test_exception_handler.py` | Error response format |
| Plus 6 additional test modules | Serializer permissions, user permissions, etc. |

Coverage target: **70%+** line coverage (enforced via pytest-cov).

**Frontend:** 16 test files covering:

- Landing page components (Navbar, Hero, Feature sections, LiveStats, EmbeddedDemo)
- Login page (form validation, error handling, redirect)
- Dashboard routing (correct dashboard per role)
- Dashboard analytics (chart rendering, data display)
- Course pages (listing, detail, CRUD)
- File upload modal (upload, progress, resolution)
- Resolution modals (conflict resolution UI)
- Settings security (password change form)
- App routes (route protection, redirects)
- MSW mock API (mock server configuration)

### 7.3 Quality Gates

| Gate | Tool | Threshold |
|---|---|---|
| Backend Linting | Ruff | Complexity limit: 10; Line length: 127 |
| Backend Formatting | Ruff | Enforced format check |
| Backend Coverage | pytest-cov | ≥ 70% |
| Frontend Linting | ESLint | TypeScript strict mode |
| Frontend Testing | Vitest | All tests must pass |
| Pre-commit | pre-commit hooks | Ruff, ESLint run before commit |

### 7.4 Validation Methodology

Beyond automated testing, the system was validated through:

1. **Workflow scenario testing:** Complete end-to-end scenarios (admin creates university → program → term → course → instructor defines LOs → maps to POs → creates assessments → imports student grades → system computes scores → student views dashboard → program head views analytics)
2. **Edge case testing:** Empty courses, courses with no assessments, students with no grades, POs with no mappings, weight sums not equal to 1.0
3. **Load testing:** Bulk imports with 500+ students and 10+ assessments verified through Celery async processing
4. **Client review:** Regular demonstrations to Prof. Dr. Ahmet Bulut with iterative feedback incorporation

---

## 8. Ethical, Social, and Professional Considerations

### 8.1 Privacy and Data Protection

SES handles sensitive student academic data and is designed with privacy-by-default principles:

| Principle | Implementation |
|---|---|
| **Data Minimization** | Only fields necessary for outcome calculation are collected; no unnecessary personal data |
| **Role-Based Access** | Five-tier role system ensures users see only data relevant to their function |
| **Secure Transport** | JWT tokens in HTTP-only cookies; all API communication over HTTPS in production |
| **Access Logging** | Authentication events (login, logout, refresh) are tracked with timestamps and IP addresses |
| **Data Retention** | Academic records retained per institutional policy; account deactivation supported |

While full KVKK/GDPR compliance workflows (explicit consent management, data portability exports, right-to-erasure automation) are documented in the system design for future implementation phases, the current architecture's data isolation model and role-based access control provide the foundational security posture required by these regulations.

### 8.2 Algorithmic Transparency

The score calculation engine is **fully deterministic** — given the same inputs (grades, weights, mappings), it always produces the same outputs. The formulas are documented in Section 3.4 and implemented in `backend/evaluation/services.py`. No "black box" decisions affect student scores.

The AI weight suggestion system is similarly transparent:

- Based on cosine similarity between text embeddings — a well-understood mathematical operation
- Suggestions are **advisory only**; instructors review and approve before application
- The SentenceTransformer model (`all-MiniLM-L6-v2`) is open-source and publicly documented
- All suggestions are logged with the requesting user and timestamp for auditability

### 8.3 Professional Standards

| Standard | Relevance | SES Compliance |
|---|---|---|
| **ABET Criterion 4** | Continuous improvement through outcome assessment | Core functionality: PO tracking enables data-driven curriculum improvement |
| **ABET Criterion 3** | Student outcomes definition and measurement | SES maps every assessment to defined outcomes with weighted contributions |
| **WCAG 2.1 Level AA** | Web accessibility | Semantic HTML; ARIA labels; keyboard-navigable modals; sufficient color contrast via Tailwind design tokens |
| **ISO/IEC 27001** | Information security management | JWT auth, role-based access, database isolation, environment-based secrets, rate limiting |
| **IEEE 830** | Software requirements specification | User stories documented across five roles; API contract versioned and auto-documented |

### 8.4 Societal Impact

**Positive contributions:**

- **Fairer evaluation:** By measuring against defined outcomes rather than relative class ranking, SES provides a more objective picture of student competency
- **Early intervention:** LO-level analytics allow instructors to identify struggling students before final exams, enabling timely academic support
- **Accreditation efficiency:** Automating outcome reporting reduces administrative burden on faculty, freeing time for teaching and research
- **Program transparency:** The Guest portal allows prospective students and their families to understand what competencies a program develops before enrolling
- **Curriculum improvement:** Program heads can identify which POs are consistently underachieved and adjust curricula accordingly

**Considerations addressed:**

- The system is designed as a **supportive tool**, not a surveillance mechanism. Student data is contextualized with constructive analytics, not punitive metrics
- Score calculations are **transparent and auditable** — no student's academic standing is affected by an opaque algorithm
- The embedding model is **not used for student evaluation** — it only suggests weights between assessments and outcomes, which instructors approve

### 8.5 Lifelong Learning

Throughout this two-semester project, the team engaged in continuous skill development:

- **Technical growth:** Deepened expertise in Django REST Framework, React/TypeScript, Celery distributed task queues, Redis, Docker containerization, and NLP/embedding models
- **Process adoption:** Implemented test-driven development, pre-commit quality gates, auto-generated API documentation, and CI/CD pipelines via GitHub Actions
- **Domain knowledge:** Studied ABET accreditation criteria, outcome-based education frameworks, and Turkish higher education regulations (KVKK)
- **Professional development:** Practiced client communication, iterative demo cycles, and technical documentation writing
- **Community engagement:** Leveraged open-source libraries (Django, React, SentenceTransformers, Celery) and contributed bug reports

---

## 9. Conclusion

The Student Evaluation System successfully delivers a complete outcome-based assessment platform that bridges the gap between day-to-day grading and institutional accreditation requirements. Over two semesters, the system evolved from a functional MVP into a production-ready platform with asynchronous processing, AI-assisted weight suggestions, and comprehensive role-based workflows.

The project demonstrates that modern web technologies — when applied through a focused, user-centered design process — can transform tedious academic administration into streamlined, data-driven processes. Instructors are freed from manual spreadsheet calculations. Program heads gain real-time visibility into program effectiveness. Students receive transparent, actionable feedback on their competency development.

Key outcomes of this project include:

1. A fully containerized, five-service application stack deployable with a single `docker compose up --build` command
2. An automated calculation engine processing the complete Assessment → Learning Outcome → Program Outcome score pipeline
3. An AI-assisted weight suggestion system using sentence embeddings that respects data privacy by running entirely on-premise
4. A comprehensive test suite (44+ test files across backend and frontend) ensuring reliability
5. Auto-generated, versioned API documentation enabling consistent frontend-backend integration

The system is ready to support departmental deployment at Acıbadem University's Computer Engineering program, with architecture designed to scale to additional programs and institutions through its multi-tenant data model.

---

## 10. References

### Frameworks and Libraries

1. Django Software Foundation. (2024). *Django Documentation (v5.2)*. https://docs.djangoproject.com/
2. Encode. (2024). *Django REST Framework (v3.16)*. https://www.django-rest-framework.org/
3. Meta Platforms, Inc. (2024). *React Documentation (v18)*. https://react.dev/
4. Celery Project. (2024). *Distributed Task Queue*. https://docs.celeryq.dev/
5. Reimers, N. & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. https://www.sbert.net/
6. Vite Contributors. (2024). *Vite Documentation*. https://vitejs.dev/
7. TanStack. (2024). *React Query*. https://tanstack.com/query/
8. Orval. (2024). *API Client Generation*. https://orval.dev/
9. T. F. F. (2024). *drf-spectacular — OpenAPI 3.0 schema generation for Django REST Framework*. https://drf-spectacular.readthedocs.io/
10. Redis Ltd. (2024). *Redis Documentation*. https://redis.io/docs/
11. PostgreSQL Global Development Group. (2024). *PostgreSQL 15 Documentation*. https://www.postgresql.org/docs/15/

### Standards and Compliance

12. ABET. (2024). *Criteria for Accrediting Engineering Programs*. https://www.abet.org/
13. Kişisel Verileri Koruma Kurumu (KVKK). (2024). *Turkish Data Protection Law No. 6698*. https://www.kvkk.gov.tr/
14. European Union. (2016). *General Data Protection Regulation (GDPR) 2016/679*.
15. W3C. (2024). *Web Content Accessibility Guidelines (WCAG) 2.1*. https://www.w3.org/TR/WCAG21/
16. ISO/IEC. (2022). *ISO/IEC 27001:2022 Information Security Management*.

### Development Tools

17. pytest. (2024). *pytest Documentation*. https://docs.pytest.org/
18. Vitest. (2024). *Vitest Documentation*. https://vitest.dev/
19. Astral. (2024). *uv — Fast Python Package Manager*. https://docs.astral.sh/uv/
20. Astral. (2024). *Ruff — Python Linter*. https://docs.astral.sh/ruff/
21. Tailwind CSS. (2024). *Utility-First CSS Framework*. https://tailwindcss.com/

---

## 11. Client Approval

**Client Information:**

- **Name:** Prof. Dr. Ahmet Bulut
- **Position:** Head of Department, Computer Engineering
- **Institution:** Acıbadem University
- **Date:** _______________
- **Signature:** _______________

---

*End of Final Report*
