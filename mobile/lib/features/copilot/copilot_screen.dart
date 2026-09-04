import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';
import 'copilot_card_widget.dart';

class CopilotScreen extends StatefulWidget {
  const CopilotScreen({super.key});

  @override
  State<CopilotScreen> createState() => _CopilotScreenState();
}

class _CopilotScreenState extends State<CopilotScreen> {
  late Future<List<CopilotCard>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<CopilotCard>> _load() {
    final app = context.read<AppState>();
    return app.api.insights(app.session!.id);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Your AI Business Manager')),
      body: RefreshIndicator(
        onRefresh: () async => setState(() {
          _future = _load();
        }),
        child: FutureBuilder<List<CopilotCard>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView(label: 'Reviewing your business…');
            }
            if (snap.hasError) {
              return ListView(children: [
                const SizedBox(height: 120),
                ErrorView(snap.error!,
                    onRetry: () => setState(() {
                          _future = _load();
                        })),
              ]);
            }
            final cards = snap.data!;
            if (cards.isEmpty) {
              return const EmptyView(
                icon: Icons.check_circle_rounded,
                title: 'Nothing needs action',
                message:
                    'Your listings, prices and photos all look healthy right now.',
              );
            }
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  'Every recommendation below comes from structured F1/F4/F5/F6 '
                  'output. An LLM, if enabled, only rephrases it — it never '
                  'invents the numbers.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 14),
                for (final c in cards)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: CopilotCardWidget(card: c),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
