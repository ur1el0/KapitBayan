import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../config/app_config.dart';
import 'api_exception.dart';

/// Centralized HTTP client managing requests, headers, cookies, timeouts,
/// and error mapping for KapitBayan REST APIs.
class ApiClient {
  final http.Client _client;
  final String _baseUrl;
  String? _accessToken;
  String? _cookieHeader;
  Future<bool>? _refreshInFlight;
  int _authSessionRevision = 0;
  int _credentialsRevision = 0;

  /// Optional listener triggered whenever a token refresh succeeds with the new access token and cookie header.
  Future<void> Function(String newAccessToken, String? newCookieHeader)?
  onTokenRefreshed;

  ApiClient({http.Client? client, String? baseUrl})
    : _client = client ?? http.Client(),
      _baseUrl = baseUrl ?? AppConfig.baseUrl;

  String get baseUrl => _baseUrl;
  String? get accessToken => _accessToken;
  String? get cookieHeader => _cookieHeader;

  /// Update active in-memory tokens and cookies
  void setAuthCredentials({String? accessToken, String? cookieHeader}) {
    final nextCookieHeader = cookieHeader ?? _cookieHeader;
    if (accessToken != _accessToken || nextCookieHeader != _cookieHeader) {
      _authSessionRevision++;
      _credentialsRevision++;
    }
    _accessToken = accessToken;
    _cookieHeader = nextCookieHeader;
  }

  /// Clear stored credentials
  void clearAuthCredentials() {
    if (_accessToken != null || _cookieHeader != null) {
      _authSessionRevision++;
      _credentialsRevision++;
    }
    _accessToken = null;
    _cookieHeader = null;
  }

  /// Performs a silent token refresh using the stored refresh cookie or token payload
  Future<bool> refreshAccessToken() {
    final currentRefresh = _refreshInFlight;
    if (currentRefresh != null) return currentRefresh;

    late final Future<bool> refreshFuture;
    refreshFuture = _performAccessTokenRefresh().whenComplete(() {
      if (identical(_refreshInFlight, refreshFuture)) {
        _refreshInFlight = null;
      }
    });
    _refreshInFlight = refreshFuture;
    return refreshFuture;
  }

  Future<bool> _performAccessTokenRefresh() async {
    final sessionRevision = _authSessionRevision;
    final cookieHeader = _cookieHeader;
    try {
      if (cookieHeader == null || cookieHeader.isEmpty) return false;

      // Extract raw token value if stored in cookie format (e.g., refresh_token=...)
      String? rawRefreshToken;
      final match = RegExp(r'refresh_token=([^;]+)').firstMatch(cookieHeader);
      if (match != null) {
        rawRefreshToken = match.group(1);
      } else {
        rawRefreshToken = cookieHeader;
      }

      final response = await _client
          .post(
            _buildUri(AppConfig.tokenRefreshEndpoint),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
              'Cookie': cookieHeader,
            },
            body: rawRefreshToken != null
                ? jsonEncode({'refresh': rawRefreshToken})
                : null,
          )
          .timeout(AppConfig.requestTimeout);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final Map<String, dynamic> data = jsonDecode(
          utf8.decode(response.bodyBytes),
        );
        final newAccess = data['access'] as String?;
        final newCookie = extractSetCookie(response) ?? cookieHeader;

        if (newAccess != null) {
          // Do not let a late refresh from the previous login replace the
          // active user's stored or in-memory credentials.
          if (_authSessionRevision != sessionRevision) return false;

          final tokenRefreshHandler = onTokenRefreshed;
          if (tokenRefreshHandler != null) {
            await tokenRefreshHandler(newAccess, newCookie);
          }

          if (_authSessionRevision != sessionRevision) return false;
          _setRefreshedCredentials(newAccess, newCookie);
          return true;
        }
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  void _setRefreshedCredentials(String accessToken, String? cookieHeader) {
    _accessToken = accessToken;
    _cookieHeader = cookieHeader;
    _credentialsRevision++;
  }

  /// Extracts the `refresh_token` or cookie string from response headers
  String? extractSetCookie(http.Response response) {
    final rawCookie = response.headers['set-cookie'];
    if (rawCookie == null || rawCookie.isEmpty) {
      return null;
    }
    // Extract refresh_token=<token_value> cleanly without breaking on date commas in 'expires='
    final match = RegExp(r'refresh_token=([^;]+)').firstMatch(rawCookie);
    if (match != null) {
      return 'refresh_token=${match.group(1)}';
    }
    // Fallback to first semicolon-delimited token
    final firstPart = rawCookie.split(';').first.trim();
    if (firstPart.isNotEmpty && firstPart.contains('=')) {
      return firstPart;
    }
    return null;
  }

  /// Perform a POST request
  Future<http.Response> post(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    bool requiresAuth = false,
  }) async {
    return _sendRequest(
      () => _client.post(
        _buildUri(endpoint),
        headers: _buildHeaders(headers, requiresAuth: requiresAuth),
        body: body != null ? jsonEncode(body) : null,
      ),
    );
  }

