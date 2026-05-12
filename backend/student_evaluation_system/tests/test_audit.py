import pytest
from core.models import AuditLog
from core.services.audit import log_audit, set_audit_request, set_grade_user
from core.middleware import audit_context_middleware
from evaluation.models import StudentGrade


@pytest.mark.django_db
class TestAuditLogModel:
    def test_create_audit_log_entry(self, student_user_factory):
        """Audit log entry can be created with all fields."""
        user = student_user_factory(username="audit_test_student")

        entry = AuditLog.objects.create(
            user=user,
            action="CREATE",
            model_name="StudentGrade",
            object_id=42,
            before_snapshot=None,
            after_snapshot={"score": 85, "total_score": 100},
            metadata={"assessment_id": 7},
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
        assert entry.id is not None
        assert entry.user == user
        assert entry.action == "CREATE"
        assert entry.timestamp is not None

    def test_audit_log_str(self, student_user_factory):
        user = student_user_factory(username="test_audit_str")
        entry = AuditLog.objects.create(user=user, action="DELETE", model_name="Term", object_id=1)
        assert "DELETE" in str(entry)
        assert "Term#1" in str(entry)

    def test_ordering_newest_first(self, student_user_factory):
        user = student_user_factory(username="test_audit_order")
        older = AuditLog.objects.create(user=user, action="CREATE", model_name="X", object_id=1)
        newer = AuditLog.objects.create(user=user, action="UPDATE", model_name="X", object_id=2)
        entries = list(AuditLog.objects.all())
        assert entries[0] == newer
        assert entries[1] == older


@pytest.mark.django_db
class TestAuditService:
    def test_log_audit_creates_entry(self, student_user_factory):
        user = student_user_factory(username="audit_svc_test")
        entry = log_audit(user, "CREATE", "TestModel", object_id=1, after={"key": "value"}, metadata={"extra": "data"})
        assert entry.id is not None
        assert entry.after_snapshot == {"key": "value"}
        assert entry.metadata == {"extra": "data"}

    def test_log_audit_without_request(self, student_user_factory):
        """log_audit works even when no request is in thread-local (e.g., from tests)."""
        user = student_user_factory(username="audit_no_req")
        entry = log_audit(user, "DELETE", "TestModel", object_id=99)
        assert entry.ip_address is None
        assert entry.user_agent == ""

    def test_set_grade_user_attaches_attribute(self, student_user_factory, student_grade_factory):
        user = student_user_factory(username="grade_audit_user")
        grade = student_grade_factory()
        set_grade_user(grade, user)
        assert getattr(grade, "_audit_user", None) == user

    def test_request_context_isolation(self, rf, student_user_factory):
        """Thread-local storage isolates requests correctly."""
        user = student_user_factory(username="ctx_iso_test")
        request = rf.get("/")
        request.audit_context = {"ip_address": "10.0.0.1", "user_agent": "test-agent"}
        set_audit_request(request)

        entry = log_audit(user, "CREATE", "X", object_id=1)
        assert entry.ip_address == "10.0.0.1"
        assert entry.user_agent == "test-agent"


class TestAuditMiddleware:
    def test_middleware_sets_audit_context(self, rf, student_user_factory):
        from core.services.audit import get_audit_request

        user = student_user_factory(username="mw_audit_test")
        request = rf.get("/some-path/")
        request.user = user

        middleware = audit_context_middleware(lambda r: None)
        middleware(request)

        assert hasattr(request, "audit_context")
        assert "ip_address" in request.audit_context
        assert "user_agent" in request.audit_context
        assert get_audit_request() is request


@pytest.mark.django_db
class TestGradeAuditSignals:
    def test_grade_create_triggers_audit(self, student_user_factory, assessment_factory):
        """Creating a grade with _audit_user set triggers audit log."""
        user = student_user_factory(username="sig_grade_create")
        student = student_user_factory(username="sig_grade_student")
        assessment = assessment_factory()
        AuditLog.objects.all().delete()

        grade = StudentGrade(score=50.0, student=student, assessment=assessment)
        set_grade_user(grade, user)
        grade.save()

        logs = AuditLog.objects.filter(action="CREATE", model_name="StudentGrade")
        assert logs.count() >= 1
        entry = logs.first()
        assert entry.user == user
        assert entry.after_snapshot["score"] == grade.score

    def test_grade_delete_triggers_audit(self, student_user_factory, student_grade_factory):
        """Deleting a grade with _audit_user set triggers audit log."""
        user = student_user_factory(username="sig_grade_delete")
        AuditLog.objects.all().delete()
        grade = student_grade_factory()
        existing_score = grade.score
        set_grade_user(grade, user)
        grade.delete()

        logs = AuditLog.objects.filter(action="DELETE", model_name="StudentGrade")
        assert logs.count() >= 1
        assert logs.first().before_snapshot["score"] == existing_score

    def test_grade_save_without_user_does_not_audit(self, student_grade_factory):
        """Grades without _audit_user do not trigger audit logs."""
        AuditLog.objects.all().delete()
        grade = student_grade_factory()
        grade.score = grade.score + 1
        grade.save()

        logs = AuditLog.objects.filter(model_name="StudentGrade")
        assert logs.count() == 0
