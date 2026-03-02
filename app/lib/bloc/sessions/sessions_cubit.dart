import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/session.dart';
import '../../services/api.dart';
import 'sessions_state.dart';

class SessionsCubit extends Cubit<SessionsState> {
  final ApiService api;
  Timer? _timer;

  SessionsCubit(this.api) : super(const SessionsState()) {
    fetchSessions();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => fetchSessions());
  }

  Future<void> fetchSessions() async {
    try {
      final data = await api.getSessions(status: state.filter);
      final sessions = (data['sessions'] as List)
          .map((e) => Session.fromJson(e))
          .toList();
      emit(state.copyWith(
        sessions: sessions,
        total: data['total'] ?? sessions.length,
        status: SessionsStatus.loaded,
      ));
    } catch (_) {
      if (state.status == SessionsStatus.loading) {
        emit(state.copyWith(status: SessionsStatus.error));
      }
    }
  }

  void setFilter(String? filter) {
    emit(state.copyWith(
      filter: () => filter,
      status: SessionsStatus.loading,
    ));
    fetchSessions();
  }

  Future<void> deleteSession(String key) async {
    final updated = state.sessions.where((s) => s.sessionKey != key).toList();
    emit(state.copyWith(sessions: updated, total: state.total - 1));
    try {
      await api.deleteSession(key);
    } catch (_) {
      fetchSessions();
    }
  }

  @override
  Future<void> close() {
    _timer?.cancel();
    return super.close();
  }
}
