import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';
import '../../widgets/score_bar.dart';
import '../product_studio/create_product_screen.dart';

/// F3 — Digital Craft Passport (spec §11). Heritage-focused, premium look.
class PassportScreen extends StatefulWidget {
  const PassportScreen({required this.productId, this.inFlow = true, super.key});
  final String productId;
  final bool inFlow;

  @override
  State<PassportScreen> createState() => _PassportScreenState();
}

class _PassportScreenState extends State<PassportScreen> {
  late Future<Passport> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.passport(widget.productId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('Digital Craft Passport'))),
      body: FutureBuilder<Passport>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const LoadingView(label: 'Building the passport…');
          }
          if (snap.hasError) {
            return ErrorView(snap.error!,
                onRetry: () => setState(() {
                      _future =
                          context.read<AppState>().api.passport(widget.productId);
                    }));
          }
          final p = snap.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (widget.inFlow) ...[
                const StepDots(active: 2),
                const SizedBox(height: 16),
              ],
              _Header(p: p),
              const SizedBox(height: 14),
              SectionCard(
                title: tr('Provenance'),
                child: Column(
                  children: [
                    KeyValueRow(tr('Craft'), p.craftName, strong: true),
                    KeyValueRow(tr('Technique'), p.techniqueName),
                    KeyValueRow(tr('Materials'),
                        p.materials.isEmpty ? '—' : p.materials.join(', ')),
                    KeyValueRow(tr('Region'), p.regionName),
                    KeyValueRow(tr('Artisan'), p.artisanName),
                    KeyValueRow(
                        'GI status', _giLabel(p.giStatus)),
                    if (p.odopCluster != null)
                      KeyValueRow('ODOP cluster', p.odopCluster!),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              _ConfidenceCard(p: p),
              const SizedBox(height: 12),
              if (p.storyEn.isNotEmpty)
                SectionCard(
                  title: tr('Craft story'),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(p.storyEn,
                          style: Theme.of(context).textTheme.bodyLarge),
                      if (p.heritageNote != null) ...[
                        const SizedBox(height: 10),
                        Text(p.heritageNote!,
                            style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ],
                  ),
                ),
              const SizedBox(height: 12),
              if (p.relatedCrafts.isNotEmpty)
                SectionCard(
                  title: tr('Related crafts'),
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final r in p.relatedCrafts)
                        InfoPill('${r['name']}', icon: Icons.account_tree_rounded),
                    ],
                  ),
                ),
              const SizedBox(height: 12),
              if (p.certifications.isNotEmpty)
                SectionCard(
                  title: tr('Verification records'),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final c in p.certifications)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            children: [
                              const Icon(Icons.workspace_premium_rounded,
                                  color: AppTheme.ochre, size: 18),
                              const SizedBox(width: 8),
                              Expanded(child: Text('${c['label']}')),
                            ],
                          ),
                        ),
                      const SizedBox(height: 6),
                      Text(
                        'These are sample verification records (demo data), not '
                        'real government GI certificates.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 20),
              if (widget.inFlow)
                ElevatedButton.icon(
                  onPressed: () =>
                      context.pushReplacement('/pricing/${widget.productId}'),
                  icon: const Icon(Icons.calculate_rounded),
                  label: Text(tr('Set a fair price')),
                ),
            ],
          );
        },
      ),
    );
  }

  static String _giLabel(String s) => switch (s) {
        'registered' => 'GI-registered craft',
        'pending' => 'GI application pending',
        _ => 'Not GI-registered',
      };
}

class _Header extends StatelessWidget {
  const _Header({required this.p});
  final Passport p;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.indigo, AppTheme.indigoLight],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.verified_rounded, color: Colors.white),
              const SizedBox(width: 8),
              Text('CRAFT PASSPORT',
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.2,
                      fontSize: 12)),
            ],
          ),
          const SizedBox(height: 10),
          Text(p.productTitle,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text('${p.craftName} · ${p.regionName}',
              style: TextStyle(color: Colors.white.withValues(alpha: 0.9))),
        ],
      ),
    );
  }
}

class _ConfidenceCard extends StatelessWidget {
  const _ConfidenceCard({required this.p});
  final Passport p;

  @override
  Widget build(BuildContext context) {
    final b = p.breakdown;
    final pct = (p.confidence * 100).round();
    return SectionCard(
      title: tr('Provenance confidence'),
      trailing: const ModeBadge('REAL'),
      child: Column(
        children: [
          Row(
            children: [
              ScoreDial(value: pct, size: 110),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _term('Government-sourced', b['gov_source_verified']),
                    _term('Voice grounding', b['grounding_guard_pass']),
                    _term('Photo consistency', b['visual_consistency_score']),
                    _term('Self-report consistency',
                        b['artisan_self_report_consistency']),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Photo check: ${p.visualStatus.replaceAll('_', ' ')}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Weighted 0.40·gov + 0.25·grounding + 0.20·photo + 0.15·self-report',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _term(String label, dynamic v) {
    final val = (v is num) ? v.toDouble() : 0.0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: ScoreBar(label: label, value: val * 100, showValue: false),
    );
  }
}
