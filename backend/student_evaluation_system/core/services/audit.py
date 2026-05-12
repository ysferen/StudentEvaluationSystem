import threading
from core.models import AuditLog

_audit_request_store = threading.local()


def set_audit_request(request):
    """Store the current request for audit context (called by middleware)."""
    _audit_request_store.request = request


def get_audit_request():
    """Retrieve the current request from thread-local storage."""
    return getattr(_audit_request_store, "request", None)


def clear_audit_request():
    """Clear the thread-local request storage (for cleanup between requests/tests)."""
    try:
        del _audit_request_store.request
    except AttributeError:
        pass


def log_audit(user, action, model_name, object_id=None, before=None, after=None, metadata=None):
    """Create an audit log entry. Safe to call from views, signals, or tasks."""
    request = get_audit_request()
    if request and hasattr(request, "audit_context"):
        ip = request.audit_context.get("ip_address")
        ua = request.audit_context.get("user_agent", "")
    else:
        ip = None
        ua = ""

    return AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        before_snapshot=before,
        after_snapshot=after,
        metadata=metadata or {},
        ip_address=ip,
        user_agent=ua,
    )


def set_grade_user(grade_instance, user):
    """Attach user to a grade instance for signal-based audit capture."""
    grade_instance._audit_user = user
