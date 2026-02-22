# PostgreSQL Guide

---

## Quick Start (New Setup)

For new developers or fresh installations:

### 1. Start All Services

```bash
# From project root
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Django backend (port 8000)
- React frontend (port 5173)

### 2. Run Migrations

```bash
# Migrations are automatically applied via docker-compose
# But if you need to run manually:
docker-compose exec backend python manage.py migrate
```

### 3. Create Superuser

```bash
docker-compose exec backend python manage.py createsuperuser
```

### 4. Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/
- API Docs: http://localhost:8000/api/docs/

---

## Migrate Existing SQLite Data

If you have existing data in SQLite that you want to keep:

### Step 1: Backup SQLite Data

```bash
cd backend/student_evaluation_system

# Export all data to JSON
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > backup.json
```

### Step 2: Start PostgreSQL

```bash

DATABASE_URL=postgres://postgres:postgres@localhost:5432/student_evaluation
```

> **Note:** When running outside Docker (native Python), use `localhost`. Inside Docker, use `db` as hostname.

### Step 3: Apply Migrations

```bash
python manage.py migrate
```

### Step 4: Import Data

```bash
# Load the backup data
python manage.py loaddata backup.json
```

## Configuration Options

### Local Development (SQLite - No Docker)

```bash
# backend/.env
DATABASE_URL=sqlite:///db.sqlite3
DEBUG=True
```

```bash
# Run locally
python manage.py runserver
```

### Local Development (PostgreSQL - With Docker)

```bash
# backend/.env
DATABASE_URL=postgres://postgres:postgres@db:5432/student_evaluation
DEBUG=True
```

```bash
# Start only database
docker-compose up -d db

# Run backend locally (native Python)
python manage.py runserver
```


---

## Troubleshooting

### Issue: "Connection refused" to database

**Cause:** Backend starts before database is ready.

**Solution:** Docker Compose already has `depends_on` and healthcheck, but if running locally:

```bash
# Wait a few seconds after starting db
docker-compose up -d db
sleep 5
python manage.py migrate
```

### Issue: "Role does not exist" or authentication failed

**Cause:** PostgreSQL credentials mismatch.

**Solution:** Check `DATABASE_URL` format:

```bash
# Correct format
postgres://USER:PASSWORD@HOST:PORT/DB_NAME

# Example
postgres://postgres:postgres@localhost:5432/student_evaluation
```

### Issue: Migrations fail on fresh PostgreSQL

**Cause:** Migration dependencies or custom SQL incompatible with PostgreSQL.

**Solution:**

```bash
# Reset and retry
docker-compose down -v  # Removes volume
docker-compose up -d db
docker-compose exec backend python manage.py migrate
```

### Issue: Data import fails (loaddata)

**Cause:** Foreign key constraints or different IDs.

**Solution:** Use `--exclude` for problematic tables:

```bash
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --exclude sessions > backup.json
```

Or import in order:
```bash
python manage.py loaddata users.json
python manage.py loaddata core.json
python manage.py loaddata evaluation.json
```

---

## Database Administration

### Access PostgreSQL Console

```bash
# Via Docker
docker-compose exec db psql -U postgres -d student_evaluation

# Common commands:
# \dt           - List tables
# \d table_name - Describe table
# \q            - Quit
```

### Reset Database (Delete All Data)

```bash
# Stop and remove volume
docker-compose down -v

# Restart with fresh database
docker-compose up -d db
docker-compose exec backend python manage.py migrate
```

### Backup Database

```bash
# Create backup
docker-compose exec db pg_dump -U postgres student_evaluation > backup_$(date +%Y%m%d).sql

# Or compressed
docker-compose exec db pg_dump -U postgres student_evaluation | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore Database

```bash
# Restore from backup
docker-compose exec -T db psql -U postgres student_evaluation < backup_20240101.sql
```

---

## Resources

- [Django Database Documentation](https://docs.djangoproject.com/en/5.2/ref/databases/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [dj-database-url](https://github.com/jazzband/dj-database-url)
