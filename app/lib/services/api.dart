import 'dart:convert';
import 'dart:io';

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
    required String name,
    String model = 'sonnet',
    required String projectPath,
    bool interactive = false,
  }) async {
    final res = await _dio.post('/sessions', data: {
      'name': name,
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

  Future<Map<String, dynamic>> sendMessage(String key, String content, {List<int>? attachmentIds}) async {
    final res = await _dio.post('/sessions/$key/messages', data: {
      'content': content,
      if (attachmentIds != null && attachmentIds.isNotEmpty) 'attachment_ids': attachmentIds,
    });
    return res.data;
  }

  Future<Map<String, dynamic>> uploadAttachment(String key, File file) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: file.path.split('/').last),
    });
    final res = await _dio.post('/sessions/$key/upload', data: formData);
    return res.data;
  }

  // SSE streams

  Stream<Map<String, dynamic>> sessionEvents() async* {
    final token = await _storage.read(key: 'access_token');
    final uri = Uri.parse('$baseUrl/sessions/events');
    final request = await HttpClient().getUrl(uri)
      ..headers.set('Authorization', 'Bearer ${token ?? ''}')
      ..headers.set('Accept', 'text/event-stream')
      ..headers.set('Cache-Control', 'no-cache');
    final response = await request.close();
    String eventType = 'message';
    await for (final chunk in response.transform(const Utf8Decoder())) {
      for (final line in chunk.split('\n')) {
        if (line.startsWith('event:')) {
          eventType = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          final dataStr = line.substring(5).trim();
          try {
            final data = jsonDecode(dataStr) as Map<String, dynamic>;
            yield {'event': eventType, ...data};
          } catch (_) {}
          eventType = 'message';
        }
      }
    }
  }

  Stream<Map<String, dynamic>> streamMessage(String key, String content) async* {
    final token = await _storage.read(key: 'access_token');
    final uri = Uri.parse('$baseUrl/sessions/$key/messages/stream');
    final request = await HttpClient().postUrl(uri)
      ..headers.set('Authorization', 'Bearer ${token ?? ''}')
      ..headers.set('Accept', 'text/event-stream')
      ..headers.set('Content-Type', 'application/json')
      ..headers.set('Cache-Control', 'no-cache');
    request.write(jsonEncode({'content': content}));
    final response = await request.close();
    String eventType = 'message';
    await for (final chunk in response.transform(const Utf8Decoder())) {
      for (final line in chunk.split('\n')) {
        if (line.startsWith('event:')) {
          eventType = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          final dataStr = line.substring(5).trim();
          try {
            final data = jsonDecode(dataStr) as Map<String, dynamic>;
            yield {'event': eventType, ...data};
          } catch (_) {}
          eventType = 'message';
        }
      }
    }
  }

  // Pipelines

  Future<Map<String, dynamic>> getPipelines() async {
    final res = await _dio.get('/pipelines');
    return res.data;
  }

  Future<Map<String, dynamic>> createPipeline({
    required String repoPath,
    int? issueNumber,
    String? taskDescription,
    String model = 'claude-sonnet-4-6',
  }) async {
    final res = await _dio.post('/pipelines', data: {
      'repo_path': repoPath,
      if (issueNumber != null) 'issue_number': issueNumber,
      if (taskDescription != null) 'task_description': taskDescription,
      'model': model,
    });
    return res.data;
  }

  Future<void> cancelPipeline(String key) async {
    await _dio.post('/pipelines/$key/cancel');
  }

  Future<void> deletePipeline(String key) async {
    await _dio.delete('/pipelines/$key');
  }

  Stream<Map<String, dynamic>> pipelineEvents() async* {
    final token = await _storage.read(key: 'access_token');
    final uri = Uri.parse('$baseUrl/pipelines/events');
    final request = await HttpClient().getUrl(uri)
      ..headers.set('Authorization', 'Bearer ${token ?? ''}')
      ..headers.set('Accept', 'text/event-stream')
      ..headers.set('Cache-Control', 'no-cache');
    final response = await request.close();
    String eventType = 'message';
    await for (final chunk in response.transform(const Utf8Decoder())) {
      for (final line in chunk.split('\n')) {
        if (line.startsWith('event:')) {
          eventType = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          final dataStr = line.substring(5).trim();
          try {
            final data = jsonDecode(dataStr) as Map<String, dynamic>;
            yield {'event': eventType, ...data};
          } catch (_) {}
          eventType = 'message';
        }
      }
    }
  }

  // Repos

  Future<Map<String, dynamic>> getRepos() async {
    final res = await _dio.get('/repos');
    return res.data;
  }

  Future<Map<String, dynamic>> getIssues(String repoPath) async {
    final res = await _dio.get('/repos/issues', queryParameters: {'repo_path': repoPath});
    return res.data;
  }

  Future<Map<String, dynamic>> getIssue(String repoPath, int issueNumber) async {
    final res = await _dio.get('/repos/issue', queryParameters: {
      'repo_path': repoPath,
      'issue_number': issueNumber,
    });
    return res.data;
  }
}
