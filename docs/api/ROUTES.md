# API Routing & Access Model

## Roles and Access
Defined in `users.CustomUser.role`: `guest`, `student`, `instructor`, `admin`.
- Default DRF permission: `IsAuthenticatedOrReadOnly`.
- Custom classes (`core/permissions.py`): `IsAdmin`, `IsInstructorOrAdmin`, `IsOwnerOrInstructorOrAdmin`, `IsAdminOrReadOnly`.

## API Routes
Versioned routes: `/api/v1/users/`, `/api/v1/core/`, `/api/v1/evaluation/`
(Backward-compatible non-versioned routes are also active).

**Authentication Endpoints:**
- Login: `POST /api/users/auth/login/`
- Refresh: `POST /api/users/auth/refresh/`
- Current User: `GET /api/users/auth/me/`

**Security Baseline:**
- JWT auth with refresh rotation and token blacklisting.
- CORS configuration via env.
- Custom exception middleware/handler.
- File upload size limits.
