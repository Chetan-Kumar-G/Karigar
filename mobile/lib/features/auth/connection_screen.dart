import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/app_config.dart';
import '../../core/theme.dart';
import '../../providers/app_state.dart';

/// Shown when the startup `/health` probe cannot reach the backend.
///
/// This is deliberately *not* a crash and *not* a login error — it tells the
/// user the server is unreachable and offers (a) a retry and (b) a way to point
/// the app at a different server address without rebuilding.
class ConnectionScreen extends StatefulWidget {
  const ConnectionScreen({super.key});

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  late final TextEditingController _addr =
      TextEditingController(text: AppConfig.apiBaseUrl);
  bool _busy = false;
  bool _showAdvanced = false;

  @override
  void dispose() {
    _addr.dispose();
    super.dispose();
  }

  Future<void> _retry({bool saveAddress = false}) async {
    setState(() => _busy = true);
    final app = context.read<AppState>();
    if (saveAddress) {
      await AppConfig.setOverride(_addr.text.trim());
    }
    final ok = await app.checkHealth();
    if (!mounted) return;
    setState(() {
      _busy = false;
      _addr.text = AppConfig.apiBaseUrl;
    });
    if (ok) {
      final signedIn = app.signedIn;
      context.go(signedIn ? (app.isArtisan ? '/home' : '/buyer') : '/onboarding');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(app.connError ?? 'Still cannot reach the server.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.cloud_off_rounded,
                    size: 64, color: AppTheme.inkSoft),
                const SizedBox(height: 20),
                Text('Can’t reach the server',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 10),
                Text(
                  'The app is working, but the Kārigar backend did not answer. '
                  'Your data is safe. Check that the server is running, then try again.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 18),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppTheme.sand,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _kv('Server', AppConfig.apiBaseUrl),
                      if (app.connError != null) _kv('Reason', app.connError!),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                ElevatedButton.icon(
                  onPressed: _busy ? null : () => _retry(),
                  icon: _busy
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.4, color: Colors.white))
                      : const Icon(Icons.refresh_rounded),
                  label: const Text('Try again'),
                ),
                const SizedBox(height: 6),
                TextButton(
                  onPressed: _busy
                      ? null
                      : () => setState(() => _showAdvanced = !_showAdvanced),
                  child: Text(_showAdvanced
                      ? 'Hide server settings'
                      : 'Change server address'),
                ),
                if (_showAdvanced) ...[
                  const SizedBox(height: 8),
                  TextField(
                    controller: _addr,
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    decoration: const InputDecoration(
                      labelText: 'Backend address',
                      helperText: 'e.g. 192.168.1.5:8000  or  http://host:8000/api\n'
                          'Emulator: 10.0.2.2:8000 · Web/desktop: localhost:8000',
                      helperMaxLines: 3,
                      prefixIcon: Icon(Icons.dns_rounded),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _busy
                              ? null
                              : () async {
                                  await AppConfig.setOverride(null);
                                  setState(
                                      () => _addr.text = AppConfig.apiBaseUrl);
                                },
                          child: const Text('Reset'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton(
                          onPressed:
                              _busy ? null : () => _retry(saveAddress: true),
                          child: const Text('Save & connect'),
                        ),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 8),
                TextButton(
                  onPressed: _busy
                      ? null
                      : () => context.go(app.signedIn
                          ? (app.isArtisan ? '/home' : '/buyer')
                          : '/onboarding'),
                  child: const Text('Continue offline'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
                width: 66,
                child: Text(k,
                    style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: AppTheme.inkSoft,
                        fontSize: 13))),
            Expanded(
                child: Text(v, style: const TextStyle(fontSize: 13))),
          ],
        ),
      );
}
