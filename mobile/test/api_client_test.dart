import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';

void main() {
  test(
    'waits for token persistence before accepting refreshed credentials',
    () async {
      final callbackStarted = Completer<void>();
      final allowPersistenceToFinish = Completer<void>();

      final mockClient = MockClient(
        (_) async => http.Response(
          '{"access":"fresh-access-token"}',
          200,
          headers: {
            'set-cookie':
                'refresh_token=fresh-refresh-token; HttpOnly; Path=/; SameSite=Strict',
          },
        ),
      );
      addTearDown(mockClient.close);

      final apiClient = ApiClient(
        client: mockClient,
        baseUrl: 'https://example.test',
      );
      apiClient.setAuthCredentials(
        accessToken: 'old-access-token',
        cookieHeader: 'refresh_token=old-refresh-token',
      );

      apiClient.onTokenRefreshed = (newAccessToken, newCookieHeader) async {
        expect(newAccessToken, 'fresh-access-token');
        expect(newCookieHeader, 'refresh_token=fresh-refresh-token');

        callbackStarted.complete();
        await allowPersistenceToFinish.future;
      };

      final refreshFuture = apiClient.refreshAccessToken();
      await callbackStarted.future;

      // The refresh must not replace the active token before persistence finishes.
      expect(apiClient.accessToken, 'old-access-token');

      allowPersistenceToFinish.complete();

      expect(await refreshFuture, isTrue);
      expect(apiClient.accessToken, 'fresh-access-token');
      expect(apiClient.cookieHeader, 'refresh_token=fresh-refresh-token');
    },
  );

  test('keeps existing credentials if token persistence fails', () async {
    final mockClient = MockClient(
      (_) async => http.Response(
        '{"access":"fresh-access-token"}',
        200,
        headers: {
          'set-cookie':
              'refresh_token=fresh-refresh-token; HttpOnly; Path=/; SameSite=Strict',
        },
      ),
    );
    addTearDown(mockClient.close);

    final apiClient = ApiClient(
      client: mockClient,
      baseUrl: 'https://example.test',
    );
    apiClient.setAuthCredentials(
      accessToken: 'old-access-token',
      cookieHeader: 'refresh_token=old-refresh-token',
    );

    apiClient.onTokenRefreshed = (newAccessToken, newCookieHeader) async {
      throw StateError('Secure token persistence failed');
    };

    expect(await apiClient.refreshAccessToken(), isFalse);
    expect(apiClient.accessToken, 'old-access-token');
    expect(apiClient.cookieHeader, 'refresh_token=old-refresh-token');
  });

  test(
    'rebuilds multipart upload with refreshed credentials after 401',
    () async {
      final uploadRequests = <http.MultipartRequest>[];
      final uploadBodies = <List<int>>[];
      var refreshCalls = 0;

      final mockClient = MockClient.streaming((request, bodyStream) async {
        if (request.url.path.contains('token/refresh')) {
          refreshCalls += 1;
          await bodyStream.toBytes();
          return http.StreamedResponse(
            Stream.value(utf8.encode('{"access":"fresh-access-token"}')),
            200,
            headers: {
              'set-cookie':
                  'refresh_token=fresh-refresh-token; HttpOnly; Path=/; SameSite=Strict',
            },
          );
        }

        uploadRequests.add(request as http.MultipartRequest);
        uploadBodies.add(await bodyStream.toBytes());
        if (uploadRequests.length == 1) {
          return http.StreamedResponse(const Stream<List<int>>.empty(), 401);
        }
        return http.StreamedResponse(
          Stream.value(utf8.encode('{"ok":true}')),
          200,
        );
      });
      addTearDown(mockClient.close);

      final apiClient =
          ApiClient(client: mockClient, baseUrl: 'https://example.test/api/v1')
            ..setAuthCredentials(
              accessToken: 'expired-access-token',
              cookieHeader: 'refresh_token=old-refresh-token',
            );

      final response = await apiClient.postMultipart(
        '/documents/1/payment-reference/',
        fields: const {'payment_reference': 'REF-RETRY-42'},
        files: [
          http.MultipartFile.fromBytes(
            'payment_proof_image',
            utf8.encode('PROOF-BYTES-42'),
            filename: 'receipt.jpg',
          ),
        ],
      );

      expect(response.statusCode, 200);
      expect(refreshCalls, 1);
      expect(uploadRequests, hasLength(2));
      expect(uploadRequests[0].method, 'POST');
      expect(
        uploadRequests[0].headers['Authorization'],
        'Bearer expired-access-token',
      );
      expect(
        uploadRequests[1].headers['Authorization'],
        'Bearer fresh-access-token',
      );
      expect(uploadRequests[0], isNot(same(uploadRequests[1])));
      for (final body in uploadBodies) {
        final bodyText = latin1.decode(body);
        expect(bodyText, contains('REF-RETRY-42'));
        expect(bodyText, contains('PROOF-BYTES-42'));
      }
    },
  );

  test(
    'rebuilds multipart PATCH with refreshed credentials after 401',
    () async {
      final uploadRequests = <http.MultipartRequest>[];
      var refreshCalls = 0;
      final mockClient = MockClient.streaming((request, bodyStream) async {
        if (request.url.path.contains('token/refresh')) {
          refreshCalls += 1;
          await bodyStream.toBytes();
          return http.StreamedResponse(
            Stream.value(utf8.encode('{"access":"fresh-access-token"}')),
            200,
            headers: {'set-cookie': 'refresh_token=fresh-refresh-token'},
          );
        }
        uploadRequests.add(request as http.MultipartRequest);
        await bodyStream.toBytes();
        return http.StreamedResponse(
          const Stream<List<int>>.empty(),
          uploadRequests.length == 1 ? 401 : 200,
        );
      });
      addTearDown(mockClient.close);

      final apiClient =
          ApiClient(client: mockClient, baseUrl: 'https://example.test/api/v1')
            ..setAuthCredentials(
              accessToken: 'expired-access-token',
              cookieHeader: 'refresh_token=old-refresh-token',
            );

      final response = await apiClient.patchMultipart(
        '/documents/1/evidence/',
        fields: const {'note': 'updated'},
      );

      expect(response.statusCode, 200);
      expect(refreshCalls, 1);
      expect(uploadRequests, hasLength(2));
      expect(uploadRequests[0].method, 'PATCH');
      expect(
        uploadRequests[1].headers['Authorization'],
        'Bearer fresh-access-token',
      );
      expect(uploadRequests[0], isNot(same(uploadRequests[1])));
    },
  );

  test('does not expose unexpected exception details in API errors', () async {
    final mockClient = MockClient(
      (_) async => throw StateError('private server path and credentials'),
    );
    addTearDown(mockClient.close);

    final apiClient = ApiClient(
      client: mockClient,
      baseUrl: 'https://example.test',
    );

    await expectLater(
      apiClient.get('/health/', requiresAuth: false),
      throwsA(
        isA<ApiException>().having(
          (error) => error.message,
          'message',
          'The request failed. Please try again.',
        ),
      ),
    );
  });

  test('does not return server exception details in API errors', () async {
    final mockClient = MockClient(
      (_) async =>
          http.Response('{"detail":"private traceback and credentials"}', 500),
    );
    addTearDown(mockClient.close);

    final apiClient = ApiClient(
      client: mockClient,
      baseUrl: 'https://example.test',
    );

    await expectLater(
      apiClient.get('/health/', requiresAuth: false),
      throwsA(
        isA<ApiException>().having(
          (error) => error.message,
          'message',
          'The service could not complete this request. Please try again.',
        ),
      ),
    );
  });

  test(
    'does not attach stored refresh cookie header to routine API requests',
    () async {
      final recordedRequests = <http.BaseRequest>[];
      final mockClient = MockClient.streaming((request, bodyStream) async {
        recordedRequests.add(request);
        await bodyStream.toBytes();
        if (request.url.path.contains('token/refresh')) {
          return http.StreamedResponse(
            Stream.value(utf8.encode('{"access":"fresh-token"}')),
            200,
          );
        }
        return http.StreamedResponse(
          Stream.value(utf8.encode('{"ok":true}')),
          200,
        );
      });
      addTearDown(mockClient.close);

      final apiClient =
          ApiClient(client: mockClient, baseUrl: 'https://example.test/api/v1')
            ..setAuthCredentials(
              accessToken: 'access-123',
              cookieHeader: 'refresh_token=secret-refresh-token',
            );

      await apiClient.get('/documents/');
      await apiClient.post(
        '/auth/logout/',
        headers: {'Cookie': apiClient.cookieHeader!},
        requiresAuth: false,
      );
      await apiClient.refreshAccessToken();

      expect(recordedRequests, hasLength(3));
      expect(recordedRequests[0].headers.containsKey('Cookie'), isFalse);
      expect(
        recordedRequests[1].headers['Cookie'],
        'refresh_token=secret-refresh-token',
      );
      expect(
        recordedRequests[2].headers['Cookie'],
        'refresh_token=secret-refresh-token',
      );
    },
  );
}
