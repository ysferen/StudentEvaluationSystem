# Student Evaluation System - AI Agent Guide

> DEPRECATION NOTICE
>
> This file is now legacy documentation.
>
> Active agent context is maintained in `.github/copilot-instructions.md` and loaded automatically for agent sessions.
>
> Planned cleanup: this file is intended to be removed after migration is complete.

## AGENTS.md Removal Checklist

Before deleting this file, verify all items below:

1. `.github/copilot-instructions.md` fully covers architecture, workflows, quality gates, and roadmap guidance.
2. No CI workflow, script, or tool in the repository references `AGENTS.md`.
3. Human-facing docs (`README.md`, `backend/README.md`) remain sufficient for developer onboarding.
4. Team confirms no external process depends on this file.

If all items pass, remove `AGENTS.md` in a dedicated cleanup change.

This document provides comprehensive information about the Student Evaluation System project for AI coding agents.

## Project Overview

The Student Evaluation System is a comprehensive academic evaluation platform built with Django REST Framework and React. It enables educational institutions to track student performance through weighted assessments and measure achievement against course and program outcomes.

### Key Domain Concepts

- **Program Outcomes (POs)**: High-level learning outcomes defined at the program level
- **Learning Outcomes (LOs)**: Course-level outcomes that map to Program Outcomes
- **Assessments**: Exams, homework, projects, etc. that evaluate Learning Outcomes
- **Weight Mappings**:
  - Assessments → Learning Outcomes (how much each assessment contributes to an LO)
  - Learning Outcomes → Program Outcomes (how much each LO contributes to a PO)
- **Score Calculation**: Automated calculation of student scores based on assessment grades and weight mappings

## Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Programming language |
| Django | 5.2.8 | Web framework |
| Django REST Framework | 3.16.1 | API framework |
| Django REST Framework SimpleJWT | 5.5.1 | JWT authentication |
| drf-spectacular | 0.29.0 | OpenAPI schema generation |
| pandas | 2.3.3 | Excel/CSV file processing |
| django-cors-headers | 4.9.0 | CORS handling |
| environs | 14.5.0 | Environment variable management |
| pytest/pytest-django | 8.3.4/4.9.0 | Testing framework |
| factory-boy | 3.3.1 | Test data factories |
| flake8 | 7.1.1 | Code linting |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2.0 | UI framework |
| TypeScript | 4.9.3 | Type safety |
| Vite | 4.1.0 | Build tool |
| React Query (TanStack) | 5.90.12 | Server state management |
| React Router | 6.8.1 | Client-side routing |
| Axios | 1.3.4 | HTTP client |
| Orval | 7.13.2 | API client generation from OpenAPI |
| Tailwind CSS | 3.2.7 | Styling |
| ApexCharts | 4.0.0 | Data visualization |
| @dnd-kit | 6.3.1 | Drag and drop functionality |
| Vitest | 4.0.16 | Testing framework |
| MSW | 2.12.7 | API mocking for tests |

## Project Structure

