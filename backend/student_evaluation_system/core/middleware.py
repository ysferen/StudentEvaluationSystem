from core.services.audit import set_audit_request


def audit_context_middleware(get_response):
    def middleware(request):
        request.audit_context = {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        set_audit_request(request)
        return get_response(request)

    return middleware
