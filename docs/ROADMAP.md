# Semester 2 Roadmap & Future Features

*Note: Do not claim planned features as complete unless code and tests are actively added.*

## Target Capabilities (Planned)
- Async processing for heavy workloads using Celery + Redis.
- Real-time updates using Django Channels + Redis pub/sub.
- AI-assisted weight recommendation service (local LLM via Ollama).
- Reporting/export features (PDF/Excel) and notification service.

## Implementation Phases
1. Infrastructure foundation (PostgreSQL, Redis, Celery).
2. Performance (async score calculation).
3. Real-time (WebSocket events).
4. AI assistance (weight recommendation).
5. Compliance (audit trails).

## Security & Compliance (Planned)
- Full audit logging for sensitive actions.
- KVKK/GDPR workflow features (consent, retention, export).
