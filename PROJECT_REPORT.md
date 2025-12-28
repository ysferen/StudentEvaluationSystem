# Student Evaluation System (SES) - Project Report

**Team Name:** `[TODO: ENTER TEAM NAME]`
**Team Members:** `[TODO: ENTER TEAM MEMBERS]`
**GitHub Repository:** `[TODO: ENTER REPO URL]`

---

## Section 1: Introduction

The Student Evaluation System (SES) is a comprehensive outcome-based academic assessment platform designed to track, measure, and analyze student performance through a hierarchical assessment structure.

### Key Features:

1. **Outcome-Based Assessment Tracking**
   - Assessment → Learning Outcome → Program Outcome mapping
   - Weighted score calculations (configurable weights)
   - Automatic score recalculation on data changes

2. **Role-Based Access Control**
   - **Students**: View personal grades, LO/PO scores, course progress
   - **Instructors**: Manage courses, create assessments, import grades
   - **Department Heads**: Overview of program outcomes
   - **Administrators**: Full system management

3. **Bulk Data Import**
   - Excel file processing (Turkish language support)
   - Comprehensive validation before import
   - Support for assignment scores, learning outcomes, and program outcomes

4. **Analytics Dashboard**
   - Student performance tracking across courses
   - Course-level statistics and averages
   - Learning outcome achievement analysis
   - Program outcome attainment metrics

5. **Academic Structure Management**
   - Multi-level hierarchy: University → Department → Program → Course
   - Term-based organization
   - Flexible instructor assignment

### Technology Stack:
- **Backend**: Django 5.2.8, Django REST Framework, PostgreSQL
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Authentication**: JWT (SimpleJWT) with token rotation
- **Data Processing**: Pandas for Excel file handling
- **API Documentation**: drf-spectacular (OpenAPI 3.0)

---

## Section 2: System Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Pages      │  │  Components  │  │   Services   │        │
│  │              │  │              │  │              │        │
│  │ - Dashboard  │  │ - Forms      │  │ - API calls  │        │
│  │ - Courses    │  │ - Charts     │  │ - Auth       │        │
│  │ - Analytics  │  │ - Tables     │  │ - Queries    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              React Query (State Management)          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/HTTPS (REST API)
                            │ JWT Authentication
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (Django)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 REST Framework (API)                     │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐       │  │
│  │  │   Core     │  │ Evaluation │  │   Users    │       │  │
│  │  │   App      │  │    App     │  │    App     │       │  │
│  │  └────────────┘  └────────────┘  └────────────┘       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Business Logic Layer                        │  │
│  │  - Score Calculation Services                           │  │
│  │  - File Import Services (Pandas)                        │  │
│  │  - Validation Services                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Django ORM (Data Access)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ SQL Queries
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE (PostgreSQL)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     Tables                                │  │
│  │  Universities, Departments, Programs, Courses            │  │
│  │  ProgramOutcomes, LearningOutcomes                        │  │
│  │  Assessments, StudentGrades                               │  │
│  │  LO-PO Mappings, Assessment-LO Mappings                   │  │
│  │  StudentLOScores, StudentPOScores                         │  │
│  │  Users, Profiles, Enrollments                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interactions:

1. **Authentication Flow**:
   - Frontend sends credentials to `/api/users/auth/login/`
   - Backend validates and returns JWT access + refresh tokens
   - Frontend stores tokens and includes in subsequent requests
   - Access token expires after 1 hour, automatically refreshed via Axios interceptor
   - Refresh token rotation enabled for security (old tokens blacklisted)

2. **Grade Import Flow**:
   - Frontend uploads Excel file via `/api/core/file-import/assignment-scores/upload/`
   - Backend validates file format and structure
   - Pandas parses Excel with explicit dtype mappings
   - Transaction atomic: validates students, assessments, score ranges
   - Bulk creates/updates StudentGrade records
   - Triggers score recalculation for affected courses
   - Returns summary of created/updated/error counts

