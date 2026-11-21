import pytest
from channels.testing import WebsocketCommunicator

from config.asgi import application
from gridy_auth.models import Barangay
from gridy_services.websocket_events import broadcast_queue_update

TEST_HEADERS = [(b"origin", b"http://localhost")]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_queue_connect_and_receive_broadcast():
    barangay = await Barangay.objects.acreate(name="WS Barangay Alpha")
    communicator = WebsocketCommunicator(
        application,
        f"/ws/queue/{barangay.id}/",
        headers=TEST_HEADERS,
    )
    connected, _ = await communicator.connect()
    assert connected, "WebSocket connection failed to establish."

    # Broadcast an update to this barangay
    broadcast_queue_update(
        barangay_id=barangay.id,
        ticket="Q042",
        action="call_next",
        message="Now serving ticket Q042",
    )

    response = await communicator.receive_json_from(timeout=3)
    assert response["type"] == "queue_update"
    assert response["barangay_id"] == barangay.id
    assert response["ticket"] == "Q042"
    assert response["action"] == "call_next"

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_queue_tenant_isolation():
    barangay_a = await Barangay.objects.acreate(name="WS Tenant A")
    barangay_b = await Barangay.objects.acreate(name="WS Tenant B")

    client_a = WebsocketCommunicator(
        application,
        f"/ws/queue/{barangay_a.id}/",
        headers=TEST_HEADERS,
    )
    connected_a, _ = await client_a.connect()
    assert connected_a

    client_b = WebsocketCommunicator(
        application,
        f"/ws/queue/{barangay_b.id}/",
        headers=TEST_HEADERS,
    )
    connected_b, _ = await client_b.connect()
    assert connected_b

    # Broadcast exclusively to Barangay A
    broadcast_queue_update(
        barangay_id=barangay_a.id,
        ticket="A001",
        action="call_next",
    )

    response_a = await client_a.receive_json_from(timeout=3)
    assert response_a["ticket"] == "A001"
    assert response_a["barangay_id"] == barangay_a.id

    # Client B should NOT receive it
    is_nothing = await client_b.receive_nothing(timeout=0.5)
    assert is_nothing, "Client B received message from a different barangay!"

    await client_a.disconnect()
    await client_b.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_websocket_queue_rejects_unscoped_or_unknown_barangay_routes():
    unscoped = WebsocketCommunicator(application, "/ws/queue/", headers=TEST_HEADERS)
    with pytest.raises(ValueError):
        await unscoped.connect()

    unknown = WebsocketCommunicator(
        application,
        "/ws/queue/999999/",
        headers=TEST_HEADERS,
    )
    connected, close_code = await unknown.connect()
    assert not connected
    assert close_code == 4004
