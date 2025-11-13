from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.utils import timezone
from .models import UserActivityLog

def _ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR'))

@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    UserActivityLog.objects.create(
        user=user, action='login', timestamp=timezone.now(),
        ip_address=_ip(request), user_agent=request.META.get('HTTP_USER_AGENT','')
    )

@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    UserActivityLog.objects.create(
        user=user, action='logout', timestamp=timezone.now(),
        ip_address=_ip(request), user_agent=request.META.get('HTTP_USER_AGENT','')
    )

@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    UserActivityLog.objects.create(
        user=None, action='failed_login', timestamp=timezone.now(),
        ip_address=_ip(request) if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT','') if request else ''
    )
