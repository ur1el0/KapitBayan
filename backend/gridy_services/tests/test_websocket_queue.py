import pytest
from channels.testing import WebsocketCommunicator
from config.asgi import application
from gridy_services.websocket_events import broadcast_queue_update


@pytest.mark.asyncio
async def test_websocket_queue_connect_and_receive_broadcast():
    communicator = WebsocketCommunicator(application, "/ws/queue/10/")
    connected, _ = await communicator.connect()
    assert connected, "WebSocket connection failed to establish."

    # Broadcast an update to barangay 10
    broadcast_queue_update(
        barangay_id=10,
        ticket="Q042",
        action="call_next",
        message="Now serving ticket Q042",
    )

    # Receive from communicator
    response = await communicator.receive_json_from(timeout=3)
    assert response["type"] == "queue_update"
    assert response["barangay_id"] == 10
    assert response["ticket"] == "Q042"
    assert response["action"] == "call_next"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_websocket_queue_tenant_isolation():
    # Client A in Barangay 10
    client_a = WebsocketCommunicator(application, "/ws/queue/10/")
    connected_a, _ = await client_a.connect()
    assert connected_a

    # Client B in Barangay 20
    client_b = WebsocketCommunicator(application, "/ws/queue/20/")
    connected_b, _ = await client_b.connect()
    assert connected_b

    # Broadcast exclusively to Barangay 10
    broadcast_queue_update(
        barangay_id=10,
        ticket="A001",
        action="call_next",
    )

    # Client A receives it
    response_a = await client_a.receive_json_from(timeout=3)
    assert response_a["ticket"] == "A001"
    assert response_a["barangay_id"] == 10

    # Client B should NOT receive it (times out / nothing received)
    is_nothing = await client_b.receive_nothing(timeout=0.5)
    assert is_nothing, "Client B received message from a different barangay!"

    await client_a.disconnect()
    await client_b.disconnect()


@pytest.mark.asyncio
async def test_websocket_queue_generic_route():
    communicator = WebsocketCommunicator(application, "/ws/queue/")
    connected, _ = await communicator.connect()
    assert connected

    # Broadcast global or generic update
    broadcast_queue_update(
        barangay_id=None,
        ticket="G001",
        action="create",
    )

    response = await communicator.receive_json_from(timeout=3)
    assert response["type"] == "queue_update"
    assert response["ticket"] == "G001"

    await communicator.disconnect()
