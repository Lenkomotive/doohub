import 'package:flutter/material.dart';
import 'api.dart';

class AuthProvider extends ChangeNotifier {
  final ApiService api;
  bool _isLoggedIn = false;
  bool _isLoading = true;
  String? _username;

  AuthProvider(this.api) {
    _checkAuth();
  }

  bool get isLoggedIn => _isLoggedIn;
  bool get isLoading => _isLoading;
  String? get username => _username;

  Future<void> _checkAuth() async {
    _isLoading = true;
    notifyListeners();

    final hasToken = await api.hasToken();
    if (hasToken) {
      final user = await api.getMe();
      if (user != null) {
        _isLoggedIn = true;
        _username = user['username'];
      }
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    final success = await api.login(username, password);
    if (success) {
      _isLoggedIn = true;
      _username = username;
      notifyListeners();
    }
    return success;
  }

  Future<void> logout() async {
    await api.logout();
    _isLoggedIn = false;
    _username = null;
    notifyListeners();
  }
}
