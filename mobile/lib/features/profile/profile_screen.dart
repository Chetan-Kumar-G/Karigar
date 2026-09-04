import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/app_config.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../providers/product_flow.dart';
import '../../widgets/common.dart';
import '../trust/trust_widgets.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final s = app.session;
    final p = s?.profile ?? {};

    return Scaffold(
      appBar: AppBar(
        title: Text(tr('Profile')),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_rounded),
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 30,
                backgroundColor: AppTheme.indigo,
                child: Text(
                  (s?.name ?? '?').characters.first.toUpperCase(),
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.w800),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(s?.name ?? 'Guest',
                        style: Theme.of(context).textTheme.titleLarge),
                    Text(app.isArtisan ? tr('Artisan') : tr('Buyer'),
                        style: Theme.of(context).textTheme.bodyMedium),
                    if (s != null) ...[
                      const SizedBox(height: 6),
                      _TrustTag(subjectId: s.id, isBusiness: !app.isArtisan),
                    ],
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          if (app.isArtisan)
            SectionCard(
              title: tr('Your workshop'),
              child: Column(
                children: [
                  KeyValueRow(tr('Region'), '${p['region'] ?? '—'}'),
                  KeyValueRow(tr('State'), '${p['state'] ?? '—'}'),
                  KeyValueRow(tr('Cluster'), '${p['cluster'] ?? '—'}'),
                  KeyValueRow(tr('Monthly capacity'),
                      '${p['monthly_capacity_units'] ?? '—'}'),
                  KeyValueRow('KYC', '${p['kyc_status'] ?? 'pending'}'),
                  KeyValueRow('Verified sales',
                      '${p['verified_sales_count'] ?? 0}'),
                ],
              ),
            ),
          if (app.isArtisan) ...[
            const SizedBox(height: 12),
            SectionCard(
              title: tr('Tools'),
              child: Column(
                children: [
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.verified_user_rounded),
                    title: Text(tr('My verification')),
                    subtitle: const Text('Proofs & Verified Artisan badge'),
                    onTap: () => context.push('/verification'),
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.inventory_2_rounded),
                    title: Text(tr('Inventory')),
                    onTap: () => context.push('/inventory'),
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.notifications_none_rounded),
                    title: Text(tr('Notifications')),
                    onTap: () => context.push('/notifications'),
                  ),
                ],
              ),
            ),
          ],
          if (!app.isArtisan && s != null) ...[
            const SizedBox(height: 12),
            SectionCard(
              title: tr('Trust'),
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.verified_rounded),
                title: Text(tr('My Verified Business card')),
                onTap: () => context.push('/trust/business/${s.id}'),
              ),
            ),
          ],
          const SizedBox(height: 12),
          SectionCard(
            title: tr('Demo controls'),
            child: Column(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.swap_horiz_rounded),
                  title: Text(app.isArtisan
                      ? tr('Switch to Buyer mode')
                      : tr('Switch to Artisan mode')),
                  onTap: () async {
                    await app.switchRole(app.isArtisan ? 'buyer' : 'artisan');
                    if (context.mounted) {
                      context.go(app.isArtisan ? '/home' : '/buyer');
                    }
                  },
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.slideshow_rounded),
                  title: Text(tr('SIH Demo Mode')),
                  onTap: () => context.push('/demo'),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.fact_check_rounded),
                  title: Text(tr('Verification reviewer')),
                  onTap: () => context.push('/reviewer'),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.translate_rounded),
                  title: Text(tr('Language')),
                  onTap: () => context.push('/language'),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.insights_rounded),
                  title: Text(tr('AI System Insights (judge view)')),
                  onTap: () => context.push('/insights'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: tr('About'),
            child: Column(
              children: [
                const KeyValueRow('App', '${AppConfig.appName} · prototype'),
                KeyValueRow('Backend', AppConfig.apiBaseUrl),
                const KeyValueRow('Problem', 'SIH PS 26090'),
              ],
            ),
          ),
          const SizedBox(height: 18),
          OutlinedButton.icon(
            onPressed: () async {
              context.read<ProductFlow>().reset();
              await app.signOut();
              if (context.mounted) context.go('/login');
            },
            icon: const Icon(Icons.logout_rounded),
            label: Text(tr('Sign out')),
          ),
        ],
      ),
    );
  }
}

/// Small verification-status pill shown under the profile name.
class _TrustTag extends StatefulWidget {
  const _TrustTag({required this.subjectId, required this.isBusiness});
  final String subjectId;
  final bool isBusiness;

  @override
  State<_TrustTag> createState() => _TrustTagState();
}

class _TrustTagState extends State<_TrustTag> {
  VerifiedCard? _card;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = context.read<AppState>().api;
      final c = widget.isBusiness
          ? await api.businessTrustCard(widget.subjectId)
          : await api.artisanTrustCard(widget.subjectId);
      if (mounted) setState(() => _card = c);
    } catch (_) {/* keep silent on the profile header */}
  }

  @override
  Widget build(BuildContext context) {
    final c = _card;
    if (c == null) return const SizedBox.shrink();
    return InkWell(
      onTap: () => context.push(widget.isBusiness
          ? '/trust/business/${widget.subjectId}'
          : '/trust/artisan/${widget.subjectId}'),
      child: VerifiedTag(c.status),
    );
  }
}
