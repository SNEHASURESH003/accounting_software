# branding/context_processors.py
from .models import BrandingSettings

from .models import BrandingSettings

def branding_context(request):
    user = getattr(request, "user", None)

    branding = None

    if user and user.is_authenticated:
        if user.is_superuser:
            # Superuser -> get their own branding
            branding = BrandingSettings.objects.filter(admin_user=user).first()
        else:
            # Accountant or staff -> get their superuser’s branding
            superuser = getattr(user, "created_by", None)
            if superuser:
                branding = BrandingSettings.objects.filter(admin_user=superuser).first()

    return {
        "branding": branding
    }

  
  
# context_processors.py
from .models import Message

def global_messages(request):
    return {
        'messages_list': Message.objects.order_by('-created_at')[:10]  # latest 10
    }
from .models import Message

def navbar_messages(request):
    msgs = Message.objects.all()[:10]  # newest → oldest if Meta.ordering is set
    unread_count = Message.objects.filter(is_read=False).count()
    return {
        'navbar_messages': msgs,
        'navbar_unread_count': unread_count,
    }
