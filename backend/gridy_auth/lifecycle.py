import base64
import logging
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action

logger = logging.getLogger(__name__)

RESIDENT_PRIVATE_MEDIA_FIELDS = (
    "philsys_id_photo",
    "secondary_id_photo",
    "utility_billing_photo",
)
PRIVATE_MEDIA_STORAGE_MODELS = {
    "gridy_auth.Resident": RESIDENT_PRIVATE_MEDIA_FIELDS,
    "gridy_auth.BarangayApplication": ("proof_of_authority",),
}


def _fernet_for_secret(secret):
    key_material = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"gridy-private-media-cleanup-v1",
    ).derive(secret.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(key_material))


def _encrypt_private_file_name(file_name):
    return _fernet_for_secret(settings.SECRET_KEY).encrypt(
        file_name.encode("utf-8")
    ).decode("ascii")


def _decrypt_private_file_name(encrypted_file_name):
    secrets = [settings.SECRET_KEY, *getattr(settings, "SECRET_KEY_FALLBACKS", [])]
    for secret in dict.fromkeys(secrets):
        try:
            return _fernet_for_secret(secret).decrypt(
                encrypted_file_name.encode("ascii")
            ).decode("utf-8")
        except (InvalidToken, UnicodeError):
            continue
    raise InvalidToken


def queue_private_media_cleanup(storage_model, field_name, file_name):
    """Queue encrypted file metadata for durable deletion after a DB commit."""
    from gridy_auth.models import PrivateMediaCleanup

    if field_name not in PRIVATE_MEDIA_STORAGE_MODELS.get(storage_model, ()):
        raise ValueError("Unrecognized private media storage field")
    return PrivateMediaCleanup.objects.create(
        storage_model=storage_model,
        field_name=field_name,
        encrypted_file_name=_encrypt_private_file_name(file_name),
        next_attempt_at=timezone.now(),
    )


def _record_private_media_retry(cleanup, error):
    now = timezone.now()
    attempt_count = cleanup.attempt_count + 1
    delay_minutes = min(5 * 2 ** min(attempt_count - 1, 9), 1440)
    try:
        type(cleanup).objects.filter(pk=cleanup.pk).update(
            attempt_count=F("attempt_count") + 1,
            last_attempt_at=now,
            next_attempt_at=now + timedelta(minutes=delay_minutes),
            last_error_code=type(error).__name__[:128],
        )
    except Exception as record_error:
        logger.error(
            "Could not update private media cleanup retry state (%s).",
            type(record_error).__name__,
        )
    logger.warning(
        "Private media cleanup remains queued (job=%s, error=%s).",
        cleanup.pk,
        type(error).__name__,
    )


def attempt_private_media_cleanup(cleanup_id):
    """Delete one queued private file; retain a retry record after any failure."""
    from gridy_auth.models import BarangayApplication, PrivateMediaCleanup, Resident

    cleanup = PrivateMediaCleanup.objects.filter(pk=cleanup_id).first()
    if cleanup is None:
        return "missing"

    now = timezone.now()
    if cleanup.next_attempt_at > now:
        return "deferred"

    try:
        allowed_fields = PRIVATE_MEDIA_STORAGE_MODELS.get(cleanup.storage_model)
        if allowed_fields is None or cleanup.field_name not in allowed_fields:
            raise ValueError("Unrecognized private media field")
        file_name = _decrypt_private_file_name(cleanup.encrypted_file_name)
        model = {
            "gridy_auth.Resident": Resident,
            "gridy_auth.BarangayApplication": BarangayApplication,
        }[cleanup.storage_model]
        storage = model._meta.get_field(cleanup.field_name).storage
        if storage.exists(file_name):
            storage.delete(file_name)
        if storage.exists(file_name):
            raise OSError("Storage still reports the private file as present")
    except Exception as error:
        _record_private_media_retry(cleanup, error)
        return "retry"

    try:
        cleanup.delete()
    except Exception as error:
        _record_private_media_retry(cleanup, error)
        return "retry"
    return "deleted"


def attempt_private_media_cleanup_safely(cleanup_id):
    """Keep post-commit cleanup failures from changing the account-delete response."""
    try:
        return attempt_private_media_cleanup(cleanup_id)
    except Exception as error:
        logger.error(
            "Private media cleanup attempt could not complete (job=%s, error=%s).",
            cleanup_id,
            type(error).__name__,
        )
        return "retry"


def erase_user_account(user, reason, request=None, actor=None):
    """
    Safely erases or removes a user account while adhering to RA 10173 and COA audit rules:
    1. Records an audit log event preserving accountability before deletion.
    2. Revokes all active JWT refresh sessions.
    3. Queues encrypted private identity file names for post-commit deletion/retry.
    4. Preserves statutory document clearances, official receipts (O.R.), fee assessments,
       and aid assistance history by dissociating the user foreign keys and snapshotting names.
    5. Deletes the User record.
    """
    from gridy_auth.models import PrivateMediaCleanup, RefreshSession
    from gridy_services.models import DocumentRequest, AidRequest

    effective_actor = actor or user
    resident = getattr(user, "profile", None)
    resident_name = (
        resident.full_name if resident else (user.get_full_name() or user.username)
    )

    with transaction.atomic():
        # Record accountability before destruction.
        log_action(
            user=effective_actor,
            action_type=AuditLog.ActionType.USER_ACTION,
            description=reason,
            request=request,
        )

        # Revoke all active refresh sessions.
        RefreshSession.objects.filter(user=user).update(is_revoked=True)

        profile_picture = user.profile_picture.name if user.profile_picture else None
        if profile_picture:
            profile_picture_storage = user.profile_picture.storage
            transaction.on_commit(
                lambda: profile_picture_storage.delete(profile_picture)
            )

        # Store only encrypted file names, with no foreign key to the account being deleted.
        if resident:
            for field_name in RESIDENT_PRIVATE_MEDIA_FIELDS:
                file_field = getattr(resident, field_name, None)
                if file_field and file_field.name:
                    cleanup = PrivateMediaCleanup.objects.create(
                        storage_model="gridy_auth.Resident",
                        field_name=field_name,
                        encrypted_file_name=_encrypt_private_file_name(
                            file_field.name
                        ),
                        next_attempt_at=timezone.now(),
                    )
                    transaction.on_commit(
                        lambda cleanup_id=cleanup.pk: attempt_private_media_cleanup_safely(
                            cleanup_id
                        )
                    )

        # Preserve Document Request history (COA Treasury compliance & ADR 007).
        for doc in DocumentRequest.objects.filter(user=user):
            if not doc.walkin_name:
                doc.walkin_name = resident_name
            doc.user = None
            doc.save(update_fields=["walkin_name", "user"])

        # Preserve Aid Request history.
        AidRequest.objects.filter(requester=user).update(requester=None)

        # Delete the user object; cleanup rows are independent of this account.
        user.delete()
