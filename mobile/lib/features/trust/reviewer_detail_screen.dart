import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

import 'complaint_labels.dart';
import 'trust_widgets.dart';

/// Reviewer detail + actions: Approve / Request more / Reject / Under review /
/// Suspend / Reinstate (spec §5). Decisions are human — AI output is advisory.
class ReviewerDetailScreen extends StatefulWidget {
  const ReviewerDetailScreen({required this.profileId, super.key});
  final String profileId;

  @override
  State<ReviewerDetailScreen> createState() => _ReviewerDetailScreenState();
}

class _ReviewerDetailScreenState extends State<ReviewerDetailScreen> {
  late Future<VerificationProfileM> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<VerificationProfileM> _load() =>
      context.read<AppState>().api.reviewerDetail(widget.profileId);

  void _reload() => setState(() {
        _future = _load();
      });

  Future<void> _act(String action, {String? note}) async {
    setState(() => _busy = true);
    try {
      final res = await context
          .read<AppState>()
          .api
          .reviewerAction(widget.profileId, action, note: note);
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(appSnack(asStr(res['message'], 'Done')));
      _reload();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(appSnack('$e', danger: true));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('Review profile'))),
      body: FutureBuilder<VerificationProfileM>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const LoadingView();
          }
          if (snap.hasError) {
            return ErrorView(snap.error!, onRetry: _reload);
          }
          final p = snap.data!;
          final rv = p.reviewerView;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 40),
            children: [
              Row(children: [
                Expanded(
                  child: Text(p.name,
                      style: Theme.of(context).textTheme.headlineSmall),
                ),
                VerifiedTag(p.status),
              ]),
              const SizedBox(height: 4),
              Text(
                '${p.subjectType == 'business' ? 'Business' : 'Artisan'}'
                '${rv['craft'] != null ? ' · ${rv['craft']}' : ''}'
                '${rv['region'] != null ? ' · ${rv['region']}' : ''}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 14),
              SectionCard(
                title: 'Verification axes',
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [for (final b in p.badges) TrustBadgeChip(b)],
                ),
              ),
              const SizedBox(height: 12),
              SectionCard(
                title: 'Submitted evidence',
                child: Column(
                  children: [
                    for (final e in p.evidence)
                      KeyValueRow('${e['label']}',
                          '${e['status']}${asBool(e['ai_assisted']) ? '  · AI-assisted' : ''}'),
                    if (p.evidence.isEmpty) const Text('None submitted.'),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              if (rv['products'] is List &&
                  (rv['products'] as List).isNotEmpty)
                SectionCard(
                  title: 'Product evidence (F1 / F2 / F3)',
                  child: Column(
                    children: [
                      for (final pr in asMapList(rv['products']))
                        _ProductEvidence(pr: pr),
                    ],
                  ),
                ),
              const SizedBox(height: 12),
              if (p.reliabilityBreakdown.isNotEmpty)
                SectionCard(
                  title: 'Reliability score',
                  child: ReliabilityBreakdownView(p.reliabilityBreakdown),
                ),
              const SizedBox(height: 12),
              if (p.complaints.isNotEmpty)
                SectionCard(
                  title: 'Complaints',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final c in p.complaints.map(ComplaintM.fromJson))
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 5),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                  '${c.id} · ${complaintLabel(c.category)} · ${c.status}',
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w700)),
                              if (c.riskFlag != null)
                                Text('AI risk flag: ${c.riskFlag}',
                                    style:
                                        Theme.of(context).textTheme.bodySmall),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              const SizedBox(height: 12),
              if (p.timeline.isNotEmpty)
                SectionCard(
                  title: 'History',
                  child: Column(
                    children: [
                      for (final t in p.timeline.take(12))
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.circle, size: 7,
                                  color: AppTheme.inkSoft),
                              const SizedBox(width: 8),
                              Expanded(
                                  child: Text('${t['summary']}',
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodySmall)),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              const SizedBox(height: 16),
              Text(tr('Reviewer decision'),
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                'AI evidence and risk flags are advisory. You make the call.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 10),
              _ActionGrid(busy: _busy, onAct: _act),
            ],
          );
        },
      ),
    );
  }
}

class _ProductEvidence extends StatelessWidget {
  const _ProductEvidence({required this.pr});
  final J pr;

  @override
  Widget build(BuildContext context) {
    final claims = asMapList(pr['f2_claims']);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('${pr['title']}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Wrap(spacing: 8, runSpacing: 6, children: [
            InfoPill('F1 readiness ${pr['f1_readiness'] ?? '—'}',
                color: AppTheme.indigo),
            InfoPill('F2 visual: ${pr['f2_visual_consistency'] ?? '—'}',
                color: AppTheme.leaf),
            InfoPill(
                'F3 provenance ${((asDouble(pr['f3_provenance_confidence']) * 100).round())}%',
                color: AppTheme.ochre),
            InfoPill('GI: ${giLabel('${pr['f3_gi_status'] ?? 'not_registered'}')}',
                color: AppTheme.inkSoft),
          ]),
          const SizedBox(height: 6),
          for (final c in claims)
            Text(
              '• ${c['key']}: ${c['value']}  (${c['source']} · ${c['grounding_status']})',
              style: Theme.of(context).textTheme.bodySmall,
            ),
        ],
      ),
    );
  }
}

class _ActionGrid extends StatelessWidget {
  const _ActionGrid({required this.busy, required this.onAct});
  final bool busy;
  final void Function(String action, {String? note}) onAct;

  @override
  Widget build(BuildContext context) {
    final actions = <({String label, String action, Color color, IconData icon})>[
      (label: tr('Approve'), action: 'approve', color: AppTheme.leaf, icon: Icons.check_rounded),
      (label: tr('Request more evidence'), action: 'request_more_evidence', color: AppTheme.indigo, icon: Icons.more_horiz_rounded),
      (label: tr('Under review'), action: 'place_under_review', color: AppTheme.ochre, icon: Icons.gpp_maybe_rounded),
      (label: tr('Suspend'), action: 'suspend', color: AppTheme.danger, icon: Icons.pause_circle_rounded),
      (label: tr('Reinstate'), action: 'reinstate', color: AppTheme.leaf, icon: Icons.play_circle_rounded),
      (label: tr('Reject'), action: 'reject', color: AppTheme.danger, icon: Icons.block_rounded),
    ];
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final a in actions)
          SizedBox(
            width: (MediaQuery.of(context).size.width - 42) / 2,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: a.color,
                side: BorderSide(color: a.color, width: 1.4),
                padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
                alignment: Alignment.centerLeft,
              ),
              onPressed: busy
                  ? null
                  : () => onAct(a.action,
                      note: a.action == 'suspend'
                          ? 'Suspended pending investigation'
                          : null),
              icon: Icon(a.icon, size: 18),
              label: Text(a.label,
                  style: const TextStyle(fontSize: 13),
                  overflow: TextOverflow.ellipsis),
            ),
          ),
      ],
    );
  }
}