3. **Score Calculation Flow**:
   - StudentGrade → AssessmentLearningOutcomeMapping (weighted) → StudentLOScore
   - StudentLOScore → LearningOutcomeProgramOutcomeMapping (weighted) → StudentPOScore
   - Calculations use Django aggregation functions
   - Results stored in pre-computed tables for fast retrieval

### Class/Object Diagram:

```
┌─────────────────┐
│   CustomUser    │
│  (AbstractUser) │
├─────────────────┤
│ - id            │──┐
│ - role          │  │
│ - first_name    │  │
│ - last_name     │  │
└─────────────────┘  │       1
       │             │       │
       │ inherits    │       │ 1..*
       │             │       ▼
       │       ┌─────────────────┐       1      1..*  ┌──────────────────┐
       │       │  University     │◄──────────────┤   Department      │
       └──────▶│ - name          │               │ - name            │
               │ - code          │               │ - code            │
               └─────────────────┘               └──────────────────┘
                       │                                  │
                       │                                  │ 1
                       ▼                                  ▼
                ┌─────────────────┐              ┌──────────────────┐
                │    Program      │              │   DegreeLevel    │
                ├─────────────────┤              └──────────────────┘
                │ - name          │
                │ - code          │
                │ - degree_level  │
                └─────────────────┘
                       │
                       │ 1
                       │
                       ▼ 1..*
                ┌─────────────────┐       1..*     ┌──────────────────┐
                │     Course      │◄─────────────┤      Term         │
                ├─────────────────┤               └──────────────────┘
                │ - name          │
                │ - code          │◄──────┐
                │ - credits       │       │
                │ - instructors   │       │ M2M
                └─────────────────┘       │
                       │                 │
                       │ 1               │
                       │                 │
       ┌───────────────┼───────────────┐ │
       │               │               │ │
       ▼               ▼               │ │
┌─────────────┐ ┌─────────────┐       │ │
│Learning     │ │   Program   │       │ │
│Outcome      │ │   Outcome   │       │ │
├─────────────┤ ├─────────────┤       │ │
│ - code       │ │ - code       │       │ │
│ - desc       │ │ - desc       │       │ │
│ - course     │ │ - program    │       │ │
└─────────────┘ └─────────────┘       │ │
       │               │               │ │
       │               │               │ │
       │       ┌───────┴───────┐       │ │
       │       │               │       │ │
       ▼       ▼               ▼       │ │
┌─────────────────────────────────┐   │ │
│LearningOutcome-ProgramOutcome   │   │ │
│Mapping                          │   │ │
├─────────────────────────────────┤   │ │
│ - weight (0-1)                  │   │ │
│ - course (FK)                   │   │ │
│ - learning_outcome (FK)         │   │ │
│ - program_outcome (FK)          │   │ │
└─────────────────────────────────┘   │ │
                                         │ │
       ┌─────────────────────────────────┘ │
       │                                   │
       ▼ 1..*                              │
┌─────────────────┐                        │
│   Assessment    │                        │
├─────────────────┤                        │
│ - name          │                        │
│ - type          │                        │
│ - total_score   │                        │
│ - weight        │                        │
│ - date          │                        │
└─────────────────┘                        │
       │                                   │
       │ 1..*                              │
       │                                   │
       ▼                                   │
┌─────────────────────────────────┐        │
│Assessment-LearningOutcome       │        │
│Mapping                          │        │
├─────────────────────────────────┤        │
│ - weight (0-1)                  │        │
│ - assessment (FK)               │        │
│ - learning_outcome (FK)         │        │
└─────────────────────────────────┘        │
                                                 │
                                                 │
                                                 ▼ 1..*
                                    ┌─────────────────────┐
                                    │    StudentGrade      │
                                    ├─────────────────────┤
                                    │ - score              │
                                    │ - student (FK)       │
                                    │ - assessment (FK)    │
                                    └─────────────────────┘
                                                 │
                                                 │ triggers
                                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Pre-computed Scores                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ StudentLOScore   │          │ StudentPOScore   │            │
│  ├──────────────────┤          ├──────────────────┤            │
│  │ - student (FK)   │          │ - student (FK)   │            │
│  │ - LO (FK)        │─────────▶│ - PO (FK)        │            │
│  │ - score          │          │ - term (FK)      │            │
│  │                 │          │ - score          │            │
│  └──────────────────┘          └──────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 3: Data Model

### Database Tables and Sizes

`[TODO: RUN THE FOLLOWING SQL QUERIES AND FILL IN THE RESULTS]`

**Query to get table sizes:**
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Query to get row counts:**
```sql
SELECT
    schemaname,
    tablename,
    n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;
