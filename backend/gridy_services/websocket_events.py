import asyncio
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _dispatch_group_send(channel_layer, group_name, payload):
    """
    Safely dispatches group_send whether called from synchronous Django views
    or an active asyncio event loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        loop.create_task(channel_layer.group_send(group_name, payload))
    else:
        async_to_sync(channel_layer.group_send)(group_name, payload)


def broadcast_queue_update(barangay_id=None, ticket=None, action="update", message="Queue updated."):
    """
    Broadcasts a real-time queue update strictly to the tenant-scoped channel
    group ``queue_{barangay_id}``. Never falls back to a global broadcast room.

    Safe to call in any context (sync or async); exceptions are caught and
    logged so business transactions are never interrupted by WebSocket issues.
    """
    if barangay_id is None:
        return

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        payload = {
            "type": "queue_update",
            "action": action,
            "barangay_id": barangay_id,
            "ticket": ticket,
            "message": message,
        }

        _dispatch_group_send(channel_layer, f"queue_{barangay_id}", payload)

        logger.debug(
            "Broadcasted queue update (barangay=%s, ticket=%s, action=%s)",
            barangay_id,
            ticket,
            action,
        )
    except Exception as exc:
        logger.warning("Failed to broadcast WebSocket queue update: %s", exc)


async def async_broadcast_queue_update(barangay_id=None, ticket=None, action="update", message="Queue updated."):
    """Async coroutine variant for explicit await in async handlers or tests."""
    if barangay_id is None:
        return

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        payload = {
            "type": "queue_update",
            "action": action,
            "barangay_id": barangay_id,
            "ticket": ticket,
            "message": message,
        }

        await channel_layer.group_send(f"queue_{barangay_id}", payload)
    except Exception as exc:
        logger.warning("Failed in async_broadcast_queue_update: %s", exc)
