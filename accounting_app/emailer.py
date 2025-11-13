# utils/emailer.py
import os, re
from typing import List, Tuple
from django.conf import settings
from django.core.mail import get_connection
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError

def _env_key_for(email: str) -> str:
    safe = re.sub(r'[^A-Za-z0-9]+', '_', email).strip('_').lower()
    return f"EMAIL_APP_PASS__{safe}"

def parse_emails(raw: str | None) -> List[str]:
    if not raw:
        return []
    parts = re.split(r'[,\s;]+', raw.strip())
    emails, validate = [], EmailValidator()
    for p in parts:
        if not p: 
            continue
        try:
            validate(p)
            emails.append(p)
        except ValidationError:
            pass
    # de-dup preserve order
    seen, out = set(), []
    for e in emails:
        if e not in seen:
            seen.add(e); out.append(e)
    return out

def build_connection_for_from(from_email: str | None) -> Tuple[str, object, List[str]]:
    """
    Returns (effective_from_email, connection, reply_to).
    - If we have an app password for from_email, we authenticate and send FROM it.
    - Else we fall back to service mailbox and set Reply-To to from_email.
    """
    reply_to: List[str] = []
    if from_email:
        k = _env_key_for(from_email)
        app_pass = os.environ.get(k)
        if app_pass:
            conn = get_connection(
                backend=settings.EMAIL_BACKEND,
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=from_email,
                password=app_pass,
                use_tls=settings.EMAIL_USE_TLS,
            )
            return from_email, conn, reply_to  # no reply-to needed
        else:
            # fall back to service mailbox, but honor requested From via Reply-To
            reply_to = [from_email]

    # service fallback
    service = "noreply.yourapp@gmail.com"  # set yours
    skey = _env_key_for(service)
    spw = os.environ.get(skey)
    if not spw:
        raise RuntimeError("Missing app password for service mailbox.")
    conn = get_connection(
        backend=settings.EMAIL_BACKEND,
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=service,
        password=spw,
        use_tls=settings.EMAIL_USE_TLS,
    )
    return service, conn, reply_to
