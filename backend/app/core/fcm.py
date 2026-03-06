import logging
import os

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if _cred_path and os.path.exists(_cred_path):
    cred = credentials.Certificate(_cred_path)
    firebase_admin.initialize_app(cred)
    _initialized = True
else:
    _initialized = False
    logger.warning("Firebase credentials not found, push notifications disabled")


def send_push(fcm_token: str, title: str, body: str, data: dict | None = None) -> None:
    if not _initialized:
        logger.warning("send_push skipped: Firebase not initialized")
        return
    if not fcm_token:
        logger.warning("send_push skipped: no FCM token")
        return
    try:
        message = messaging.Message(
            token=fcm_token,
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="default",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default"),
                ),
            ),
        )
        resp = messaging.send(message)
        logger.info("Push sent successfully: %s", resp)
    except Exception:
        logger.exception("Failed to send push notification")
