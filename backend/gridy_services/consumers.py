import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

from gridy_auth.models import Barangay

logger = logging.getLogger(__name__)


class QueueConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer handling real-time queue notifications strictly inside
    verified tenant-isolated rooms (``queue_{barangay_id}``).
    """

    async def connect(self):
        raw_barangay_id = self.scope.get("url_route", {}).get("kwargs", {}).get("barangay_id")
        try:
            barangay_id = int(raw_barangay_id)
        except (TypeError, ValueError):
            barangay_id = None

        if (
            not barangay_id
            or barangay_id <= 0
            or not await Barangay.objects.filter(pk=barangay_id).aexists()
        ):
            await self.close(code=4004)
            return

        self.barangay_id = str(barangay_id)
        self.group_name = f"queue_{barangay_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()
        logger.info("WebSocket connected on group: %s", self.group_name)

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(
                group_name,
                self.channel_name,
            )
            logger.info("WebSocket disconnected from group: %s (code: %s)", group_name, close_code)

    async def queue_update(self, event):
        """
        Handler triggered when a group_send event of type 'queue_update' is fired.
        Forwards the update payload to the connected WebSocket client.
        """
        payload = {
            'type': 'queue_update',
            'action': event.get('action', 'update'),
            'ticket': event.get('ticket'),
            'barangay_id': event.get('barangay_id'),
            'message': event.get('message', 'Data has changed. Please refetch.')
        }
        await self.send(text_data=json.dumps(payload))