```

`[TODO: FILL IN TABLE BELOW WITH ACTUAL DATA]`

| Table Name | Raw Size | Row Count | Column Count | Primary Key | Foreign Keys |
|-----------|----------|-----------|--------------|-------------|--------------|
| users_user | `[TODO]` | `[TODO]` | `[TODO]` | id | department, university |
| users_studentprofile | `[TODO]` | `[TODO]` | `[TODO]` | id | user, enrollment_term, program |
| users_instructorprofile | `[TODO]` | `[TODO]` | `[TODO]` | id | user |
| core_university | `[TODO]` | `[TODO]` | `[TODO]` | id | - |
| core_department | `[TODO]` | `[TODO]` | `[TODO]` | id | university |
| core_program | `[TODO]` | `[TODO]` | `[TODO]` | id | department, degree_level |
| core_degreelevel | `[TODO]` | `[TODO]` | `[TODO]` | id | - |
| core_term | `[TODO]` | `[TODO]` | `[TODO]` | id | - |
| core_course | `[TODO]` | `[TODO]` | `[TODO]` | id | program, term |
| core_course_instructors | `[TODO]` | `[TODO]` | `[TODO]` | id | course, user |
| core_programoutcome | `[TODO]` | `[TODO]` | `[TODO]` | id | program, term, created_by |
| core_learningoutcome | `[TODO]` | `[TODO]` | `[TODO]` | id | course, created_by |
| core_lo_po_mapping | `[TODO]` | `[TODO]` | `[TODO]` | id | course, lo, po |
| core_studentloscore | `[TODO]` | `[TODO]` | `[TODO]` | id | student, lo |
| core_studentposcore | `[TODO]` | `[TODO]` | `[TODO]` | id | student, po, term |
| evaluation_assessment | `[TODO]` | `[TODO]` | `[TODO]` | id | course, created_by |
| evaluation_assessment_lo_mapping | `[TODO]` | `[TODO]` | `[TODO]` | id | assessment, lo |
| evaluation_studentgrade | `[TODO]` | `[TODO]` | `[TODO]` | id | student, assessment |
| evaluation_courseenrollment | `[TODO]` | `[TODO]` | `[TODO]` | id | student, course |

### Schema Design Discussion

**Schema Type:** Star Schema with Snowflake characteristics

Our data model follows a **star schema pattern** centered around fact tables (`StudentGrade`, `StudentLOScore`, `StudentPOScore`) with dimension tables (`University`, `Department`, `Program`, `Course`, `Term`, etc.).

**Normalization Level:** The schema is **normalized (3NF)** with controlled denormalization for performance:

1. **Normalized Aspects:**
   - All dimension tables are in 3NF (no transitive dependencies)
   - Foreign key relationships maintain referential integrity
   - Unique constraints prevent duplicate data

2. **Strategic Denormalization:**
   - **Pre-computed score tables** (`StudentLOScore`, `StudentPOScore`)
     - Denormalized from raw grade data
     - Enables fast analytics without complex joins
     - Updated via triggers when grades change
   - **Timestamp fields** on all models for audit trails
   - **Redundant weight fields** in mapping tables for calculation efficiency

**Schema Justification:**

1. **Star Schema Benefits:**
   - **Query Performance**: Fact tables can be queried directly with minimal joins
   - **Analytics-Friendly**: Simple joins enable fast aggregation and filtering
   - **Scalability**: Easy to add new dimensions without restructuring

2. **Normalization Benefits:**
   - **Data Integrity**: Constraints prevent orphaned records and invalid data
   - **Update Anomalies**: Single source of truth for each entity
   - **Flexibility**: Easy to modify structure without affecting dependent queries

3. **Denormalization Trade-offs:**
   - **Storage vs Speed**: Extra storage for pre-computed scores, but much faster reads
   - **Write Complexity**: Score recalculation required on grade changes
   - **Data Consistency**: Maintained through Django signals and transaction atomicity

### Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  University  │───────│ Department   │───────│ DegreeLevel  │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ PK id        │       │ PK id        │       │ PK id        │
│    name      │       │    name      │       │    name      │
│              │       │ FK university │       │              │
└──────────────┘       └──────┬───────┘       └──────────────┘
                              │
                              │
                              ▼
                       ┌──────────────┐       ┌──────────────┐
                       │    Program   │───────│     Term     │
                       ├──────────────┤       ├──────────────┤
                       │ PK id        │ 1..*  │ PK id        │
                       │    name      │       │    name      │
                       │    code      │       │    is_active │
                       │ FK degree    │       │              │
                       │ FK department │       └──────────────┘
                       └──────┬───────┘
                              │ 1
                              │
                              │ 1..*
                              ▼
                       ┌──────────────┐
                       │    Course    │
                       ├──────────────┤
                       │ PK id        │
                       │    name      │
                       │    code      │
                       │ FK program   │
                       │ FK term      │
                       └──────┬───────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           │                  │                  │
           ▼                  ▼                  ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│Learning       │    │Program        │    │  Assessment   │
│Outcome        │    │Outcome        │    │               │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ PK id         │    │ PK id         │    │ PK id         │
│ FK course     │    │ FK program    │    │ FK course     │
│               │    │ FK term       │    │    name       │
│               │    │               │    │    type       │
└───────┬───────┘    └───────┬───────┘    │    total      │
        │                    │            │    weight     │
        │                    │            └───────┬───────┘
        │                    │                    │
        └────────┬───────────┘                    │
                 │                                │
                 ▼                                ▼
        ┌───────────────────┐            ┌───────────────────┐
        │ LO-PO Mapping     │            │ Assessment-LO     │
        ├───────────────────┤            │ Mapping            │
        │ PK id             │            ├───────────────────┤
        │ FK course         │            │ PK id             │
        │ FK lo             │            │ FK assessment     │
        │ FK po             │            │ FK lo             │
        │ weight (0-1)      │            │ weight (0-1)      │
        └───────────────────┘            └─────────┬─────────┘
                                               │
                                               │
                                               ▼
                                    ┌───────────────────┐
                                    │   StudentGrade    │
                                    ├───────────────────┤
                                    │ PK id             │
                                    │ FK student        │
                                    │ FK assessment     │
                                    │    score          │
                                    └─────────┬─────────┘
                                              │
                                              │ triggers
                                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Pre-computed Scores                          │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ StudentLOScore   │          │ StudentPOScore   │            │
│  ├──────────────────┤          ├──────────────────┤            │
│  │ PK id            │          │ PK id            │            │
│  │ FK student       │          │ FK student       │            │
│  │ FK lo            │          │ FK po            │            │
│  │ FK term          │◄─────────│ FK term          │            │
│  │    score         │          │    score         │            │
│  └──────────────────┘          └──────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 4: Scalability and Fault Tolerance

### Indexes Used

**Primary Indexes:**
- All tables have primary key indexes on `id` (BigAutoField)
- Automatically created by Django for fast lookups

**Foreign Key Indexes:**
Django automatically creates indexes for foreign keys. Our key FK indexes:

| Table | Foreign Key Column | Indexed | Purpose |
|-------|-------------------|---------|---------|
| core_department | university | Yes | Filter departments by university |
| core_program | department, degree_level | Yes | Filter programs by department/degree |
| core_course | program, term | Yes | Filter courses by program/term |
| core_programoutcome | program, term | Yes | Filter POs by program/term |
| core_learningoutcome | course | Yes | Get LOs for a course |
| core_lo_po_mapping | course, learning_outcome, program_outcome | Yes | Mapping lookups |
| core_studentloscore | student, learning_outcome | Yes | Student score queries |
| core_studentposcore | student, program_outcome, term | Yes | Student PO queries |
| evaluation_assessment | course, created_by | Yes | Course assessments |
| evaluation_assessment_lo_mapping | assessment, learning_outcome | Yes | Assessment LO mappings |
| evaluation_studentgrade | student, assessment | Yes | Student grade lookups |
| evaluation_courseenrollment | student, course | Yes | Enrollment checks |

**Unique Indexes (Data Integrity):**
| Table | Columns | Purpose |
|-------|---------|---------|
| core_university | name | Prevent duplicate universities |
| core_department | code | Prevent duplicate department codes |
| core_program | code | Prevent duplicate program codes |
| core_course | code, term | One course code per term |
| core_lo_po_mapping | course, learning_outcome, program_outcome | One mapping per LO-PO per course |
| core_studentloscore | student, learning_outcome | One score per student per LO |
| core_studentposcore | student, program_outcome, term | One score per student per PO per term |
| evaluation_assessment_lo_mapping | assessment, learning_outcome | One mapping per assessment per LO |
| evaluation_studentgrade | student, assessment | One grade per student per assessment |
| evaluation_courseenrollment | student, course | One enrollment per student per course |
| users_studentprofile | student_id | Unique student IDs |
| core_term | (name, is_active) with constraint | Only one active term per name |

**Custom Indexes for Query Performance:**

`[TODO: CHECK IF THERE ARE ANY CUSTOM INDEXES IN MODELS]`

```python
# Example from Django models Meta class:
class Meta:
    indexes = [
        models.Index(fields=['student', 'course']),
        models.Index(fields=['term', 'program_outcome']),
    ]