  /// Perform a POST request with multipart/form-data (for file uploads)
  Future<http.Response> postMultipart(
    String endpoint, {
    Map<String, String>? fields,
    List<http.MultipartFile>? files,
    bool requiresAuth = true,
  }) async {
    final requestFiles = List<http.MultipartFile>.of(files ?? const []);
    final replayableFiles = _hasRefreshCookie
        ? await _makeMultipartFilesReplayable(requestFiles)
        : null;
    final requestFields = Map<String, String>.of(fields ?? const {});
    return _sendRequest(
      () => _sendMultipartRequest(
        'POST',
        endpoint,
        fields: requestFields,
        filesForAttempt: replayableFiles == null
            ? () => requestFiles
            : () => replayableFiles
                  .map((file) => file.createMultipartFile())
                  .toList(),
        requiresAuth: requiresAuth,
      ),
    );
  }

  /// Perform a PATCH request with multipart/form-data (for file uploads and updates)
  Future<http.Response> patchMultipart(
    String endpoint, {
    Map<String, String>? fields,
    List<http.MultipartFile>? files,
    bool requiresAuth = true,
  }) async {
    final requestFiles = List<http.MultipartFile>.of(files ?? const []);
    final replayableFiles = _hasRefreshCookie
        ? await _makeMultipartFilesReplayable(requestFiles)
        : null;
    final requestFields = Map<String, String>.of(fields ?? const {});
    return _sendRequest(
      () => _sendMultipartRequest(
        'PATCH',
        endpoint,
        fields: requestFields,
        filesForAttempt: replayableFiles == null
            ? () => requestFiles
            : () => replayableFiles
                  .map((file) => file.createMultipartFile())
                  .toList(),
        requiresAuth: requiresAuth,
      ),
    );
  }

  Future<http.Response> _sendMultipartRequest(
    String method,
    String endpoint, {
    required Map<String, String> fields,
    required List<http.MultipartFile> Function() filesForAttempt,
    required bool requiresAuth,
  }) async {
    final request = http.MultipartRequest(method, _buildUri(endpoint));
    final headers = _buildHeaders(null, requiresAuth: requiresAuth);
    headers.remove('Content-Type');
    request.headers.addAll(headers);
    request.fields.addAll(fields);
    request.files.addAll(filesForAttempt());

    final streamedResponse = await _client.send(request);
    return http.Response.fromStream(streamedResponse);
  }

  bool get _hasRefreshCookie =>
      _cookieHeader != null && _cookieHeader!.isNotEmpty;

  /// Captures file streams once so a single token-refresh retry can build fresh requests.
  Future<List<_ReplayableMultipartFile>> _makeMultipartFilesReplayable(
    List<http.MultipartFile>? files,
  ) async {
    if (files == null || files.isEmpty) return const [];

    final replayable = <_ReplayableMultipartFile>[];
    for (final file in files) {
      replayable.add(
        _ReplayableMultipartFile(
          field: file.field,
          bytes: await file.finalize().toBytes(),
          filename: file.filename,
          contentType: file.contentType,
        ),
      );
    }
    return replayable;
  }

  /// Perform a GET request
  Future<http.Response> get(
    String endpoint, {
    Map<String, String>? queryParams,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    return _sendRequest(
      () => _client.get(
        _buildUri(endpoint, queryParams: queryParams),
        headers: _buildHeaders(headers, requiresAuth: requiresAuth),
      ),
    );
  }

  /// Perform a PUT request
  Future<http.Response> put(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    return _sendRequest(
      () => _client.put(
        _buildUri(endpoint),
        headers: _buildHeaders(headers, requiresAuth: requiresAuth),
        body: body != null ? jsonEncode(body) : null,
      ),
    );
  }

  /// Perform a PATCH request
  Future<http.Response> patch(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    return _sendRequest(
      () => _client.patch(
        _buildUri(endpoint),
        headers: _buildHeaders(headers, requiresAuth: requiresAuth),
        body: body != null ? jsonEncode(body) : null,
      ),
    );
  }

  /// Perform a DELETE request
  Future<http.Response> delete(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    return _sendRequest(
      () => _client.delete(
        _buildUri(endpoint),
        headers: _buildHeaders(headers, requiresAuth: requiresAuth),
        body: body != null ? jsonEncode(body) : null,
      ),
    );
  }

  /// Constructs the full URI with optional query parameters
  Uri _buildUri(String endpoint, {Map<String, String>? queryParams}) {
    final cleanBase = _baseUrl.endsWith('/')
        ? _baseUrl.substring(0, _baseUrl.length - 1)
        : _baseUrl;
    final cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/$endpoint';
    final fullUrl = '$cleanBase$cleanEndpoint';

    final uri = Uri.parse(fullUrl);
    if (kReleaseMode && uri.scheme != 'https') {
      throw StateError(
        'Release builds require an HTTPS endpoint. Cleartext HTTP is prohibited: $fullUrl',
      );
    }
    if (queryParams != null && queryParams.isNotEmpty) {
      return uri.replace(queryParameters: queryParams);
    }
    return uri;
  }

  /// Prepares standard request headers
  Map<String, String> _buildHeaders(
    Map<String, String>? customHeaders, {
    bool requiresAuth = false,
  }) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (requiresAuth && _accessToken != null && _accessToken!.isNotEmpty) {
      headers['Authorization'] = 'Bearer $_accessToken';
    }

    if (_cookieHeader != null && _cookieHeader!.isNotEmpty) {
      headers['Cookie'] = _cookieHeader!;
    }

    if (customHeaders != null) {
      headers.addAll(customHeaders);
    }

    return headers;
  }

