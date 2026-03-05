import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'auth/bloc/auth_bloc.dart';
import 'auth/bloc/auth_state.dart';
import 'auth/view/login_screen.dart';
import 'home/view/home_screen.dart';
import 'sessions/view/sessions_screen.dart';
import 'pipelines/view/pipelines_screen.dart';
import 'settings/view/settings_screen.dart';
import 'pipelines/view/pipeline_detail_screen.dart';
import 'sessions/view/chat_screen.dart';

GoRouter createRouter(AuthBloc authBloc) {
  return GoRouter(
    initialLocation: '/sessions',
    refreshListenable: GoRouterRefreshStream(authBloc.stream),
    redirect: (context, state) {
      final authState = authBloc.state;
      final isAuth = authState is AuthAuthenticated;
      final isLoggingIn = state.matchedLocation == '/login';

      if (authState is AuthInitial || authState is AuthLoading) return null;

      if (!isAuth && !isLoggingIn) return '/login';
      if (isAuth && isLoggingIn) return '/sessions';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            HomeShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/sessions',
                builder: (context, state) => const SessionsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/pipelines',
                builder: (context, state) => const PipelinesScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/settings',
                builder: (context, state) => const SettingsScreen(),
              ),
            ],
          ),
        ],
      ),
      // Full-screen detail routes (no bottom nav)
      GoRoute(
        path: '/sessions/:key',
        builder: (context, state) =>
            ChatScreen(sessionKey: state.pathParameters['key']!),
      ),
      GoRoute(
        path: '/pipelines/:key',
        builder: (context, state) =>
            PipelineDetailScreen(pipelineKey: state.pathParameters['key']!),
      ),
    ],
  );
}

class GoRouterRefreshStream extends ChangeNotifier {
  GoRouterRefreshStream(Stream<dynamic> stream) {
    notifyListeners();
    _subscription = stream.asBroadcastStream().listen((_) => notifyListeners());
  }

  late final StreamSubscription<dynamic> _subscription;

  @override
  void dispose() {
    _subscription.cancel();
    super.dispose();
  }
}
