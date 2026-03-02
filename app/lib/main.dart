import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/api.dart';
import 'services/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const DooHubApp());
}

class DooHubApp extends StatelessWidget {
  const DooHubApp({super.key});

  @override
  Widget build(BuildContext context) {
    final api = ApiService();

    return ChangeNotifierProvider(
      create: (_) => AuthProvider(api),
      child: MaterialApp(
        title: 'DooHub',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
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
        ),
        home: Consumer<AuthProvider>(
          builder: (context, auth, _) {
            if (auth.isLoading) {
              return const Scaffold(
                body: Center(child: CircularProgressIndicator()),
              );
            }
            if (auth.isLoggedIn) {
              return HomeScreen(api: api);
            }
            return const LoginScreen();
          },
        ),
      ),
    );
  }
}