```
StudentEvaluationSystem/
├── backend/                              # Django backend
│   ├── requirements.txt                  # Python dependencies
│   ├── Dockerfile                        # Backend container config
│   └── student_evaluation_system/        # Django project root
│       ├── manage.py
│       ├── student_evaluation_system/    # Project settings
│       │   ├── settings.py
│       │   ├── urls.py
│       │   └── wsgi.py
│       ├── core/                         # Core models and logic
│       │   ├── models.py                 # Academic structure models
│       │   ├── serializers.py
│       │   ├── views.py
│       │   ├── urls.py
│       │   └── services/                 # Business logic
│       │       ├── file_import.py        # Excel/CSV import
│       │       └── validation.py
│       ├── evaluation/                   # Assessment & grading
│       │   ├── models.py                 # Assessments, grades
│       │   ├── serializers.py
│       │   ├── views.py
│       │   ├── urls.py
│       │   └── services.py               # Score calculation
│       └── users/                        # User management
│           ├── models.py                 # CustomUser, profiles
│           ├── serializers.py
│           ├── views.py
│           └── urls.py
├── frontend/                             # React frontend
│   ├── package.json                      # Node dependencies
│   ├── vite.config.ts                    # Vite configuration
│   ├── orval.config.cjs                  # API client generation
│   ├── Dockerfile                        # Frontend container config
│   ├── nginx.conf                        # Nginx config for prod
│   └── src/
│       ├── App.tsx                       # Main app component
│       ├── main.tsx                      # Entry point
│       ├── types.ts                      # TypeScript interfaces
│       ├── api/
│       │   ├── mutator.ts                # Axios instance + interceptors
│       │   ├── generated/                # Auto-generated API clients
│       │   └── model/                    # Auto-generated TypeScript models
│       ├── components/                   # Reusable UI components
│       ├── pages/                        # Page-level components
│       │   ├── Login.tsx
│       │   ├── Dashboard.tsx
│       │   ├── StudentDashboard.tsx
│       │   ├── InstructorDashboard.tsx
│       │   ├── HeadDashboard.tsx
│       │   ├── CourseDetail.tsx
│       │   └── ...
│       └── hooks/                        # Custom React hooks
├── .github/workflows/                    # CI/CD pipelines
│   ├── backend-ci.yml                    # Backend lint/migrations
│   ├── backend-test.yml                  # Backend tests
│   ├── frontend-ci.yml                   # Frontend lint/build
│   ├── frontend-test.yml                 # Frontend tests
│   ├── docker-build.yml                  # Docker image builds
│   └── codeql.yml                        # Security scanning
├── .ai-agents/                           # AI agent documentation
│   ├── IMPLEMENTATION_PLAN.md            # Detailed improvement plans
│   └── README.md                         # AI agents directory guide
├── .clinerules/                          # Cline IDE rules
│   └── PROJECT_RULES.md                  # Project conventions
└── run.bat                               # Windows dev server launcher
```

## Backend Architecture

### Django Apps

1. **core** - Academic structure and outcomes
   - `Term`, `University`, `Department`, `DegreeLevel`, `Program`
   - `Course`, `ProgramOutcome`, `LearningOutcome`
   - `LearningOutcomeProgramOutcomeMapping` (LO-PO weights)
   - `StudentLearningOutcomeScore`, `StudentProgramOutcomeScore`
   - File import services (Excel/CSV)

2. **evaluation** - Assessments and grading
   - `Assessment`, `AssessmentLearningOutcomeMapping`
   - `StudentGrade`, `CourseEnrollment`
   - Score calculation services

3. **users** - User management
   - `CustomUser` (with roles: guest, student, instructor, admin)
   - `StudentProfile`, `InstructorProfile`
   - JWT authentication endpoints

### Authentication

- JWT-based authentication using Django REST Framework SimpleJWT
- Token rotation and blacklisting enabled
- Access token lifetime: 1 hour
- Refresh token lifetime: 7 days
- Role-based access control (RBAC)

### API Documentation

- OpenAPI 3.0 schema auto-generated by drf-spectacular
- Schema endpoint: `/api/schema/`
- Swagger UI: `/api/docs/`
- Frontend API clients auto-generated from schema using Orval

### Key Backend Patterns

1. **Serializers with Validation**: All serializers include proper validation
2. **Service Layer**: Business logic isolated in `services.py` files
3. **Model Constraints**: Database-level constraints for data integrity
4. **Bulk Operations**: Efficient handling of large datasets (file imports)
5. **Score Recalculation**: Automated when grades are created/updated

## Frontend Architecture

### Routing Structure

