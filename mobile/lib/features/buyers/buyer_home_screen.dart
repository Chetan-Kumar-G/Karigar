import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';
import '../marketplace/search_screen.dart';

class BuyerHomeScreen extends StatefulWidget {
  const BuyerHomeScreen({super.key});

  @override
  State<BuyerHomeScreen> createState() => _BuyerHomeScreenState();
}

class _BuyerHomeScreenState extends State<BuyerHomeScreen> {
  late Future<List<Requirement>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.requirements();
  }

  void _reload() => setState(() {
        _future = context.read<AppState>().api.requirements();
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('Buyer')),
        actions: [
          IconButton(
            tooltip: 'My Verified Business card',
            icon: const Icon(Icons.verified_user_rounded),
            onPressed: () {
              final id = context.read<AppState>().session?.id;
              if (id != null) context.push('/trust/business/$id');
            },
          ),
          IconButton(
            tooltip: tr('Language'),
            icon: const Icon(Icons.translate_rounded),
            onPressed: () => context.push('/language'),
          ),
          TextButton.icon(
            onPressed: () async {
              await context.read<AppState>().switchRole('artisan');
              if (context.mounted) context.go('/home');
            },
            icon: const Icon(Icons.swap_horiz_rounded),
            label: Text(tr('Switch to Artisan mode')),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<Requirement>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView();
            }
            if (snap.hasError) {
              return ErrorView(snap.error!, onRetry: _reload);
            }
            final reqs = snap.data!;
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                _ActionRow(),
                const SizedBox(height: 18),
                Text(tr('Your requirements'),
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 10),
                if (reqs.isEmpty)
                  EmptyView(
                    icon: Icons.assignment_rounded,
                    title: tr('No requirements yet'),
                    message:
                        'Post a bulk requirement and we will pool artisans to fill it.',
                  )
                else
                  for (final r in reqs)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _RequirementTile(
                        r: r,
                        onTap: () =>
                            context.push('/buyer/requirement/${r.id}'),
                      ),
                    ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Expanded(
        child: ElevatedButton.icon(
          onPressed: () => context.push('/buyer/new'),
          icon: const Icon(Icons.add_business_rounded),
          label: Text(tr('Post requirement')),
        ),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: OutlinedButton.icon(
          onPressed: () => Navigator.of(context).push(
            MaterialPageRoute<void>(
                builder: (_) => const SearchScreen(standalone: true)),
          ),
          icon: const Icon(Icons.search_rounded),
          label: Text(tr('Browse market')),
        ),
      ),
    ]);
  }
}

class _RequirementTile extends StatelessWidget {
  const _RequirementTile({required this.r, required this.onTap});
  final Requirement r;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(r.title,
                        style: const TextStyle(
                            fontWeight: FontWeight.w800, fontSize: 15)),
                  ),
                  if (r.isDemo)
                    const InfoPill('Demo', color: AppTheme.ochre),
                ],
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  InfoPill('${r.quantity} units',
                      icon: Icons.inventory_2_rounded),
                  InfoPill('₹${r.priceMin.round()}–₹${r.priceMax.round()}/unit',
                      icon: Icons.sell_rounded, color: AppTheme.leaf),
                  if (r.daysLeft != null)
                    InfoPill('${r.daysLeft} days left',
                        icon: Icons.schedule_rounded, color: AppTheme.ochre),
                ],
              ),
              const SizedBox(height: 8),
              Text('${r.buyerName} · status: ${r.status}',
                  style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}
