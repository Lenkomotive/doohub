import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'firebase_options.dart';
import 'services/api.dart';
import 'auth/bloc/auth_bloc.dart';
import 'auth/bloc/auth_state.dart';
import 'theme/bloc/theme_cubit.dart';
import 'auth/view/login_screen.dart';
import 'home/view/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  final prefs = await SharedPreferences.getInstance();
  runApp(DooHubApp(prefs: prefs));

  // Init FCM in background, don't block app startup
  Future.delayed(const Duration(milliseconds: 500), _initFCM);
}

Future<void> _initFCM() async {
  try {
    final messaging = FirebaseMessaging.instance;
    
    // Request permissions
    await messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );
    
    // On iOS, get APNS token first
    try {
      await messaging.getAPNSToken();
    } catch (_) {}

    // Get FCM token with retries
    String? token;
    for (var i = 0; i < 5 && token == null; i++) {
      try {
        token = await messaging.getToken();
      } catch (_) {
        if (i < 4) await Future.delayed(const Duration(seconds: 1));
      }
    }

    FirebaseMessaging.onMessage.listen((message) {
      // TODO: show in-app notification
    });
  } catch (_) {}
}

final _darkTheme = ThemeData(
  colorScheme: ColorScheme.fromSeed(
    seedColor: Colors.grey,
    brightness: Brightness.dark,
  ),
  useMaterial3: true,
  cardTheme: CardThemeData(
    color: const Color(0xFF1E1E1E),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    elevation: 0,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: Colors.transparent,
    elevation: 0,
    scrolledUnderElevation: 0,
  ),
  navigationBarTheme: NavigationBarThemeData(
    backgroundColor: const Color(0xFF141414),
    indicatorColor: Colors.white.withValues(alpha: 0.1),
    height: 60,
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: const Color(0xFF1E1E1E),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: BorderSide.none,
    ),
  ),
  scaffoldBackgroundColor: const Color(0xFF0F0F0F),
);

final _lightTheme = ThemeData(
  colorScheme: ColorScheme.fromSeed(
    seedColor: Colors.grey,
    brightness: Brightness.light,
  ),
  useMaterial3: true,
  cardTheme: CardThemeData(
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    elevation: 0,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: Colors.transparent,
    elevation: 0,
    scrolledUnderElevation: 0,
  ),
  navigationBarTheme: const NavigationBarThemeData(
    height: 60,
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: BorderSide.none,
    ),
  ),
);

class DooHubApp extends StatelessWidget {
  final SharedPreferences prefs;

  const DooHubApp({super.key, required this.prefs});

  @override
  Widget build(BuildContext context) {
    final api = ApiService();

    return RepositoryProvider.value(
      value: api,
      child: MultiBlocProvider(
        providers: [
          BlocProvider(create: (_) => AuthBloc(api)),
          BlocProvider(create: (_) => ThemeCubit(prefs)),
        ],
        child: BlocBuilder<ThemeCubit, ThemeMode>(
          builder: (context, themeMode) {
            return MaterialApp(
              title: 'DooHub',
              debugShowCheckedModeBanner: false,
              theme: _lightTheme,
              darkTheme: _darkTheme,
              themeMode: themeMode,
              home: BlocBuilder<AuthBloc, AuthState>(
                builder: (context, state) {
                  if (state is AuthLoading || state is AuthInitial) {
                    return const Scaffold(
                      body: Center(child: CircularProgressIndicator()),
                    );
                  }
                  if (state is AuthAuthenticated) {
                    return const HomeScreen();
                  }
                  return const LoginScreen();
                },
              ),
            );
          },
        ),
      ),
    );
  }
}
