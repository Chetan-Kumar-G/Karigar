import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';
import '../copilot/copilot_card_widget.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<Dashboard> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Dashboard> _load() {
    final app = context.read<AppState>();
    return app.api.dashboard(app.session!.id);
  }

  Future<void> _refresh() async {
    setState(() {
      _future = _load();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('Your business today')),
        actions: [
          IconButton(
            tooltip: 'Notifications',
            icon: const Icon(Icons.notifications_none_rounded),
            onPressed: () => context.push('/notifications'),
          ),
          IconButton(
            tooltip: 'AI System Insights (judge view)',
            icon: const Icon(Icons.insights_rounded),
            onPressed: () => context.push('/insights'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<Dashboard>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView(label: 'Loading your dashboard…');
            }
            if (snap.hasError) {
              return ListView(children: [
                const SizedBox(height: 120),
                ErrorView(snap.error!, onRetry: _refresh),
              ]);
            }
            final d = snap.data!;
            final s = d.summary;
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
              children: [
                Text('${d.greeting}, ${d.artisanName.split(' ').first} 👋',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 4),
                Text(
                  d.attention.isEmpty
                      ? tr('Everything looks good today.')
                      : '${d.attention.length} · ${tr('Needs your attention')}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),
                const _VerificationStrip(),
                _StatGrid(summary: s),
                const SizedBox(height: 20),
                if (d.attention.isNotEmpty) ...[
                  Text(tr('Needs your attention'),
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 10),
                  for (final c in d.attention)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: CopilotCardWidget(card: c),
                    ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: () => context.push('/copilot'),
                    icon: const Icon(Icons.auto_awesome_rounded),
                    label: Text(tr('Open Business Copilot')),
                  ),
                  const SizedBox(height: 20),
                ],
                Text(tr('Quick actions'),
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 10),
                _QuickActions(),
              ],
            );
          },
        ),
      ),
    );
  }
}

/// Actionable verification status strip (spec §16 — short, plain, useful).
class _VerificationStrip extends StatefulWidget {
  const _VerificationStrip();

  @override
  State<_VerificationStrip> createState() => _VerificationStripState();
}

class _VerificationStripState extends State<_VerificationStrip> {
  VerifiedCard? _card;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final app = context.read<AppState>();
      final c = await app.api.artisanTrustCard(app.session!.id);
      if (mounted) setState(() => _card = c);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final c = _card;
    if (c == null) return const SizedBox.shrink();
    final verified = c.status == 'VERIFIED' || c.status == 'REINSTATED';
    final color = verified
        ? AppTheme.leaf
        : c.status == 'SUSPENDED'
            ? AppTheme.danger
            : AppTheme.ochre;
    final msg = verified
        ? 'Verified Artisan · reliability ${c.reliabilityScore.round()}/100'
        : c.status == 'UNDER_REVIEW'
            ? 'Account under review — nothing to do right now'
            : c.status == 'SUSPENDED'
                ? 'Verified status paused — open to see why'
                : 'Add one more proof to become a Verified Artisan';
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => context.push('/verification'),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: color.withValues(alpha: 0.30)),
          ),
          child: Row(
            children: [
              Icon(verified ? Icons.verified_rounded : Icons.gpp_maybe_rounded,
                  color: color),
              const SizedBox(width: 10),
              Expanded(
                  child: Text(msg,
                      style: const TextStyle(fontWeight: FontWeight.w700))),
              const Icon(Icons.chevron_right_rounded, color: AppTheme.inkSoft),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatGrid extends StatelessWidget {
  const _StatGrid({required this.summary});
  final J summary;

  @override
  Widget build(BuildContext context) {
    final tiles = [
      (
        tr('Products listed'),
        '${asInt(summary['products_listed'])}',
        Icons.grid_view_rounded,
        AppTheme.indigo
      ),
      (
        tr('B2B orders'),
        '${asInt(summary['b2b_orders'])}',
        Icons.local_shipping_rounded,
        AppTheme.leaf
      ),
      (
        tr('B2B revenue'),
        '₹${_k(asInt(summary['b2b_revenue_inr']))}',
        Icons.payments_rounded,
        AppTheme.terracotta
      ),
      (
        tr('Pending actions'),
        '${asInt(summary['pending_actions'])}',
        Icons.notifications_active_rounded,
        AppTheme.ochre
      ),
    ];
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.35,
      children: [
        for (final t in tiles)
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppTheme.line),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(t.$3, color: t.$4, size: 22),
                Text(t.$2,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 22, fontWeight: FontWeight.w900)),
                Text(t.$1,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
      ],
    );
  }

  static String _k(int v) =>
      v >= 100000 ? '${(v / 100000).toStringAsFixed(1)}L' : '$v';
}

class _QuickActions extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final actions = [
      (tr('Add product'), Icons.add_a_photo_rounded, () => context.push('/create')),
      (tr('Market'), Icons.storefront_rounded, () => context.push('/market')),
      (tr('Inventory'), Icons.inventory_2_rounded, () => context.push('/inventory')),
      (tr('Market demand'), Icons.trending_up_rounded, () => context.push('/demand')),
      (tr('Find buyers'), Icons.handshake_rounded, () => context.go('/orders')),
    ];
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        for (final a in actions)
          SizedBox(
            width: (MediaQuery.of(context).size.width - 44) / 2,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                alignment: Alignment.centerLeft,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
              ),
              onPressed: a.$3,
              icon: Icon(a.$2),
              label: Text(a.$1, overflow: TextOverflow.ellipsis),
            ),
          ),
      ],
    );
  }
}