```

### Materialized Views and Pre-computation

**Pre-computed Score Tables:**

We use **pre-computed tables** instead of materialized views for performance:

1. **StudentLOScore** (Pre-computed):
   - Stores calculated learning outcome scores per student
   - Updated via Django signals when grades change
   - Enables fast retrieval: `SELECT score FROM studentloscore WHERE student_id=X AND lo_id=Y`

2. **StudentPOScore** (Pre-computed):
   - Stores calculated program outcome scores per student per term
   - Aggregated from LO scores using weighted mappings
   - Enables fast program-level analytics

**Calculation Flow:**
```python
# From evaluation/services.py
def calculate_course_scores(course_id):
    """
    Pre-compute LO scores from student grades
    Uses bulk operations for efficiency
    """
    # 1. Get all grades for course
    # 2. Calculate weighted LO scores
    # 3. Bulk update StudentLOScore table
    # 4. Trigger PO score calculation
```

**Why Pre-computed Tables vs Materialized Views?**
- **Real-time updates**: Scores update immediately when grades change
- **Flexibility**: Can implement business logic in Python
- **Query simplicity**: No need for complex JOINs in analytics queries
- **Transaction safety**: Updates are atomic with grade changes

### Data Partitioning

**Current Implementation:** No data partitioning implemented

**Recommended Partitioning for Scale:**

`[TODO: THIS IS A RECOMMENDATION - IMPLEMENT IF NEEDED]`

For large-scale deployments (100K+ students), consider:

1. **Time-based Partitioning** (StudentGrade, StudentLOScore):
   ```sql
   -- Partition by academic term
   CREATE TABLE evaluation_studentgrade_fall2024
       PARTITION OF evaluation_studentgrade
       FOR VALUES IN ('2024-Fall');
   ```

2. **Hash-based Partitioning** (StudentLOScore, StudentPOScore):
   ```sql
   -- Distribute across partitions by student_id hash
   -- Enables parallel query processing
   ```

3. **Range Partitioning** (StudentGrade by date):
   ```sql
   -- Useful for time-series analytics
   -- Older partitions can be archived
   ```

### Data Replication

**Current Implementation:** No replication configured

**Recommended Replication Strategy:**

`[TODO: FILL IN REPLICATION STRATEGY IF IMPLEMENTED]`

1. **Read Replicas for Reporting:**
   - Primary: Handle all writes
   - Replicas: Serve read-heavy analytics queries
   - Benefit: Offload read traffic, improve query performance

2. **Multi-Region Replication:**
   - For distributed campuses
   - Reduces latency for remote users

### Fault Tolerance Mechanisms

**1. Database Level:**
- **ACID Transactions**: All critical operations wrapped in `transaction.atomic()`
- **Foreign Key Constraints**: Prevent orphaned records
- **Unique Constraints**: Prevent duplicate data
- **Validation**: Model-level and serializer-level validation

**2. Application Level:**
- **Try-Except Blocks**: Graceful error handling in file import
- **Rollback on Error**: Transaction atomicity ensures all-or-nothing
- **Error Logging**: Comprehensive error logging for debugging

**3. File Import Fault Tolerance:**
```python
with transaction.atomic():
    for idx, row in df.iterrows():
        try:
            # Process row
        except Exception as e:
            # Log error, continue with next row
            self.import_results['errors'].append(f"Row {idx}: {str(e)}")
            continue
