import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../widgets/glass.dart';
import '../services/api.dart';
import '../bloc/auth/auth_bloc.dart';
import '../bloc/auth/auth_event.dart';
import '../bloc/sessions/sessions_cubit.dart';
import 'sessions_screen.dart';

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

    return BlocProvider(
      create: (_) => SessionsCubit(api),
      child: Scaffold(
        body: SafeArea(
          child: IndexedStack(
            index: _currentIndex,
            children: const [
              SessionsScreen(),
            ],
          ),
        ),
        bottomNavigationBar: GlassBar(
          child: NavigationBar(
            backgroundColor: Colors.transparent,
            selectedIndex: _currentIndex,
            onDestinationSelected: (index) {
              if (index == 1) {
                context.read<AuthBloc>().add(AuthLogoutRequested());
                return;
              }
              setState(() => _currentIndex = index);
            },
            destinations: const [
              NavigationDestination(icon: Icon(Icons.chat_outlined), selectedIcon: Icon(Icons.chat), label: 'Sessions'),
              NavigationDestination(icon: Icon(Icons.logout), label: 'Logout'),
            ],
          ),
        ),
      ),
    );
  }
}
