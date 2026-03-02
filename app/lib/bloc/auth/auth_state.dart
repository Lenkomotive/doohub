import 'package:equatable/equatable.dart';

sealed class AuthState extends Equatable {
  const AuthState();

  @override
  List<Object?> get props => [];
}

class AuthInitial extends AuthState {}

class AuthLoading extends AuthState {}

class AuthAuthenticated extends AuthState {
  final String username;

  const AuthAuthenticated(this.username);

  @override
  List<Object?> get props => [username];
}

class AuthUnauthenticated extends AuthState {}

class AuthLoginFailure extends AuthState {}
