import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

import 'complaint_labels.dart';
import 'trust_widgets.dart';

/// Lightweight platform verification dashboard (spec §5). Demo/judge tool.
class ReviewerDashboardScreen extends StatefulWidget {
  const ReviewerDashboardScreen({super.key});

  @override
  State<ReviewerDashboardScreen> createState() =>
      _ReviewerDashboardScreenState();
}

class _ReviewerDashboardScreenState extends State<ReviewerDashboardScreen> {
  late Future<J> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.reviewerQueue();
  }

  void _reload() => setState(() {
        _future = context.read<AppState>().api.reviewerQueue();
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('Verification reviewer'))),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<J>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView();
            }
            if (snap.hasError) {
              return ErrorView(snap.error!, onRetry: _reload);
            }
            final data = snap.data!;
            final counts = asMap(data['counts']);
            final queue = asMapList(data['queue'])
                .map(ReviewerQueueItem.fromJson)
                .toList();
            final complaints = asMapList(data['complaints'])
                .map(ComplaintM.fromJson)
                .toList();
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                _CountsRow(counts: counts),
                const SizedBox(height: 18),
                Text(tr('Needs attention'),
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                for (final it in queue.where((q) => q.needsAttention))
                  _QueueTile(it: it, onDone: _reload),
                const SizedBox(height: 16),
                if (complaints.isNotEmpty) ...[
                  Text(tr('Complaints'),
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  for (final c in complaints) _ComplaintTile(c: c),
                  const SizedBox(height: 16),
                ],
                Text(tr('All profiles'),
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                for (final it in queue.where((q) => !q.needsAttention))
                  _QueueTile(it: it, onDone: _reload),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _CountsRow extends StatelessWidget {
  const _CountsRow({required this.counts});
  final J counts;

  @override
  Widget build(BuildContext context) {
    final tiles = [
      ('Pending', asInt(counts['pending']), AppTheme.ochre),
      ('Under review', asInt(counts['under_review']), AppTheme.indigo),
      ('Suspended', asInt(counts['suspended']), AppTheme.danger),
      ('Open complaints', asInt(counts['open_complaints']), AppTheme.terracotta),
    ];
    return Row(
      children: [
        for (final t in tiles)
          Expanded(
            child: Container(
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.line),
              ),
              child: Column(
                children: [
                  Text('${t.$2}',
                      style: TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 20,
                          color: t.$3)),
                  const SizedBox(height: 2),
                  Text(t.$1,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _QueueTile extends StatelessWidget {
  const _QueueTile({required this.it, required this.onDone});
  final ReviewerQueueItem it;
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () async {
          await context.push('/reviewer/${it.profileId}');
          onDone();
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Text(it.name,
                          style: const TextStyle(
                              fontWeight: FontWeight.w800, fontSize: 15)),
                      const SizedBox(width: 8),
                      if (it.isDemo)
                        const InfoPill('Demo', color: AppTheme.ochre),
                    ]),
                    const SizedBox(height: 6),
                    Wrap(spacing: 8, runSpacing: 6, children: [
                      VerifiedTag(it.status),
                      InfoPill(
                          it.subjectType == 'business' ? 'Business' : 'Artisan',
                          color: AppTheme.inkSoft),
                      InfoPill('Reliability ${it.reliabilityScore.round()}',
                          color: AppTheme.leaf),
                      if (it.openComplaints)
                        const InfoPill('Complaint', color: AppTheme.danger),
                    ]),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: AppTheme.inkSoft),
            ],
          ),
        ),
      ),
    );
  }
}

class _ComplaintTile extends StatelessWidget {
  const _ComplaintTile({required this.c});
  final ComplaintM c;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
              child: Text('${c.id} · ${complaintLabel(c.category)}',
                  style: const TextStyle(fontWeight: FontWeight.w800)),
            ),
            InfoPill(c.status,
                color: c.status == 'resolved'
                    ? AppTheme.leaf
                    : AppTheme.terracotta),
          ]),
          const SizedBox(height: 4),
          Text('Against ${c.artisanName} · reported by ${c.reportedBy}',
              style: Theme.of(context).textTheme.bodySmall),
          if (c.description.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(c.description,
                style: Theme.of(context).textTheme.bodyMedium),
          ],
          if (c.riskFlag != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.amberBg,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(children: [
                const Icon(Icons.smart_toy_outlined,
                    size: 16, color: AppTheme.ochre),
                const SizedBox(width: 8),
                Expanded(
                  child: Text('AI risk flag: ${c.riskFlag}',
                      style: const TextStyle(
                          fontWeight: FontWeight.w600, fontSize: 12.5)),
                ),
              ]),
            ),
          ],
        ],
      ),
    );
  }
}