  /// Executes request with timeout and maps network/HTTP status errors
  Future<http.Response> _sendRequest(
    Future<http.Response> Function() requestFn,
  ) async {
    try {
      final sessionRevisionAtRequest = _authSessionRevision;
      final credentialsRevisionAtRequest = _credentialsRevision;
      var response = await requestFn().timeout(AppConfig.requestTimeout);

      // Check if response indicates success (2xx)
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return response;
      }

      // Automatic silent retry on 401 Unauthorized if refresh cookie is present
      if (response.statusCode == 401 && _hasRefreshCookie) {
        if (_authSessionRevision != sessionRevisionAtRequest) {
          _handleHttpError(response);
          return response;
        }

        // Another request may already have rotated the token while this
        // request was in flight. Retry with the updated credentials instead
        // of rotating the new refresh token again.
        if (_credentialsRevision != credentialsRevisionAtRequest) {
          response = await requestFn().timeout(AppConfig.requestTimeout);
        } else {
          final refreshed = await refreshAccessToken();
          if (_authSessionRevision != sessionRevisionAtRequest) {
            _handleHttpError(response);
            return response;
          }
          if (refreshed) {
            response = await requestFn().timeout(AppConfig.requestTimeout);
          }
        }

        if (response.statusCode >= 200 && response.statusCode < 300) {
          return response;
        }
      }
      // Handle HTTP error statuses
      _handleHttpError(response);
      return response;
    } on SocketException catch (_) {
      throw const NetworkException();
    } on TimeoutException catch (_) {
      throw const NetworkException(
        'Request timed out. Please verify the server is reachable.',
      );
    } on http.ClientException catch (_) {
      throw const NetworkException();
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const ApiException('The request failed. Please try again.');
    }
  }

  /// Parses error responses from Django Rest Framework
  void _handleHttpError(http.Response response) {
    dynamic decodedBody;
    try {
      if (response.body.isNotEmpty) {
        decodedBody = jsonDecode(utf8.decode(response.bodyBytes));
      }
    } catch (_) {
      decodedBody = null;
    }

    String? detailMessage;
    if (decodedBody is Map<String, dynamic>) {
      if (decodedBody.containsKey('detail')) {
        detailMessage = decodedBody['detail']?.toString();
      } else if (decodedBody.containsKey('error')) {
        detailMessage = decodedBody['error']?.toString();
      } else if (decodedBody.containsKey('message')) {
        detailMessage = decodedBody['message']?.toString();
      }
    }

    switch (response.statusCode) {
      case 400:
        if (decodedBody is Map<String, dynamic>) {
          throw ValidationException.fromDrfErrors(decodedBody);
        }
        throw ValidationException(
          detailMessage ?? 'Bad request. Please check submitted data.',
          details: decodedBody,
        );

      case 401:
        String message =
            'Invalid credentials or session expired. Please log in again.';
        if (detailMessage != null && detailMessage.isNotEmpty) {
          final lower = detailMessage.toLowerCase();
          if (lower.contains('token not valid') ||
              lower.contains('token is invalid') ||
              lower.contains('given token not valid') ||
              lower.contains('token has expired') ||
              lower.contains('token_not_valid')) {
            message = 'Your session has expired. Please log in again.';
          } else {
            message = detailMessage;
          }
        }
        throw UnauthorizedException(message, decodedBody);

      case 403:
        throw ForbiddenException(
          detailMessage ?? 'Access forbidden. Verification required.',
          decodedBody,
        );

      case 404:
        throw NotFoundException(
          detailMessage ?? 'Requested resource was not found.',
          decodedBody,
        );

      default:
        if (response.statusCode >= 500) {
          throw ApiException(
            'The service could not complete this request. Please try again.',
            statusCode: response.statusCode,
          );
        }
        throw ApiException(
          detailMessage ??
              'Request failed with status code ${response.statusCode}.',
          statusCode: response.statusCode,
          details: decodedBody,
        );
    }
  }
}

class _ReplayableMultipartFile {
  const _ReplayableMultipartFile({
    required this.field,
    required this.bytes,
    required this.filename,
    required this.contentType,
  });

  final String field;
  final List<int> bytes;
  final String? filename;
  final http.MediaType contentType;

  http.MultipartFile createMultipartFile() => http.MultipartFile.fromBytes(
    field,
    bytes,
    filename: filename,
    contentType: contentType,
  );
}
