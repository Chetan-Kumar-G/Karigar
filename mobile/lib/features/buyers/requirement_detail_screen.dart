import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/ai_progress.dart';
import '../../widgets/common.dart';

class RequirementDetailScreen extends StatefulWidget {
  const RequirementDetailScreen({required this.requirementId, super.key});
  final String requirementId;

  @override
  State<RequirementDetailScreen> createState() =>
      _RequirementDetailScreenState();
}

class _RequirementDetailScreenState extends State<RequirementDetailScreen> {
  late Future<Requirement> _future;
  bool _matching = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _future =
        context.read<AppState>().api.requirement(widget.requirementId);
  }

  Future<void> _findCluster() async {
    final api = context.read<AppState>().api;
    setState(() {
      _matching = true;
      _error = null;
    });
    try {
      final order = await api.buyerMatch(requirementId: widget.requirementId);
      if (!mounted) return;
      context.push('/buyer/allocation/${order.id}');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _matching = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isArtisan = context.read<AppState>().isArtisan;
    return Scaffold(
      appBar: AppBar(
          title: Text(isArtisan
              ? tr('B2B opportunities')
              : tr('Requirement'))),
      body: _matching
          ? const AiProgress(steps: AiProgress.match, title: 'Cluster Order Pooling')
          : FutureBuilder<Requirement>(
              future: _future,
              builder: (context, snap) {
                if (snap.connectionState == ConnectionState.waiting) {
                  return const LoadingView();
                }
                if (snap.hasError) {
                  return ErrorView(snap.error!);
                }
                final r = snap.data!;
                return ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Text(r.title,
                        style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: 6),
                    Text('${r.buyerName} · ${r.buyerType}',
                        style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: 16),
                    SectionCard(
                      title: tr('Requirement'),
                      child: Column(
                        children: [
                          KeyValueRow(tr('Quantity'), '${r.quantity}',
                              strong: true),
                          KeyValueRow(tr('Craft'), r.craftName ?? '—'),
                          KeyValueRow(tr('Price band'),
                              '₹${r.priceMin.round()} – ₹${r.priceMax.round()}'),
                          if (r.daysLeft != null)
                            KeyValueRow(tr('Deadline'), '${r.daysLeft} days'),
                          const KeyValueRow('Min fill', '100%'),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    if (r.notes.isNotEmpty)
                      SectionCard(
                        title: tr('Notes'),
                        child: Text(r.notes,
                            style: Theme.of(context).textTheme.bodyLarge),
                      ),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppTheme.amberBg,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.info_rounded, color: AppTheme.ochre),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              isArtisan
                                  ? 'This order is larger than one artisan can '
                                      'fulfil alone. It will be pooled across '
                                      'your cluster — see how it would be split, '
                                      'including your share.'
                                  : 'No single artisan can fulfil ${r.quantity} '
                                      'units. We will pool a cluster and split '
                                      'the order and payment fairly.',
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Text(_error!,
                          style: const TextStyle(color: AppTheme.danger)),
                    ],
                    const SizedBox(height: 18),
                    ElevatedButton.icon(
                      onPressed: _findCluster,
                      icon: Icon(isArtisan
                          ? Icons.visibility_rounded
                          : Icons.groups_rounded),
                      label: Text(isArtisan
                          ? 'Preview cluster allocation'
                          : tr('Find artisan cluster')),
                    ),
                    if (isArtisan) ...[
                      const SizedBox(height: 8),
                      Text(
                        'The buyer runs the final matching. This preview shows '
                        'the optimiser output and your Shapley-fair payment '
                        'share.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                );
              },
            ),
    );
  }
}
