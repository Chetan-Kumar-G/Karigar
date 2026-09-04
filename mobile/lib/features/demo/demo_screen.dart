import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../providers/app_state.dart';
import '../../providers/product_flow.dart';
import '../../widgets/common.dart';

/// SIH Demo Mode (spec §36, §37) — one-tap load / reset of the known dataset.
class DemoScreen extends StatefulWidget {
  const DemoScreen({super.key});

  @override
  State<DemoScreen> createState() => _DemoScreenState();
}

class _DemoScreenState extends State<DemoScreen> {
  bool _busy = false;
  String? _error;
  J _scenario = {};

  @override
  void initState() {
    super.initState();
    _loadScenario();
  }

  Future<void> _loadScenario() async {
    try {
      final s = await context.read<AppState>().api.demoScenario();
      setState(() => _scenario = s);
    } catch (e) {
      setState(() => _error = '$e');
    }
  }

  Future<void> _run(Future<void> Function() body, {String? goTo}) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await body();
      if (!mounted) return;
      if (goTo != null) context.go(goTo);
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final steps = asStringList(_scenario['steps']);
    return Scaffold(
      appBar: AppBar(title: const Text('SIH Demo Mode')),
      body: _busy
          ? const LoadingView(label: 'Preparing the demo dataset…')
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                SectionCard(
                  title: 'Scenario',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(asStr(_scenario['title'], 'Loading…'),
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 10),
                      Text(
                        'Artisan 9800000001 · Buyer 9900000001 · OTP '
                        '${asStr(_scenario['otp'], '123456')}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                if (_error != null) ...[
                  ErrorView(_error!),
                  const SizedBox(height: 12),
                ],
                ElevatedButton.icon(
                  onPressed: () => _run(() async {
                    context.read<ProductFlow>().reset();
                    await context.read<AppState>().loadDemo();
                  }, goTo: '/home'),
                  icon: const Icon(Icons.play_circle_fill_rounded),
                  label: const Text('Load demo & sign in as Meera'),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: () => _run(() async {
                    context.read<ProductFlow>().reset();
                    await context.read<AppState>().api.demoReset();
                  }),
                  icon: const Icon(Icons.restart_alt_rounded),
                  label: const Text('Reset demo data only'),
                ),
                const SizedBox(height: 20),
                if (asMap(_scenario['cast']).isNotEmpty)
                  _CastCard(cast: asMap(_scenario['cast'])),
                if (asMap(_scenario['cast']).isNotEmpty)
                  const SizedBox(height: 12),
                if (steps.isNotEmpty)
                  SectionCard(
                    title: 'Demo script',
                    child: Column(
                      children: [
                        for (var i = 0; i < steps.length; i++)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 5),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  width: 22,
                                  height: 22,
                                  alignment: Alignment.center,
                                  decoration: const BoxDecoration(
                                      color: AppTheme.sand,
                                      shape: BoxShape.circle),
                                  child: Text('${i + 1}',
                                      style: const TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w800)),
                                ),
                                const SizedBox(width: 10),
                                Expanded(child: Text(steps[i])),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }
}

class _CastCard extends StatelessWidget {
  const _CastCard({required this.cast});
  final J cast;

  @override
  Widget build(BuildContext context) {
    final buyers = asMapList(cast['buyers']);
    final artisans = asMapList(cast['artisans']);
    final walk = asStringList(cast['walkthrough']);
    Widget row(J m) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(
            children: [
              Expanded(
                child: Text('${m['name']}  ·  ${m['phone']}',
                    style: const TextStyle(fontWeight: FontWeight.w700)),
              ),
              Expanded(
                flex: 2,
                child: Text('${m['use_for'] ?? m['note'] ?? ''}',
                    style: Theme.of(context).textTheme.bodySmall),
              ),
            ],
          ),
        );
    return SectionCard(
      title: asStr(cast['title'], 'Named demo cast'),
      trailing: Text('OTP ${asStr(cast['otp'], '123456')}',
          style: Theme.of(context).textTheme.bodySmall),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Buyers',
              style: TextStyle(fontWeight: FontWeight.w800, color: AppTheme.ink)),
          for (final b in buyers) row(b),
          const SizedBox(height: 8),
          const Text('Artisans',
              style: TextStyle(fontWeight: FontWeight.w800, color: AppTheme.ink)),
          for (final a in artisans) row(a),
          if (walk.isNotEmpty) ...[
            const SizedBox(height: 10),
            const Divider(),
            const SizedBox(height: 4),
            for (var i = 0; i < walk.length; i++)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Text('${i + 1}.  ${walk[i]}',
                    style: Theme.of(context).textTheme.bodySmall),
              ),
          ],
        ],
      ),
    );
  }
}