```

**4. API Level:**
- **404 Handling**: Graceful handling of missing resources
- **400 Validation**: Clear error messages for invalid data
- **500 Logging**: Server errors logged for investigation

### Failure Scenarios and Handling

| Failure Type | Impact | Mitigation |
|--------------|--------|------------|
| Database connection loss | API unavailable | Connection pooling, retry logic |
| File server unavailable | Can't import files | Local temp storage, retry queue |
| Token refresh failure | User logged out | Clear tokens, redirect to login |
| Import file invalid | Partial import | Transaction rollback, error reporting |
| Score calculation error | Stale scores | Recalculation triggered on next grade change |

---

## Section 5: Consistency

### Transaction Usage

**Critical Operations Using Transactions:**

1. **File Import Operations** (`core/services/file_import.py`):
```python
with transaction.atomic():
    # Batch create/update records
    for row in data:
        StudentGrade.objects.update_or_create(...)
    # If any row fails, entire transaction rolls back
```

2. **Score Calculation** (`evaluation/services.py`):
```python
with transaction.atomic():
    # Delete old scores
    StudentLearningOutcomeScore.objects.filter(...).delete()
    # Create new scores
    StudentLearningOutcomeScore.objects.bulk_create(scores)
    # All-or-nothing guarantee
```

3. **Bulk Grade Updates**:
```python
with transaction.atomic():
    # Ensure grade and score updates are atomic
    grade.save()
    calculate_course_scores(grade.course_id)
