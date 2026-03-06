import 'dart:developer' as developer;
import 'dart:io' show Platform;

import 'package:firebase_messaging/firebase_messaging.dart';
import 'api.dart';

void _log(String msg) => developer.log(msg, name: 'FCM');

Future<void> registerFcmToken(ApiService api) async {
  try {
    final messaging = FirebaseMessaging.instance;

    final settings = await messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );
    _log('Permission status: ${settings.authorizationStatus}');

    if (Platform.isIOS) {
      String? apnsToken;
      for (var i = 0; i < 5 && apnsToken == null; i++) {
        try {
          apnsToken = await messaging.getAPNSToken();
          _log('APNS token (attempt ${i + 1}): ${apnsToken ?? "null"}');
        } catch (e) {
          _log('APNS token error (attempt ${i + 1}): $e');
        }
        if (apnsToken == null && i < 4) {
          await Future.delayed(const Duration(seconds: 2));
        }
      }
      if (apnsToken == null) {
        _log('Failed to get APNS token after 5 attempts');
        return;
      }
    }

    String? token;
    for (var i = 0; i < 5 && token == null; i++) {
      try {
        token = await messaging.getToken();
        _log('FCM token (attempt ${i + 1}): ${token ?? "null"}');
      } catch (e) {
        _log('FCM token error (attempt ${i + 1}): $e');
        if (i < 4) await Future.delayed(const Duration(seconds: 1));
      }
    }

    if (token != null) {
      await api.updateFcmToken(token);
      _log('FCM token sent to backend');
    } else {
      _log('Failed to get FCM token after 5 attempts');
    }

    messaging.onTokenRefresh.listen((newToken) {
      _log('FCM token refreshed');
      api.updateFcmToken(newToken);
    });
  } catch (e) {
    _log('registerFcmToken error: $e');
  }
}
