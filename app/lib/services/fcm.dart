import 'package:firebase_messaging/firebase_messaging.dart';
import 'api.dart';

Future<void> unregisterFcmToken() async {
  try {
    await FirebaseMessaging.instance.deleteToken();
  } catch (_) {}
}

Future<void> registerFcmToken(ApiService api) async {
  try {
    final messaging = FirebaseMessaging.instance;

    await messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );

    try {
      await messaging.getAPNSToken();
    } catch (_) {}

    String? token;
    for (var i = 0; i < 5 && token == null; i++) {
      try {
        token = await messaging.getToken();
      } catch (_) {
        if (i < 4) await Future.delayed(const Duration(seconds: 1));
      }
    }

    if (token != null) {
      await api.updateFcmToken(token);
    }

    messaging.onTokenRefresh.listen((newToken) {
      api.updateFcmToken(newToken);
    });
  } catch (_) {}
}
