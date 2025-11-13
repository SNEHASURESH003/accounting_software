# core/middleware.py
from threading import local

# ---- Current user storage (thread-local) ----
_thread_local = local()

def get_current_user():
    return getattr(_thread_local, "user", None)

class CurrentUserMiddleware:
    """Store request.user in thread-local for use inside managers/signals."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_local.user = getattr(request, "user", None)
        try:
            return self.get_response(request)
        finally:
            _thread_local.user = None


# ---- Exception logging (lazy model import) ----
class ExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as exc:
            # Lazy lookup so we don't touch models before apps are ready
            from django.apps import apps
            import traceback as _tb

            ErrorLog = apps.get_model("core", "ErrorLog")
            if ErrorLog is not None:
                user = getattr(request, "user", None)
                try:
                    ErrorLog.objects.create(
                        path=request.path,
                        method=request.method,
                        user=(user if (user and user.is_authenticated) else None),
                        exception_type=exc.__class__.__name__,
                        exception_msg=str(exc),
                        traceback=_tb.format_exc(),
                        get_data=request.GET.dict(),
                        post_data=request.POST.dict(),
                    )
                except Exception:
                    # Never let logging crash the request cycle
                    pass

            raise  # re-raise to keep normal error behaviour
