import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

/// "AI System Insights" — judge-facing technical screen (spec §35, §45).
class InsightsScreen extends StatefulWidget {
  const InsightsScreen({super.key});

  @override
  State<InsightsScreen> createState() => _InsightsScreenState();
}

class _InsightsScreenState extends State<InsightsScreen> {
  late Future<_InsightsData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_InsightsData> _load() async {
    final app = context.read<AppState>();
    final feats = await app.api.features();
    final summary = await app.api.aiRunsSummary();
    final runs = await app.api.aiRuns();
    final f7 = await app.api.f7Explain('handwoven cotton dupatta');
    return _InsightsData(feats, summary, runs, f7);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI System Insights')),
      body: RefreshIndicator(
        onRefresh: () async => setState(() {
          _future = _load();
        }),
        child: FutureBuilder<_InsightsData>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView();
            }
            if (snap.hasError) {
              return ErrorView(snap.error!,
                  onRetry: () => setState(() {
                        _future = _load();
                      }));
            }
            final d = snap.data!;
            final summary = asMap(d.summary['summary']);
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  'This screen is for the technical judging round. It shows the '
                  'model, mode and latency behind every AI call.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 14),
                for (final f in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7'])
                  _FeatureCard(
                    code: f,
                    info: asMap(d.features[f]),
                    stats: asMap(summary[f]),
                  ),
                const SizedBox(height: 12),
                _F7Table(f7: d.f7),
                const SizedBox(height: 12),
                SectionCard(
                  title: 'Recent AI runs (${d.runs.length})',
                  child: Column(
                    children: [
                      for (final r in d.runs.take(20))
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 5),
                          child: Row(
                            children: [
                              SizedBox(
                                  width: 34,
                                  child: Text(r.feature,
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w900))),
                              ModeBadge(r.mode),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(r.model,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style:
                                        Theme.of(context).textTheme.bodySmall),
                              ),
                              Text('${r.latencyMs.toStringAsFixed(0)}ms',
                                  style: Theme.of(context).textTheme.bodySmall),
                            ],
                          ),
                        ),
                    ],
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

class _InsightsData {
  _InsightsData(this.features, this.summary, this.runs, this.f7);
  final J features;
  final J summary;
  final List<AiRun> runs;
  final J f7;
}

class _FeatureCard extends StatelessWidget {
  const _FeatureCard({required this.code, required this.info, required this.stats});
  final String code;
  final J info;
  final J stats;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppTheme.indigo,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(code,
                    style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 12)),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(asStr(info['name']),
                    style: const TextStyle(fontWeight: FontWeight.w800)),
              ),
              ModeBadge(asStr(info['mode'], 'REAL')),
            ],
          ),
          const SizedBox(height: 6),
          Text(asStr(info['engine']),
              style: Theme.of(context).textTheme.bodySmall),
          if (stats.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              'runs: ${asInt(stats['count'])} · '
              'avg ${asDouble(stats['avg_latency_ms']).toStringAsFixed(0)}ms · '
              'modes ${asMap(stats['modes']).keys.join(', ')}',
              style: const TextStyle(fontSize: 11.5, color: AppTheme.inkSoft),
            ),
          ],
        ],
      ),
    );
  }
}

class _F7Table extends StatelessWidget {
  const _F7Table({required this.f7});
  final J f7;

  @override
  Widget build(BuildContext context) {
    final rows = asMapList(f7['rows']);
    final w = asMap(f7['weights']);
    return SectionCard(
      title: 'F7 ranking breakdown',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'query "${f7['query']}" · α=${w['alpha_relevance']} β=${w['beta_new_seller']} '
            'γ=${w['gamma_region']} δ=${w['delta_exposure']}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columnSpacing: 16,
              headingRowHeight: 34,
              dataRowMinHeight: 30,
              dataRowMaxHeight: 40,
              columns: const [
                DataColumn(label: Text('#')),
                DataColumn(label: Text('Artisan')),
                DataColumn(label: Text('rel')),
                DataColumn(label: Text('new')),
                DataColumn(label: Text('reg')),
                DataColumn(label: Text('exp')),
                DataColumn(label: Text('score')),
              ],
              rows: [
                for (final r in rows.take(10))
                  DataRow(cells: [
                    DataCell(Text('${r['rank']}')),
                    DataCell(Text('${r['artisan']}',
                        style: const TextStyle(fontSize: 11))),
                    DataCell(Text('${r['relevance']}')),
                    DataCell(Text('${r['new_seller_boost']}')),
                    DataCell(Text('${r['underserved_region_boost']}')),
                    DataCell(Text('${r['exposure_penalty']}')),
                    DataCell(Text('${r['final_score']}',
                        style: const TextStyle(fontWeight: FontWeight.w800))),
                  ]),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Text('exposure gap: ${asMap(f7['exposure_gap_metric'])['gap']}',
              style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
