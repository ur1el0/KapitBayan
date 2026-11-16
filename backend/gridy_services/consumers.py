import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class QueueConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer handling real-time queue notifications.
    Supports tenant-isolated rooms (queue_{barangay_id}) as well as
    fallback global rooms (queue_updates).
    """

    async def connect(self):
        # Extract optional barangay_id from route kwargs
        self.barangay_id = self.scope.get('url_route', {}).get('kwargs', {}).get('barangay_id')

        if self.barangay_id:
            self.group_name = f"queue_{self.barangay_id}"
        else:
            self.group_name = "queue_updates"

        # Join the channel layer group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info("WebSocket connected on group: %s", self.group_name)

    async def disconnect(self, close_code):
        # Leave the channel layer group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info("WebSocket disconnected from group: %s (code: %s)", self.group_name, close_code)

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
