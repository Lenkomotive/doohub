import 'package:flutter_bloc/flutter_bloc.dart';
import '../../services/api.dart';
import '../../services/fcm.dart';
import 'auth_event.dart';
import 'auth_state.dart';

class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final ApiService api;

  AuthBloc(this.api) : super(AuthInitial()) {
    on<AuthCheckRequested>(_onCheckRequested);
    on<AuthLoginRequested>(_onLoginRequested);
    on<AuthLogoutRequested>(_onLogoutRequested);

    add(AuthCheckRequested());
  }

  Future<void> _onCheckRequested(
    AuthCheckRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    final hasToken = await api.hasToken();
    if (hasToken) {
      final user = await api.getMe();
      if (user != null) {
        emit(AuthAuthenticated(user['username']));
        registerFcmToken(api);
        return;
      }
    }
    emit(AuthUnauthenticated());
  }

  Future<void> _onLoginRequested(
    AuthLoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    final success = await api.login(event.username, event.password);
    if (success) {
      emit(AuthAuthenticated(event.username));
      registerFcmToken(api);
    } else {
      emit(AuthLoginFailure());
    }
  }

  Future<void> _onLogoutRequested(
    AuthLogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    await api.logout();
    await unregisterFcmToken();
    emit(AuthUnauthenticated());
  }
}
