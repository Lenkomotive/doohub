import 'package:flutter/material.dart';
import '../services/api.dart';
import '../services/auth_provider.dart';
import 'package:provider/provider.dart';
import 'sessions_screen.dart';
import 'pipelines_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  final ApiService api;

  const HomeScreen({super.key, required this.api});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: IndexedStack(
          index: _currentIndex,
          children: [
            SessionsScreen(api: widget.api),
            PipelinesScreen(api: widget.api),
            const SettingsScreen(),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          if (index == 3) {
            // Logout
            context.read<AuthProvider>().logout();
            return;
          }
          setState(() => _currentIndex = index);
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.chat_outlined), selectedIcon: Icon(Icons.chat), label: 'Sessions'),
          NavigationDestination(icon: Icon(Icons.account_tree_outlined), selectedIcon: Icon(Icons.account_tree), label: 'Pipelines'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), selectedIcon: Icon(Icons.settings), label: 'Settings'),
          NavigationDestination(icon: Icon(Icons.logout), label: 'Logout'),
        ],
      ),
    );
  }
}
