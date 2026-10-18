"""Email backends used by the KapitBayan API."""

import base64
import json
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    """Send Django email messages through Resend's HTTPS API.

    Render Free blocks outbound SMTP ports, so this backend provides a
    dependency-free HTTPS alternative while keeping Django's ``send_mail``
    call sites unchanged.
    """

    api_url = "https://api.resend.com/emails"

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = settings.RESEND_API_KEY
        if not self.api_key:
            raise ImproperlyConfigured(
                "RESEND_API_KEY is required when using ResendEmailBackend."
            )

    def send_messages(self, email_messages):
        sent_count = 0
        for message in email_messages or ():
            if not message.recipients():
                continue
            try:
                self._send(message)
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                sent_count += 1
        return sent_count

    def _send(self, message):
        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": message.to,
            "subject": message.subject or "",
            "text": message.body or "",
        }
        if message.cc:
            payload["cc"] = message.cc
        if message.bcc:
            payload["bcc"] = message.bcc
        if message.reply_to:
            payload["reply_to"] = message.reply_to

        for alternative in getattr(message, "alternatives", ()) or ():
            if alternative.mimetype == "text/html":
                payload["html"] = alternative.content
                break

        attachments = self._serialize_attachments(message)
        if attachments:
            payload["attachments"] = attachments

        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(
                    f"Resend email API returned HTTP {response.status}."
                )

    @staticmethod
    def _serialize_attachments(message):
        serialized = []
        for attachment in getattr(message, "attachments", ()) or ():
            if isinstance(attachment, tuple):
                filename, content, _mimetype = attachment
            else:
                filename = attachment.get_filename()
                content = attachment.get_payload(decode=True)

            if not filename or content is None:
                raise ValueError("Email attachment must have a filename and content.")
            if isinstance(content, str):
                content = content.encode("utf-8")
            serialized.append(
                {
                    "filename": filename,
                    "content": base64.b64encode(content).decode("ascii"),
                }
            )
        return serialized
