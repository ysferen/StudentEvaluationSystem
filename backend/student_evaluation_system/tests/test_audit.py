import pytest
from core.models import AuditLog


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