```
/login                    → Login page
/student                  → Student dashboard
/student/courses          → Student's enrolled courses
/student/courses/:id      → Course detail (student view)
/instructor               → Instructor dashboard
/instructor/courses       → Instructor's courses
/instructor/course/:id    → Course management
/head                     → Department head dashboard
/head/courses             → All department courses
/head/course/:id          → Course oversight
/settings                 → User settings
/security                 → Security settings
```

### State Management

- **React Query** for server state (caching, background updates)
- **Local state** via React hooks for UI state
- **localStorage** for JWT tokens

### API Integration

- Orval generates TypeScript clients from backend OpenAPI schema
- Custom mutator (`api/mutator.ts`) configures Axios interceptors
- Automatic token injection and 401 handling

### Key Frontend Patterns

1. **Lazy Loading**: All pages loaded via `React.lazy()` for code splitting
2. **Role-Based Layouts**: Different navigation based on user role
3. **Generated API Clients**: Type-safe API calls from OpenAPI schema
4. **Error Boundaries**: Graceful error handling

## Development Workflow

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Backend Development

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cd student_evaluation_system
python manage.py migrate
python manage.py runserver
```

Backend runs at: `http://localhost:8000/`

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173/`

### Quick Start (Windows)

```bash
run.bat  # Starts both backend and frontend in separate windows
```

### API Client Regeneration

After changing backend serializers or views:

```bash
cd frontend
npm run generate:api  # One-time generation
npm run generate:api:watch  # Watch mode
```

This regenerates TypeScript clients from the OpenAPI schema at `backend/student_evaluation_system/schema.yml`.

## Build and Deployment

### Backend Production Build

```bash
cd backend/student_evaluation_system
pip install -r ../requirements.txt
python manage.py collectstatic
python manage.py migrate
gunicorn --bind 0.0.0.0:8000 student_evaluation_system.wsgi:application
```

### Frontend Production Build

```bash
cd frontend
npm ci
npm run build
```

Output is in `frontend/dist/` directory.

### Docker Deployment

```bash
# Build backend image
docker build -t ses-backend ./backend

# Build frontend image
docker build -t ses-frontend ./frontend

