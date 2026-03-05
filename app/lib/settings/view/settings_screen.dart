import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../auth/bloc/auth_bloc.dart';
import '../../auth/bloc/auth_event.dart';
import '../../services/api.dart';
import '../../theme/bloc/theme_cubit.dart';
import '../bloc/notification_settings_cubit.dart';
import '../bloc/notification_settings_state.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => NotificationSettingsCubit(context.read<ApiService>())..load(),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Settings', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w500)),
            const SizedBox(height: 16),
            BlocBuilder<ThemeCubit, ThemeMode>(
              builder: (context, themeMode) {
                return SwitchListTile(
                  title: const Text('Dark mode'),
                  subtitle: const Text('Use dark theme'),
                  value: themeMode == ThemeMode.dark,
                  onChanged: (_) => context.read<ThemeCubit>().toggle(),
                  contentPadding: EdgeInsets.zero,
                );
              },
            ),
            const SizedBox(height: 24),
            Text('Notifications', style: Theme.of(context).textTheme.titleSmall?.copyWith(color: Colors.grey)),
            const SizedBox(height: 4),
            BlocBuilder<NotificationSettingsCubit, NotificationSettingsState>(
              builder: (context, state) {
                if (state.status == NotificationSettingsStatus.loading) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                final cubit = context.read<NotificationSettingsCubit>();
                return Column(
                  children: [
                    SwitchListTile(
                      title: const Text('Session replies'),
                      value: state.sessions,
                      onChanged: cubit.toggleSessions,
                      contentPadding: EdgeInsets.zero,
                    ),
                    SwitchListTile(
                      title: const Text('Pipeline updates'),
                      value: state.pipelines,
                      onChanged: cubit.togglePipelines,
                      contentPadding: EdgeInsets.zero,
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: 24),
            Text('Account', style: Theme.of(context).textTheme.titleSmall?.copyWith(color: Colors.grey)),
            const SizedBox(height: 4),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Sign out', style: TextStyle(color: Colors.red)),
              leading: const Icon(Icons.logout, color: Colors.red),
              onTap: () => context.read<AuthBloc>().add(AuthLogoutRequested()),
            ),
          ],
        ),
      ),
    );
  }
}
