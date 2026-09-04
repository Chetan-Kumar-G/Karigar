import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

/// B2B order protection — commitment stages, simulated milestone payments and
/// stage-aware cancellation (spec §10, §11, §12). Clearly labelled *Simulated*.
class OrderCommitmentScreen extends StatefulWidget {
  const OrderCommitmentScreen({required this.orderId, super.key});
  final String orderId;

  @override
  State<OrderCommitmentScreen> createState() => _OrderCommitmentScreenState();
}

class _OrderCommitmentScreenState extends State<OrderCommitmentScreen> {
  late Future<OrderCommitment> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.orderCommitment(widget.orderId);
  }

  void _set(OrderCommitment c) => setState(() {
        _future = Future.value(c);
      });

  Future<void> _run(Future<OrderCommitment> Function() op) async {
    setState(() => _busy = true);
    try {
      _set(await op());
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(appSnack('$e', danger: true));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancel() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Cancel this order?'),
        content: const Text(
            'You will see the cancellation stage and any artisan cost that is '
            'protected. This is a simulated flow.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Keep order')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Cancel order')),
        ],
      ),
    );
    if (ok == true) {
      await _run(() =>
          context.read<AppState>().api.commitmentCancel(widget.orderId));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('Order protection & payments'))),
      body: FutureBuilder<OrderCommitment>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const LoadingView();
          }
          if (snap.hasError) {
            return ErrorView(snap.error!,
                onRetry: () => setState(() {
                      _future = context
                          .read<AppState>()
                          .api
                          .orderCommitment(widget.orderId);
                    }));
          }
          final c = snap.data!;
          final cancelled = c.status.startsWith('CANCELLED');
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 40),
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.amberBg,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(children: [
                  const Icon(Icons.science_rounded, color: AppTheme.ochre, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(tr('Prototype Payment Flow / Simulated'),
                        style: const TextStyle(
                            fontWeight: FontWeight.w800, fontSize: 12.5)),
                  ),
                ]),
              ),
              const SizedBox(height: 14),
              SectionCard(
                title: tr('Commitment stage'),
                child: _StageTracker(flow: c.flow, current: c.status),
              ),
              const SizedBox(height: 12),
              SectionCard(
                title: tr('Milestone payments (simulated)'),
                child: Column(
                  children: [
                    for (final m in c.milestones)
                      _MilestoneRow(
                        label: '${m['label']}',
                        pct: (m['pct'] as num?)?.toInt() ?? 0,
                        amount: (m['amount_inr'] as num?)?.toInt() ?? 0,
                        status: '${m['status']}',
                      ),
                    const Divider(height: 18),
                    KeyValueRow(tr('Released so far'), '₹${c.paidInr}',
                        strong: true),
                    KeyValueRow(tr('Order value'), '₹${c.totalBuyerPaymentInr}'),
                  ],
                ),
              ),
              if (c.cancellationStage != null) ...[
                const SizedBox(height: 12),
                SectionCard(
                  title: tr('Cancellation'),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      KeyValueRow('Cancellation stage', c.cancellationStage!),
                      KeyValueRow('Artisan committed cost',
                          '₹${c.artisanCommittedCostInr}'),
                      KeyValueRow('Advance retained / due',
                          '₹${c.advanceRetainedInr}'),
                      const SizedBox(height: 6),
                      Text(c.consequence ?? c.trackingNote ?? '',
                          style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 16),
              if (!cancelled) ...[
                ElevatedButton.icon(
                  onPressed: _busy
                      ? null
                      : () => _run(() => context
                          .read<AppState>()
                          .api
                          .commitmentAdvancePayment(widget.orderId)),
                  icon: const Icon(Icons.payments_rounded),
                  label: Text(tr('Pay advance (20%)')),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _busy
                      ? null
                      : () => _run(() => context
                          .read<AppState>()
                          .api
                          .commitmentNextStage(widget.orderId)),
                  icon: const Icon(Icons.skip_next_rounded),
                  label: Text(tr('Advance to next stage')),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.danger,
                    side: const BorderSide(color: AppTheme.danger, width: 1.4),
                  ),
                  onPressed: _busy ? null : _cancel,
                  icon: const Icon(Icons.cancel_rounded),
                  label: Text(tr('Cancel order')),
                ),
              ],
              const SizedBox(height: 12),
              Text(c.disclaimer,
                  style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 6),
              Text(
                'Not a legally enforceable escrow. Production can connect this '
                'to a real payment provider.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          );
        },
      ),
    );
  }
}

class _StageTracker extends StatelessWidget {
  const _StageTracker({required this.flow, required this.current});
  final List<String> flow;
  final String current;

  @override
  Widget build(BuildContext context) {
    final idx = flow.indexOf(current);
    return Column(
      children: [
        for (var i = 0; i < flow.length; i++)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(
              children: [
                Icon(
                  i <= idx && idx >= 0
                      ? Icons.check_circle_rounded
                      : Icons.radio_button_unchecked_rounded,
                  size: 18,
                  color: i <= idx && idx >= 0
                      ? AppTheme.leaf
                      : AppTheme.inkSoft,
                ),
                const SizedBox(width: 10),
                Text(
                  flow[i].replaceAll('_', ' ').toLowerCase(),
                  style: TextStyle(
                    fontWeight:
                        i == idx ? FontWeight.w900 : FontWeight.w600,
                    color: i == idx ? AppTheme.ink : AppTheme.inkSoft,
                  ),
                ),
              ],
            ),
          ),
        if (idx < 0)
          Align(
            alignment: Alignment.centerLeft,
            child: Text('Current: ${current.replaceAll('_', ' ').toLowerCase()}',
                style: const TextStyle(
                    fontWeight: FontWeight.w900, color: AppTheme.danger)),
          ),
      ],
    );
  }
}

class _MilestoneRow extends StatelessWidget {
  const _MilestoneRow({
    required this.label,
    required this.pct,
    required this.amount,
    required this.status,
  });
  final String label;
  final int pct;
  final int amount;
  final String status;

  @override
  Widget build(BuildContext context) {
    final paid = status == 'paid';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(paid ? Icons.check_circle_rounded : Icons.schedule_rounded,
              size: 18, color: paid ? AppTheme.leaf : AppTheme.inkSoft),
          const SizedBox(width: 10),
          Expanded(
            child: Text('$label  ·  $pct%',
                style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
          Text('₹$amount',
              style: TextStyle(
                  fontWeight: FontWeight.w800,
                  color: paid ? AppTheme.leaf : AppTheme.inkSoft)),
        ],
      ),
    );
  }
}
