from unittest.mock import patch

import pytest

from firebase_admin import messaging


@pytest.fixture()
def fcm():
    """Import fcm module with Firebase marked as initialised."""
    with patch("firebase_admin.initialize_app"), \
         patch("os.path.exists", return_value=True), \
         patch("firebase_admin.credentials.Certificate"):
        import importlib
        import backend.app.core.fcm as fcm_module
        importlib.reload(fcm_module)
        fcm_module._initialized = True
        yield fcm_module


class TestSendPush:
    def test_message_has_android_config(self, fcm):
        with patch.object(fcm.messaging, "send", return_value="projects/x/messages/1") as mock_send:
            fcm.send_push("token123", "Title", "Body")

            msg = mock_send.call_args[0][0]
            assert msg.android is not None
            assert msg.android.priority == "high"
            assert msg.android.notification.sound == "default"
            assert msg.android.notification.channel_id == "default"

    def test_message_has_apns_config(self, fcm):
        with patch.object(fcm.messaging, "send", return_value="projects/x/messages/1") as mock_send:
            fcm.send_push("token123", "Title", "Body")

            msg = mock_send.call_args[0][0]
            assert msg.apns is not None
            assert msg.apns.payload.aps.sound == "default"

    def test_skips_when_not_initialized(self, fcm):
        fcm._initialized = False
        with patch.object(fcm.messaging, "send") as mock_send:
            fcm.send_push("token123", "Title", "Body")
            mock_send.assert_not_called()
        fcm._initialized = True

    def test_skips_when_no_token(self, fcm):
        with patch.object(fcm.messaging, "send") as mock_send:
            fcm.send_push("", "Title", "Body")
            mock_send.assert_not_called()

    def test_passes_data(self, fcm):
        with patch.object(fcm.messaging, "send", return_value="projects/x/messages/1") as mock_send:
            fcm.send_push("token123", "Title", "Body", data={"key": "val"})

            msg = mock_send.call_args[0][0]
            assert msg.data == {"key": "val"}
