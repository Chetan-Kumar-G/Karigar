import 'package:artisan_market/core/api_client.dart';
import 'package:artisan_market/core/app_config.dart';
import 'package:artisan_market/services/api_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Phase 2 regression tests — backend connection reliability.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await AppConfig.setOverride(null);
  });

  group('AppConfig server-address resolution', () {
    test('defaults to the Android-emulator host', () {
      expect(AppConfig.apiBaseUrl, 'http://10.0.2.2:8000/api');
    });

    test('mediaHost is derived from the base URL (no separate define needed)',
        () {
      expect(AppConfig.mediaHost, 'http://10.0.2.2:8000');
    });

    test('runtime override normalises a bare host:port to a full /api URL',
        () async {
      await AppConfig.setOverride('192.168.1.5:8000');
      expect(AppConfig.apiBaseUrl, 'http://192.168.1.5:8000/api');
      expect(AppConfig.mediaHost, 'http://192.168.1.5:8000');
      expect(AppConfig.hasOverride, isTrue);
    });

    test('override accepts a full URL and is cleared by setOverride(null)',
        () async {
      await AppConfig.setOverride('http://localhost:8000/api');
      expect(AppConfig.apiBaseUrl, 'http://localhost:8000/api');
      await AppConfig.setOverride(null);
      expect(AppConfig.apiBaseUrl, 'http://10.0.2.2:8000/api');
      expect(AppConfig.hasOverride, isFalse);
    });

    test('override survives a reload via loadOverride()', () async {
      await AppConfig.setOverride('10.0.2.2:9000');
      await AppConfig.loadOverride();
      expect(AppConfig.apiBaseUrl, 'http://10.0.2.2:9000/api');
    });
  });

  group('health probe', () {
    test('parses status/database/version on success', () async {
      final api = ApiService(ApiClient(
        client: MockClient((req) async {
          expect(req.url.path, endsWith('/health'));
          return http.Response(
            '{"status":"ok","database":"ok","version":"0.1.0-prototype"}',
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      ));
      final h = await api.health();
      expect(h['status'], 'ok');
      expect(h['database'], 'ok');
      expect(h['version'], '0.1.0-prototype');
    });

    test('surfaces a network failure as ApiException(isNetwork) — not a crash',
        () async {
      final api = ApiService(ApiClient(
        client: MockClient((req) async => throw http.ClientException('boom')),
      ));
      await expectLater(
        api.health(),
        throwsA(isA<ApiException>().having((e) => e.isNetwork, 'isNetwork', true)),
      );
    });

    test('a 401 is auth, not network — the two are distinguishable', () async {
      final api = ApiService(ApiClient(
        client: MockClient((req) async => http.Response('{"detail":"nope"}', 401,
            headers: {'content-type': 'application/json'})),
      ));
      await expectLater(
        api.health(),
        throwsA(isA<ApiException>()
            .having((e) => e.isAuth, 'isAuth', true)
            .having((e) => e.isNetwork, 'isNetwork', false)),
      );
    });
  });
}