```

### Transaction Isolation Level

**Default Django Isolation:** `READ COMMITTED`

`[TODO: CHECK POSTGRESQL DEFAULT ISOLATION LEVEL]`

PostgreSQL default is **Read Committed**, which provides:
- Guarantees only committed data is read
- Prevents dirty reads
- Allows non-repeatable reads and phantom reads
- Suitable for most web applications

**For Stronger Consistency (if needed):**
```python
from django.db import transaction

@transaction.atomic(isolation='SERIALIZABLE')
def critical_operation():
    # Highest isolation level
    # Prevents all concurrency anomalies
    # Use sparingly due to performance impact
```

### Consistency Guarantees

**1. Referential Integrity:**
- Foreign key constraints enforced at database level
- Cannot orphan records (e.g., grade without student)
- Cascade deletes configured appropriately

**2. Data Validation:**
- **Model-level**: `clean()`, `validate_*()` methods
- **Serializer-level**: DRF field validators
- **Database-level**: Constraints, CHECK constraints

**3. Score Consistency:**
```python
# Score recalculation ensures consistency
def calculate_course_scores(course_id):
    """
    Recalculate all LO and PO scores for a course
    Called via signals when grades change
    """
    # Delete old scores (atomic with bulk_create)
    StudentLearningOutcomeScore.objects.filter(
        learning_outcome__course_id=course_id
    ).delete()

    # Calculate new scores
    # Bulk insert for performance
    StudentLearningOutcomeScore.objects.bulk_create(new_scores)
