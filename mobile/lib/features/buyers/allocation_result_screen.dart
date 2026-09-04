import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';
import '../trust/trust_widgets.dart';

/// F6 result — AI Cluster Allocation + Fair Payment Distribution (spec §15, §31).
class AllocationResultScreen extends StatefulWidget {
  const AllocationResultScreen({required this.orderId, super.key});
  final String orderId;

  @override
  State<AllocationResultScreen> createState() => _AllocationResultScreenState();
}

class _AllocationResultScreenState extends State<AllocationResultScreen> {
  late Future<OrderResult> _future;
  bool _confirming = false;

  @override
  void initState() {
    super.initState();
    _future = _loadOrder();
  }

  Future<OrderResult> _loadOrder() async {
    final orders = await context.read<AppState>().api.orders();
    final match = orders.firstWhere((o) => asStr(o['order_id']) == widget.orderId,
        orElse: () => <String, dynamic>{});
    return OrderResult(match);
  }

  Future<void> _confirm() async {
    setState(() => _confirming = true);
    try {
      final res =
          await context.read<AppState>().api.allocateOrder(widget.orderId);
      if (!mounted) return;
      setState(() {
        _future = Future.value(res);
      });
      showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          icon: const Icon(Icons.verified_rounded,
              color: AppTheme.leaf, size: 44),
          title: const Text('Allocation confirmed'),
          content: Text(
              '${res.totalAllocated} / ${res.totalQuantity} units committed '
              'across ${res.allocations.length} artisans.'),
          actions: [
            FilledButton(
              onPressed: () {
                Navigator.pop(context);
                context.go('/buyer');
              },
              child: const Text('Done'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(appSnack('$e', danger: true));
      }
    } finally {
      if (mounted) setState(() => _confirming = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('AI Cluster Allocation'))),
      body: FutureBuilder<OrderResult>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const LoadingView();
          }
          if (snap.hasError || (snap.data?.id.isEmpty ?? true)) {
            return ErrorView(snap.error ?? 'Order not found',
                onRetry: () => setState(() {
                      _future = _loadOrder();
                    }));
          }
          final o = snap.data!;
          final meta = o.optimizationMeta;
          final greedy = asMap(meta['baseline_greedy']);
          final trace = asMap(meta['eligibility_trace']);
          final allocs = o.allocations;
          final isBuyer = !context.read<AppState>().isArtisan;
          final maxUnits = allocs.isEmpty
              ? 1
              : allocs.map((a) => a.units).reduce((a, b) => a > b ? a : b);

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              _FulfilledBanner(o: o),
              const SizedBox(height: 14),
              if (trace.isNotEmpty) ...[
                _EligibilityCard(trace: trace),
                const SizedBox(height: 12),
              ],
              Text(tr('Allocation across the cluster'),
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 10),
              for (final a in allocs)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _AllocCard(
                    a: a,
                    maxUnits: maxUnits,
                    isMe: a.artisanId ==
                        context.read<AppState>().session?.id,
                    onReport: isBuyer
                        ? () => context.push('/report/${a.artisanId}', extra: {
                              'artisanName': a.artisanName,
                              'orderId': o.id,
                            })
                        : null,
                  ),
                ),
              const SizedBox(height: 6),
              SectionCard(
                title: 'Optimization',
                trailing: const ModeBadge('REAL'),
                child: Column(
                  children: [
                    KeyValueRow('Fulfilment', '${o.fulfillmentPct}%',
                        strong: true),
                    KeyValueRow('Capacity utilisation',
                        '${meta['capacity_utilization_pct'] ?? '—'}%'),
                    KeyValueRow('Total cost', '₹${_money(o.totalCost)}'),
                    KeyValueRow('Buyer payment', '₹${_money(o.totalBuyerPayment)}'),
                    KeyValueRow('Objective value',
                        o.objectiveValue?.toStringAsFixed(0) ?? '—'),
                    KeyValueRow(
                        'Solver',
                        o.solver == 'greedy_fallback'
                            ? 'Greedy fallback (CP-SAT unavailable)'
                            : o.solver.toUpperCase()),
                    KeyValueRow('Solve time',
                        '${o.solveTimeMs?.toStringAsFixed(1) ?? '—'} ms'),
                    if (asStr(meta['shapley_method']).isNotEmpty)
                      KeyValueRow('Shapley method',
                          asStr(meta['shapley_method']).replaceAll('_', ' ')),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              _PaymentDistribution(allocs: allocs, total: o.totalBuyerPayment),
              const SizedBox(height: 12),
              if (greedy.isNotEmpty)
                SectionCard(
                  title: 'vs. naive greedy baseline',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${greedy['strategy']}',
                          style: Theme.of(context).textTheme.bodyMedium),
                      const SizedBox(height: 8),
                      KeyValueRow('Greedy fill',
                          '${greedy['fulfillment_pct']}% (${greedy['filled_units']} units)'),
                      KeyValueRow('Greedy cost',
                          '₹${_money(asInt(greedy['total_cost_inr']))}'),
                      KeyValueRow('Greedy artisans',
                          '${greedy['artisans_used']}'),
                    ],
                  ),
                ),
              const SizedBox(height: 8),
              if (asStr(meta['shapley_note']).isNotEmpty)
                Text(asStr(meta['shapley_note']),
                    style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 16),
              if (context.read<AppState>().isArtisan)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                      color: AppTheme.skyBg,
                      borderRadius: BorderRadius.circular(12)),
                  child: const Row(children: [
                    Icon(Icons.visibility_rounded, color: AppTheme.indigo),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                          'Preview only — the buyer confirms the final allocation.',
                          style: TextStyle(fontWeight: FontWeight.w600)),
                    ),
                  ]),
                )
              else if (o.status == 'proposed' || o.status == 'partially_allocated')
                ElevatedButton.icon(
                  onPressed: _confirming ? null : _confirm,
                  icon: _confirming
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.2, color: Colors.white))
                      : const Icon(Icons.check_rounded),
                  label: Text(tr('Confirm allocation')),
                )
              else
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                      color: AppTheme.leafBg,
                      borderRadius: BorderRadius.circular(12)),
                  child: Row(children: [
                    const Icon(Icons.check_circle_rounded, color: AppTheme.leaf),
                    const SizedBox(width: 8),
                    Text('Order ${o.status.replaceAll('_', ' ')}',
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                  ]),
                ),
              if (isBuyer && o.id.isNotEmpty) ...[
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: () =>
                      context.push('/order-commitment/${o.id}'),
                  icon: const Icon(Icons.verified_user_rounded),
                  label: Text(tr('Order protection & payments')),
                ),
              ],
            ],
          );
        },
      ),
    );
  }

  static String _money(int v) {
    final s = v.toString();
    final b = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0 && !(s.length - i == s.length)) {
        b.write(',');
      }
      b.write(s[i]);
    }
    return b.toString();
  }
}

