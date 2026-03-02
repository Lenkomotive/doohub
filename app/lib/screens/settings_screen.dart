import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../bloc/theme/theme_cubit.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
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
        ],
      ),
    );
  }
}
