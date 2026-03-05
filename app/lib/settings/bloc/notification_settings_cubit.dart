import 'package:flutter_bloc/flutter_bloc.dart';
import '../../services/api.dart';
import 'notification_settings_state.dart';

class NotificationSettingsCubit extends Cubit<NotificationSettingsState> {
  final ApiService _api;

  NotificationSettingsCubit(this._api) : super(const NotificationSettingsState());

  Future<void> load() async {
    try {
      final data = await _api.getNotificationSettings();
      emit(NotificationSettingsState(
        sessions: data['notify_sessions'] ?? true,
        pipelines: data['notify_pipelines'] ?? true,
        status: NotificationSettingsStatus.loaded,
      ));
    } catch (_) {
      emit(state.copyWith(status: NotificationSettingsStatus.error));
    }
  }

  Future<void> toggleSessions(bool value) async {
    emit(state.copyWith(sessions: value));
    try {
      await _api.updateNotificationSettings(sessions: value, pipelines: state.pipelines);
    } catch (_) {
      emit(state.copyWith(sessions: !value));
    }
  }

  Future<void> togglePipelines(bool value) async {
    emit(state.copyWith(pipelines: value));
    try {
      await _api.updateNotificationSettings(sessions: state.sessions, pipelines: value);
    } catch (_) {
      emit(state.copyWith(pipelines: !value));
    }
  }
}
