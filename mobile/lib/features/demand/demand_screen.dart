import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/ai_progress.dart';
import '../../widgets/common.dart';

/// F5 — Demand & Market Opportunity Intelligence (spec §13).
class DemandScreen extends StatefulWidget {
  const DemandScreen({this.category, super.key});
  final String? category;

  @override
  State<DemandScreen> createState() => _DemandScreenState();
}

class _DemandScreenState extends State<DemandScreen> {
  String? _category;
  bool _loading = false;
  String? _error;
  DemandResult? _result;
  List<String> _categories = [];

  @override
  void initState() {
    super.initState();
    _category = widget.category;
    WidgetsBinding.instance.addPostFrameCallback((_) => _init());
  }

  Future<void> _init() async {
    final ref = context.read<AppState>().reference;
    _categories = (ref?.crafts ?? []).map((c) => c.name).toList();
    _category ??= _categories.isNotEmpty ? _categories.first : 'basket';
    await _run();
  }

  Future<void> _run() async {
    if (_category == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final app = context.read<AppState>();
      final res = await app.api.demandForecast(
        category: _category!,
        artisanId: app.isArtisan ? app.session!.id : null,
      );
      setState(() => _result = res);
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('Market demand'))),
      body: _loading && _result == null
          ? const AiProgress(steps: AiProgress.demand, title: 'Demand Intelligence')
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_categories.isNotEmpty)
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        for (final c in _categories)
                          Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ChoiceChip(
                              label: Text(c),
                              selected: _category == c,
                              onSelected: (_) {
                                setState(() => _category = c);
                                _run();
                              },
                            ),
                          ),
                      ],
                    ),
                  ),
                const SizedBox(height: 14),
                if (_error != null)
                  ErrorView(_error!, onRetry: _run)
                else if (_result != null)
                  _ForecastView(r: _result!),
              ],
            ),
    );
  }
}

class _ForecastView extends StatelessWidget {
  const _ForecastView({required this.r});
  final DemandResult r;

  @override
  Widget build(BuildContext context) {
    final action = r.action;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (r.isSimulated)
          Container(
            padding: const EdgeInsets.all(10),
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              color: AppTheme.amberBg,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(children: [
              const Icon(Icons.science_rounded, color: AppTheme.ochre, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(r.simulatedNote,
                    style: const TextStyle(
                        fontSize: 12, fontWeight: FontWeight.w600)),
              ),
            ]),
          ),
        SectionCard(
          title: tr('Predicted demand'),
          trailing: ModeBadge(r.meta['mode']?.toString() ?? 'SIMULATED_DATA'),
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: _Big(
                        label: 'Next ${r.windowDays} days',
                        value: '${r.predicted}',
                        sub: 'units'),
                  ),
                  Expanded(
                    child: _Big(
                      label: 'Trend',
                      value: '${r.trendPct >= 0 ? '↑' : '↓'} ${r.trendPct.abs()}%',
                      sub: 'vs previous period',
                      color: r.trendPct >= 0 ? AppTheme.leaf : AppTheme.danger,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Confidence interval: ${r.ci.isNotEmpty ? r.ci[0] : '—'} – '
                '${r.ci.length > 1 ? r.ci[1] : '—'} units · '
                'seasonal index ${r.seasonalIndex}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              if (r.curveP50.isNotEmpty)
                SizedBox(height: 160, child: _Chart(r: r)),
            ],
          ),
        ),
        const SizedBox(height: 12),
        SectionCard(
          title: tr('What to do'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.leafBg,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.checklist_rounded, color: AppTheme.leaf),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text('${action['text_en']}',
                          style: const TextStyle(
                              fontWeight: FontWeight.w800, fontSize: 15)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Text('${action['text_hi']}',
                  style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 8),
              Text(
                'Prediction and decision are separate pipeline stages: the model '
                'forecasts demand, then a translation layer scales it to your '
                'capacity and a deadline.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Big extends StatelessWidget {
  const _Big({
    required this.label,
    required this.value,
    required this.sub,
    this.color,
  });
  final String label;
  final String value;
  final String sub;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 2),
        Text(value,
            style: TextStyle(
                fontSize: 26,
                fontWeight: FontWeight.w900,
                color: color ?? AppTheme.ink)),
        Text(sub, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

class _Chart extends StatelessWidget {
  const _Chart({required this.r});
  final DemandResult r;

  @override
  Widget build(BuildContext context) {
    List<FlSpot> spots(List<double> ys) =>
        [for (var i = 0; i < ys.length; i++) FlSpot(i.toDouble(), ys[i])];
    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots(r.curveP90),
            isCurved: true,
            color: AppTheme.line,
            barWidth: 1,
            dotData: const FlDotData(show: false),
          ),
          LineChartBarData(
            spots: spots(r.curveP50),
            isCurved: true,
            color: AppTheme.terracotta,
            barWidth: 3,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: AppTheme.terracotta.withValues(alpha: 0.12),
            ),
          ),
          LineChartBarData(
            spots: spots(r.curveP10),
            isCurved: true,
            color: AppTheme.line,
            barWidth: 1,
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }
}
