import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const _storage = FlutterSecureStorage();
  late final Dio _dio;

  static const String baseUrl = 'https://api.doohub.io';

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 300),
      headers: {'Content-Type': 'application/json'},
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _refreshToken();
          if (refreshed) {
            // Retry the original request
            final token = await _storage.read(key: 'access_token');
            error.requestOptions.headers['Authorization'] = 'Bearer $token';
            final response = await _dio.fetch(error.requestOptions);
            return handler.resolve(response);
          }
        }
        handler.next(error);
      },
    ));
  }

  // Auth

  Future<bool> login(String username, String password) async {
    try {
      final res = await _dio.post('/auth/login', data: {
        'username': username,
        'password': password,
      });
      await _storage.write(key: 'access_token', value: res.data['access_token']);
      await _storage.write(key: 'refresh_token', value: res.data['refresh_token']);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;
      final res = await _dio.post('/auth/refresh', data: {
        'refresh_token': refreshToken,
      });
      await _storage.write(key: 'access_token', value: res.data['access_token']);
      await _storage.write(key: 'refresh_token', value: res.data['refresh_token']);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>?> getMe() async {
    try {
      final res = await _dio.get('/auth/me');
      return res.data;
    } catch (_) {
      return null;
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  Future<bool> hasToken() async {
    final token = await _storage.read(key: 'access_token');
    return token != null;
  }

  // Sessions

  Future<Map<String, dynamic>> getSessions({String? status}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    final res = await _dio.get('/sessions', queryParameters: params);
    return res.data;
  }

  Future<Map<String, dynamic>> getSession(String key) async {
    final res = await _dio.get('/sessions/$key');
    return res.data;
  }

  Future<void> deleteSession(String key) async {
    await _dio.delete('/sessions/$key');
  }

  Future<void> cancelSession(String key) async {
    await _dio.post('/sessions/$key/cancel');
  }

  Future<Map<String, dynamic>> createSession({
    required String sessionKey,
    String model = 'sonnet',
    required String projectPath,
    bool interactive = false,
  }) async {
    final res = await _dio.post('/sessions', data: {
      'session_key': sessionKey,
      'model': model,
      'project_path': projectPath,
      'interactive': interactive,
    });
    return res.data;
  }

  Future<Map<String, dynamic>> getHistory(String key, {int limit = 50, int offset = 0}) async {
    final res = await _dio.get('/sessions/$key/history', queryParameters: {
      'limit': limit,
      'offset': offset,
    });
    return res.data;
  }

  Future<Map<String, dynamic>> sendMessage(String key, String content) async {
    final res = await _dio.post('/sessions/$key/messages', data: {
      'content': content,
    });
    return res.data;
  }

  // Repos

  Future<Map<String, dynamic>> getRepos() async {
    final res = await _dio.get('/repos');
    return res.data;
  }
}
