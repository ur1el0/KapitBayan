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
    Broadcasts real-time queue update to the tenant-scoped channel group:
    queue_{barangay_id} and fallback global room queue_updates.
    
    Safe to call in any context (sync or async); exceptions are caught and
    logged so business transactions are never interrupted by WebSocket issues.
    """
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

        # Send to barangay-scoped group
        if barangay_id is not None:
            _dispatch_group_send(channel_layer, f"queue_{barangay_id}", payload)

        # Send to global queue_updates group for backward compatibility
        _dispatch_group_send(channel_layer, "queue_updates", payload)

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

        if barangay_id is not None:
            await channel_layer.group_send(f"queue_{barangay_id}", payload)

        await channel_layer.group_send("queue_updates", payload)
    except Exception as exc:
        logger.warning("Failed in async_broadcast_queue_update: %s", exc)
