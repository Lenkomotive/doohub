import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:go_router/go_router.dart';

void _log(String msg) => print('[NotificationHandler] $msg');

Future<void> setupNotificationHandlers(GoRouter router) async {
  // Handle app launched from terminated state via notification tap
  final initialMessage = await FirebaseMessaging.instance.getInitialMessage();
  if (initialMessage != null) {
    _log('App opened from terminated state via notification');
    _handleMessage(initialMessage, router);
  }

  // Handle notification tap when app is in background
  FirebaseMessaging.onMessageOpenedApp.listen((message) {
    _log('App opened from background via notification');
    _handleMessage(message, router);
  });

  // Show notifications in foreground on iOS
  await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(
    alert: true,
    badge: true,
    sound: true,
  );
}

void _handleMessage(RemoteMessage message, GoRouter router) {
  final data = message.data;
  final type = data['type'];

  if (type == 'session') {
    final key = data['session_key'];
    if (key != null) {
      _log('Navigating to session: $key');
      router.go('/sessions/$key');
    }
  } else if (type == 'pipeline') {
    final key = data['pipeline_key'];
    if (key != null) {
      _log('Navigating to pipeline: $key');
      router.go('/pipelines/$key');
    }
  } else {
    _log('Unknown notification type: $type');
  }
}
