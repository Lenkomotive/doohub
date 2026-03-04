import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeCubit extends Cubit<ThemeMode> {
  static const _key = 'dark_mode';
  final SharedPreferences _prefs;

  ThemeCubit(this._prefs)
      : super(_prefs.getBool(_key) ?? true ? ThemeMode.dark : ThemeMode.light);

  bool get isDark => state == ThemeMode.dark;

  void toggle() {
    final next = isDark ? ThemeMode.light : ThemeMode.dark;
    _prefs.setBool(_key, next == ThemeMode.dark);
    emit(next);
  }
}