# Or use docker-compose (if available)
docker-compose up --build
```

## Testing

### Backend Tests

```bash
cd backend/student_evaluation_system
pytest
pytest --cov=student_evaluation_system  # With coverage
```

### Frontend Tests

```bash
cd frontend
npm run test           # Run tests in watch mode
npm run test:ui        # Run with Vitest UI
npm run test:coverage  # Generate coverage report
```

### Test Files Location

- Backend: Look for `test*.py` files in app directories
- Frontend: `frontend/src/pages/__tests__/` and `*.test.ts` files

## Code Style Guidelines

### Python (Backend)

- **Linting**: flake8
- **Line length**: 127 characters max
- **Complexity**: max 10
- Follow PEP 8 conventions
- Use type hints where appropriate

### TypeScript (Frontend)

- **Linting**: ESLint with TypeScript parser
- **Formatting**: Consistent with existing code style
- **Types**: Always use explicit types for function parameters and returns
- **Components**: Functional components with hooks

### Naming Conventions

- **Python**: `snake_case` for variables/functions, `PascalCase` for classes
- **TypeScript**: `camelCase` for variables/functions, `PascalCase` for components/types
- **Files**: `snake_case.py` for backend, `PascalCase.tsx` for React components

## CI/CD Pipelines

All workflows in `.github/workflows/`:

| Workflow | Triggers | Purpose |
|----------|----------|---------|
| backend-ci.yml | push/PR to main/dev | Linting, Django system check, migration check |
| backend-test.yml | push/PR to main/dev | Run pytest with coverage |
| frontend-ci.yml | push/PR to main/dev | ESLint, TypeScript check, build |
| frontend-test.yml | push/PR to main/dev | Run Vitest with coverage |
| docker-build.yml | push to main | Build and push Docker images |
| codeql.yml | Weekly, push to main | Security analysis |
| python-security.yml | push/PR to main/dev | Python security scanning |

## Security Considerations

### Authentication & Authorization

- JWT tokens with rotation and blacklisting
- All API endpoints require authentication (except login/register)
- Role-based permissions enforced at API level

### File Uploads

- File type validation (Excel, CSV only)
- File size limits
- Server-side parsing only (never execute uploaded files)
- Temporary files cleaned up after processing

### Data Access

- Students can only see their own data
- Instructors can only access their courses
- Admins have full access
- All data access filtered by user permissions

### API Security

- CORS configured for specific origins only
- CSRF protection enabled
- XSS protection headers
- No sensitive data in URL parameters

## Common Development Tasks

### Adding a New API Endpoint

1. Define URL pattern in app's `urls.py`
2. Create view in `views.py` using DRF viewsets or APIView
3. Create/update serializer in `serializers.py`
4. Add permission classes as needed
5. Regenerate frontend API clients: `npm run generate:api`
6. Add frontend code to use the new endpoint

### Adding a New Model

1. Define model in app's `models.py` with proper fields and constraints
2. Create and run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
3. Create serializer for the model
4. Add to admin if needed: `admin.py`
5. Create/update views for CRUD operations

### Adding a New Page

1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Add to navigation in appropriate layout component
4. Use generated API hooks for data fetching

## Environment Variables

### Backend
Create `.env` file in `backend/student_evaluation_system/`:

```
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
DATABASE_URL=sqlite:///db.sqlite3  # Or PostgreSQL/MySQL URL
```

### Frontend
Create `.env.development` and `.env.production` in `frontend/`:

```
VITE_API_URL=http://localhost:8000
VITE_PORT=5173
VITE_APP_VERSION=1.0.0
VITE_ENABLE_DEBUG=true
```

## Completed Major Improvements

### Security & Configuration (Batch 1)
- Environment variable configuration with `environs` library
- Rate limiting: 5/min for login, 10/min for file uploads using `django-ratelimit`
- Input validation and sanitization for XSS/SQL injection protection

### Permissions & Performance (Batch 2)
- Custom permission classes: `IsAdmin`, `IsInstructorOrAdmin`, `IsOwnerOrInstructorOrAdmin`
- Role-based access control applied to all viewsets
- N+1 query fixes in score calculation with `select_related`/`prefetch_related`
- Database indexes on frequently queried fields
- Global exception handler for consistent API error responses

### Testing (Batch 3)
- Factory-boy factories for all models (User, Course, Assessment, etc.)
- Permission tests (6 test cases)
- Service unit tests (12 test cases)
- Pytest configuration with 70% coverage threshold
- All 31 tests passing

### Frontend Improvements (Batch 4)
- Environment configuration: `.env.development`, `.env.production`, `.env.example`
- Error Boundary component for graceful error handling
- Loading skeleton components for consistent loading states
- React Query optimization with retry and staleTime configuration

## Known Issues & Limitations

1. **File Import**: Large Excel files (>10MB) may require increased timeout
2. **Score Calculation**: Currently synchronous; large courses may take time
3. **Real-time Updates**: Uses polling, not WebSockets
4. **Browser Support**: Modern browsers only (ES2020+)

## Documentation References

- **Implementation Plans**: `.ai-agents/IMPLEMENTATION_PLAN.md`
- **Project Rules**: `.clinerules/PROJECT_RULES.md`
- **API Documentation**: Run backend and visit `/api/docs/`
- **Component Documentation**: Inline JSDoc comments

## Support & Resources

- Django Docs: https://docs.djangoproject.com/en/5.2/
- DRF Docs: https://www.django-rest-framework.org/
- React Query Docs: https://tanstack.com/query/latest
- Orval Docs: https://orval.dev/
- Tailwind Docs: https://tailwindcss.com/docs

---

**Last Updated**: February 20, 2026
**Project Version**: 1.1.0
**Maintainer**: AI Agents should update this file when making architectural changes