class _FulfilledBanner extends StatelessWidget {
  const _FulfilledBanner({required this.o});
  final OrderResult o;

  @override
  Widget build(BuildContext context) {
    final done = o.fulfillmentPct >= 100;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: done
              ? [AppTheme.leaf, const Color(0xFF2F6B49)]
              : [AppTheme.ochre, AppTheme.terracotta],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(done ? 'FULLY ALLOCATED' : 'PARTIALLY ALLOCATED',
              style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.9),
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                  fontSize: 12)),
          const SizedBox(height: 8),
          Text('${o.totalAllocated} / ${o.totalQuantity}',
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 34,
                  fontWeight: FontWeight.w900)),
          Text('units fulfilled across ${o.allocations.length} artisans',
              style: TextStyle(color: Colors.white.withValues(alpha: 0.9))),
        ],
      ),
    );
  }
}

class _AllocCard extends StatelessWidget {
  const _AllocCard({
    required this.a,
    required this.maxUnits,
    this.isMe = false,
    this.onReport,
  });
  final Allocation a;
  final int maxUnits;
  final bool isMe;
  final VoidCallback? onReport;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: isMe
          ? BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppTheme.terracotta, width: 2))
          : null,
      child: SectionCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: isMe ? AppTheme.terracotta : AppTheme.sand,
                  child: Text(
                      a.artisanName.isNotEmpty ? a.artisanName[0] : '?',
                      style: TextStyle(
                          fontWeight: FontWeight.w800,
                          color: isMe ? Colors.white : AppTheme.ink)),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(isMe ? '${a.artisanName} (you)' : a.artisanName,
                          style: const TextStyle(fontWeight: FontWeight.w800)),
                      const SizedBox(height: 3),
                      VerifiedTag(a.verificationStatus),
                    ],
                  ),
                ),
                Text('${a.units} units',
                    style: const TextStyle(
                        fontWeight: FontWeight.w900,
                        color: AppTheme.terracotta,
                        fontSize: 16)),
              ],
            ),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: maxUnits == 0 ? 0 : a.units / maxUnits,
                minHeight: 8,
                backgroundColor: AppTheme.sand,
                valueColor: const AlwaysStoppedAnimation(AppTheme.indigo),
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                InfoPill('Quality ${(a.quality * 100).round()}%',
                    color: AppTheme.leaf),
                InfoPill(
                    'Reliability ${(a.reliabilityPct ?? a.reliability * 100).round()}%',
                    color: AppTheme.indigo),
                InfoPill('Capacity ${a.capacity}', color: AppTheme.inkSoft),
              ],
            ),
            if (a.allocationRationale.isNotEmpty) ...[
              const SizedBox(height: 8),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info_outline_rounded,
                      size: 15, color: AppTheme.inkSoft),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(a.allocationRationale,
                        style: Theme.of(context).textTheme.bodySmall),
                  ),
                ],
              ),
            ],
            if (onReport != null) ...[
              const SizedBox(height: 6),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: onReport,
                  icon: const Icon(Icons.flag_outlined, size: 16),
                  label: const Text('Report an issue'),
                  style: TextButton.styleFrom(
                      foregroundColor: AppTheme.danger,
                      padding: EdgeInsets.zero,
                      minimumSize: const Size(0, 32)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _EligibilityCard extends StatelessWidget {
  const _EligibilityCard({required this.trace});
  final Map<String, dynamic> trace;

  @override
  Widget build(BuildContext context) {
    int n(String k) => (trace[k] as num?)?.toInt() ?? 0;
    final steps = [
      ('Registered artisans', n('pool')),
      ('Craft compatible', n('craft_compatible')),
      ('Capacity available', n('capacity_available')),
      ('Verification OK (not suspended)', n('verification_ok')),
      ('Within price band', n('within_price_band')),
      ('Eligible for the optimiser', n('eligible')),
    ];
    return SectionCard(
      title: tr('Who was eligible'),
      trailing: const ModeBadge('REAL'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final s in steps)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(
                children: [
                  const Icon(Icons.filter_alt_rounded,
                      size: 15, color: AppTheme.inkSoft),
                  const SizedBox(width: 8),
                  Expanded(child: Text(s.$1)),
                  Text('${s.$2}',
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                ],
              ),
            ),
          const SizedBox(height: 6),
          Text('${trace['note'] ?? ''}',
              style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _PaymentDistribution extends StatelessWidget {
  const _PaymentDistribution({required this.allocs, required this.total});
  final List<Allocation> allocs;
  final int total;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      title: tr('Fair payment distribution'),
      trailing: const ModeBadge('REAL'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Shapley value = average marginal contribution across every '
            'sub-coalition. Compare with a plain by-units split — they differ '
            'whenever quality, reliability or capacity are unequal.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          for (final a in allocs) ...[
            Text(a.artisanName,
                style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            _DualBar(
              shapley: a.payment.toDouble(),
              proportional: a.proportional.toDouble(),
              max: (total == 0 ? 1 : total).toDouble(),
            ),
            if (a.paymentRationale.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(a.paymentRationale,
                  style: Theme.of(context).textTheme.bodySmall),
            ],
            const SizedBox(height: 10),
          ],
          const SizedBox(height: 4),
          const Row(children: [
            _LegendDot(color: AppTheme.terracotta, label: 'Shapley payment'),
            SizedBox(width: 16),
            _LegendDot(color: AppTheme.inkSoft, label: 'By-units split'),
          ]),
        ],
      ),
    );
  }
}

class _DualBar extends StatelessWidget {
  const _DualBar({
    required this.shapley,
    required this.proportional,
    required this.max,
  });
  final double shapley;
  final double proportional;
  final double max;

  @override
  Widget build(BuildContext context) {
    Widget bar(double v, Color c, String prefix) => Row(
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(
                  value: (v / max).clamp(0, 1),
                  minHeight: 14,
                  backgroundColor: AppTheme.sand,
                  valueColor: AlwaysStoppedAnimation(c),
                ),
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 78,
              child: Text('$prefix₹${v.round()}',
                  textAlign: TextAlign.right,
                  style: TextStyle(
                      fontWeight: FontWeight.w800, color: c, fontSize: 12)),
            ),
          ],
        );
    return Column(
      children: [
        bar(shapley, AppTheme.terracotta, ''),
        const SizedBox(height: 4),
        bar(proportional, AppTheme.inkSoft, ''),
      ],
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color, required this.label});
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 11.5)),
      ],
    );
  }
}
