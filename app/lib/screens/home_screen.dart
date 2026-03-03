import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../services/api.dart';
import '../bloc/sessions/sessions_cubit.dart';
import '../bloc/pipelines/pipelines_cubit.dart';
import 'sessions_screen.dart';
import 'pipelines_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiService>();

    return MultiBlocProvider(
      providers: [
        BlocProvider(create: (_) => SessionsCubit(api)),
        BlocProvider(create: (_) => PipelinesCubit(api)),
      ],
      child: Scaffold(
        body: SafeArea(
          child: IndexedStack(
            index: _currentIndex,
            children: const [
              SessionsScreen(),
              PipelinesScreen(),
              SettingsScreen(),
            ],
          ),
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) => setState(() => _currentIndex = index),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.chat_outlined), selectedIcon: Icon(Icons.chat), label: 'Sessions'),
            NavigationDestination(icon: Icon(Icons.rocket_launch_outlined), selectedIcon: Icon(Icons.rocket_launch), label: 'Pipelines'),
            NavigationDestination(icon: Icon(Icons.settings_outlined), selectedIcon: Icon(Icons.settings), label: 'Settings'),
          ],
        ),
      ),
    );
  }
}
