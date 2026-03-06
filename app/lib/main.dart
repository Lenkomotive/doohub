import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'firebase_options.dart';
import 'services/api.dart';
import 'auth/bloc/auth_bloc.dart';
import 'sessions/bloc/sessions_cubit.dart';
import 'pipelines/bloc/pipelines_cubit.dart';
import 'theme/bloc/theme_cubit.dart';
import 'package:go_router/go_router.dart';
import 'router.dart';
import 'services/notification_handler.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  final prefs = await SharedPreferences.getInstance();
  runApp(DooHubApp(prefs: prefs));
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

class DooHubApp extends StatefulWidget {
  final SharedPreferences prefs;

  const DooHubApp({super.key, required this.prefs});

  @override
  State<DooHubApp> createState() => _DooHubAppState();
}

class _DooHubAppState extends State<DooHubApp> {
  late final ApiService _api;
  late final AuthBloc _authBloc;
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _api = ApiService();
    _authBloc = AuthBloc(_api);
    _router = createRouter(_authBloc);
    setupNotificationHandlers(_router);
  }

  @override
  void dispose() {
    _router.dispose();
    _authBloc.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RepositoryProvider.value(
      value: _api,
      child: MultiBlocProvider(
        providers: [
          BlocProvider.value(value: _authBloc),
          BlocProvider(create: (_) => ThemeCubit(widget.prefs)),
          BlocProvider(create: (_) => SessionsCubit(_api)),
          BlocProvider(create: (_) => PipelinesCubit(_api)),
        ],
        child: BlocBuilder<ThemeCubit, ThemeMode>(
          builder: (context, themeMode) {
            return MaterialApp.router(
              title: 'DooHub',
              debugShowCheckedModeBanner: false,
              theme: _lightTheme,
              darkTheme: _darkTheme,
              themeMode: themeMode,
              routerConfig: _router,
            );
          },
        ),
      ),
    );
  }
}