```

**4. Weight Sum Validation:**
```python
# ListSerializer validates weight sums = 1.0
class AssessmentLearningOutcomeMappingListSerializer(serializers.ListSerializer):
    def validate(self, attrs):
        total_weight = sum(item.get('weight', 0) for item in attrs)
        if not (0.99 <= total_weight <= 1.01):
            raise serializers.ValidationError("Weights must sum to 1.0")
        return attrs
```

**5. Concurrent Modification Handling:**
- Django ORM's `update_or_create()` prevents race conditions
- `select_for_update()` locks rows during updates (if needed)
- Transaction atomicity prevents partial updates

### Concurrency Control

**Optimistic Locking:**
```python
# Django's default approach
grade = StudentGrade.objects.get(pk=grade_id)
grade.score = new_score
grade.save()  # Checks if record changed since fetch
```

**Pessimistic Locking (if needed):**
```python
from django.db import transaction

@transaction.atomic
def update_grade_safely(grade_id, new_score):
    grade = StudentGrade.objects.select_for_update().get(pk=grade_id)
    grade.score = new_score
    grade.save()
    # Row locked until transaction completes
```

---

## Section 6: Teamwork

### Team Members and Responsibilities

`[TODO: FILL IN TEAM MEMBER DETAILS]`

| Team Member | Role | Responsibilities Completed |
|-------------|------|---------------------------|
| `[NAME]` | `[ROLE]` | `[TASKS COMPLETED]` |
| `[NAME]` | `[ROLE]` | `[TASKS COMPLETED]` |
| `[NAME]` | `[ROLE]` | `[TASKS COMPLETED]` |
| `[NAME]` | `[ROLE]` | `[TASKS COMPLETED]` |

### Work Division

**Backend Development:**
- **Models & Database Schema:** `[TODO: WHO]`
  - Designed Django models
  - Defined relationships and constraints
  - Created and ran migrations

- **API Development:** `[TODO: WHO]`
  - Implemented ViewSets (core, evaluation, users)
  - Configured DRF routers
  - Added authentication with JWT

- **Business Logic:** `[TODO: WHO]`
  - Score calculation services
  - File import services with Pandas
  - Validation logic

- **Security Implementation:** `[TODO: WHO]`
  - JWT token rotation and blacklisting
  - Role-based permissions
  - DRF weight validation (ListSerializer)

**Frontend Development:**
- **UI Components:** `[TODO: WHO]`
  - Dashboard pages (student, instructor, head)
  - Course management pages
  - Forms and modals

- **State Management:** `[TODO: WHO]`
  - React Query integration
  - Auth context and hooks
  - Error handling

- **API Integration:** `[TODO: WHO]`
  - Axios interceptors with token refresh
  - Orval-generated API clients
  - File upload components

- **Build Configuration:** `[TODO: WHO]`
  - Vite environment setup
  - Path aliases
  - Proxy configuration

**DevOps & Infrastructure:**
- **Database Setup:** `[TODO: WHO]`
  - PostgreSQL configuration
  - Migration management
  - Index optimization

- **Documentation:** `[TODO: WHO]`
  - API documentation (drf-spectacular)
  - README and setup instructions
  - This project report

- **Testing:** `[TODO: WHO]`
  - Unit tests (Pytest)
  - Integration tests
  - End-to-end tests

### Collaboration Tools

- **Version Control:** Git with GitHub
  - Feature branches
  - Pull requests for code review
  - `main` branch for production

- **Issue Tracking:** `[TODO: WHAT WAS USED]`
  - GitHub Projects / Jira / Trello

- **Communication:** `[TODO: WHAT WAS USED]`
  - Slack / Discord / Teams

### Challenges and Solutions

`[TODO: DESCRIBE ANY CHALLENGES FACED AND HOW THEY WERE RESOLVED]`

1. **Challenge:** `[DESCRIPTION]`
   - **Solution:** `[HOW SOLVED]`

2. **Challenge:** `[DESCRIPTION]`
   - **Solution:** `[HOW SOLVED]`

3. **Challenge:** `[DESCRIPTION]`
   - **Solution:** `[HOW SOLVED]`

---

## Appendix A: API Endpoints Reference

### Core App Endpoints

| Endpoint | Methods | Description | Authentication |
|----------|---------|-------------|----------------|
| `/api/core/universities/` | GET, POST | List/create universities | Optional |
| `/api/core/departments/` | GET, POST | List/create departments | Optional |
| `/api/core/programs/` | GET, POST | List/create programs | Optional |
| `/api/core/courses/` | GET, POST | List/create courses | Optional |
| `/api/core/courses/{id}/learning_outcomes/` | GET | Get LOs for course | Required |
| `/api/core/program-outcomes/` | GET, POST | List/create POs | Required (Instructor+) |
| `/api/core/learning-outcomes/` | GET, POST | List/create LOs | Required (Instructor+) |
| `/api/core/student-lo-scores/` | GET | Get LO scores | Required |
| `/api/core/student-po-scores/` | GET | Get PO scores | Required |
| `/api/core/file-import/assignment-scores/upload/` | POST | Import grades | Required (Instructor+) |
| `/api/core/file-import/learning-outcomes/upload/` | POST | Import LOs | Required (Instructor+) |

### Evaluation App Endpoints

| Endpoint | Methods | Description | Authentication |
|----------|---------|-------------|----------------|
| `/api/evaluation/assessments/` | GET, POST | List/create assessments | Required (Instructor+) |
| `/api/evaluation/grades/` | GET, POST | List/create grades | Required (Instructor+) |
| `/api/evaluation/grades/course_averages/` | GET | Get course averages | Required |
| `/api/evaluation/enrollments/` | GET, POST | Manage enrollments | Required (Instructor+) |

### Users App Endpoints

| Endpoint | Methods | Description | Authentication |
|----------|---------|-------------|----------------|
| `/api/users/auth/login/` | POST | Authenticate user | None |
| `/api/users/auth/refresh/` | POST | Refresh access token | None (with refresh token) |
| `/api/users/auth/me/` | GET | Get current user | Required |
| `/api/users/users/` | GET, POST | List/create users | Required (Admin) |

---

## Appendix B: Recent Improvements (December 2025)

### Priority 1: Security Enhancements ✅

1. **JWT Token Rotation & Blacklisting**
   - Enabled `ROTATE_REFRESH_TOKENS: True`
   - Enabled `BLACKLIST_AFTER_ROTATION: True`
   - Old refresh tokens automatically invalidated after rotation
   - Files: `settings.py`

2. **Automatic Token Refresh**
   - Axios interceptor with request queue pattern
   - Seamless token refresh on 401 errors
   - Handles concurrent requests during refresh
   - File: `frontend/src/services/api.ts`

3. **Weight Sum Validation**
   - Custom ListSerializer validates weight sums = 1.0
   - Prevents invalid assessment/LO mappings
   - Files: `evaluation/serializers.py`, `core/serializers.py`

### Priority 2: Data Quality ✅

4. **Pandas dtype Enhancement**
   - Explicit dtype mappings preserve data types
   - `dtype_backend='numpy_nullable'` for better null handling
   - File: `core/services/file_import.py`

5. **Vite Environment Configuration**
   - Environment-specific configs (`.env.development`, `.env.production`)
   - Proxy configuration for API calls
   - Path aliases for cleaner imports
   - Files: `vite.config.ts`, `.env.*`

---

**Report Prepared:** `[TODO: DATE]`
**Last Updated:** `[TODO: DATE]`
