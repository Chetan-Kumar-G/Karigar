import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'app_config.dart';

/// An in-memory file part for multipart uploads (web-safe — no `dart:io`).
class UploadPart {
  const UploadPart(this.bytes, this.filename);
  final Uint8List bytes;
  final String filename;
}

/// Human-readable API failure (spec §26 — never surface a raw 500 to the user).
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.isNetwork = false});

  final String message;
  final int? statusCode;
  final bool isNetwork;

  bool get isAuth => statusCode == 401 || statusCode == 403;
  // Backend says this failed only from transient write contention (spec §26
  // db-lock handling) — safe to retry automatically once.
  bool get isRetryable => statusCode == 503;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  String? _token;

  void setToken(String? token) => _token = token;
  bool get hasToken => _token != null;

  Map<String, String> get _headers => {
        'Accept': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final base = Uri.parse('${AppConfig.apiBaseUrl}$path');
    if (query == null) return base;
    final merged = <String, String>{};
    query.forEach((k, v) {
      if (v != null) merged[k] = '$v';
    });
    return base.replace(queryParameters: {...base.queryParameters, ...merged});
  }

  Future<dynamic> get(String path,
      {Map<String, dynamic>? query, Duration? timeout}) {
    return _send(
      () => _client.get(_uri(path, query), headers: _headers),
      timeout ?? AppConfig.apiTimeout,
      'GET $path',
    );
  }

  Future<dynamic> postJson(String path, Map<String, dynamic> body,
      {Duration? timeout}) {
    return _send(
      () => _client.post(_uri(path),
          headers: {..._headers, 'Content-Type': 'application/json'},
          body: jsonEncode(body)),
      timeout ?? AppConfig.aiTimeout,
      'POST $path',
    );
  }

  Future<dynamic> postForm(String path, Map<String, String> fields,
      {Map<String, dynamic>? query, Duration? timeout}) {
    return _send(
      () => _client.post(_uri(path, query), headers: _headers, body: fields),
      timeout ?? AppConfig.aiTimeout,
      'POST $path',
    );
  }

  /// Multipart upload — [files] maps a field name to an in-memory [UploadPart].
  /// Bytes-based so it works identically on mobile and web.
  Future<dynamic> postMultipart(
    String path, {
    Map<String, String> fields = const {},
    Map<String, UploadPart> files = const {},
    Duration? timeout,
  }) {
    Future<http.Response> run() async {
      final req = http.MultipartRequest('POST', _uri(path))
        ..headers.addAll(_headers)
        ..fields.addAll(fields);
      for (final e in files.entries) {
        req.files.add(http.MultipartFile.fromBytes(
          e.key,
          e.value.bytes,
          filename: e.value.filename,
        ));
      }
      final streamed = await _client.send(req);
      return http.Response.fromStream(streamed);
    }

    return _send(run, timeout ?? AppConfig.aiTimeout, 'MULTIPART $path');
  }

  Future<dynamic> _send(
    Future<http.Response> Function() run,
    Duration timeout,
    String label,
  ) async {
    http.Response res;
    try {
      res = await run().timeout(timeout);
    } on TimeoutException {
      throw ApiException(
        'This is taking longer than expected. Check your connection and try again.',
        isNetwork: true,
      );
    } on http.ClientException {
      throw ApiException(
        'No connection to the server. Your work is saved — try again when you are online.',
        isNetwork: true,
      );
    } catch (e) {
      throw ApiException('Could not reach the server. Please try again.',
          isNetwork: true);
    }

    final ok = res.statusCode >= 200 && res.statusCode < 300;
    dynamic decoded;
    if (res.body.isNotEmpty) {
      try {
        decoded = jsonDecode(res.body);
      } catch (_) {
        decoded = null;
      }
    }

    if (ok) return decoded;

    final detail = decoded is Map && decoded['detail'] != null
        ? decoded['detail']
        : 'Something went wrong ($label · ${res.statusCode}).';
    throw ApiException(
      detail is List ? detail.map((e) => e['msg'] ?? e).join(', ') : '$detail',
      statusCode: res.statusCode,
    );
  }
}
