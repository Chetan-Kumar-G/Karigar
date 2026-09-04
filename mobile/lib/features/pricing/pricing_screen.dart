import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/product_flow.dart';
import '../../widgets/ai_progress.dart';
import '../../widgets/common.dart';
import '../product_studio/create_product_screen.dart';

/// F4 — Fair Cost-Aware Pricing Assistant (spec §12, §30).
class PricingScreen extends StatefulWidget {
  const PricingScreen({required this.productId, this.inFlow = true, super.key});
  final String productId;
  final bool inFlow;

  @override
  State<PricingScreen> createState() => _PricingScreenState();
}

class _PricingScreenState extends State<PricingScreen> {
  final _material = TextEditingController(text: '180');
  final _hours = TextEditingController(text: '6');
  final _rate = TextEditingController(text: '60');
  final _packaging = TextEditingController(text: '40');
  final _logistics = TextEditingController(text: '30');
  bool _showTechnical = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final flow = context.read<ProductFlow>();
      if (flow.product?.id != widget.productId) {
        flow.loadExisting(widget.productId);
      }
    });
  }

  @override
  void dispose() {
    for (final c in [_material, _hours, _rate, _packaging, _logistics]) {
      c.dispose();
    }
    super.dispose();
  }

  double _v(TextEditingController c) => double.tryParse(c.text.trim()) ?? 0;

  Future<void> _calc() async {
    await context.read<ProductFlow>().runPrice(
          materialCost: _v(_material),
          labourHours: _v(_hours),
          labourRate: _v(_rate),
          packaging: _v(_packaging),
          logistics: _v(_logistics),
        );
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<ProductFlow>();
    final r = flow.price;

    return Scaffold(
      appBar: AppBar(title: Text(tr('Fair price'))),
      body: flow.busy
          ? const AiProgress(steps: AiProgress.price, title: 'Pricing Assistant')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (widget.inFlow) ...[
                    const StepDots(active: 3),
                    const SizedBox(height: 16),
                  ],
                  SectionCard(
                    title: tr('Your costs'),
                    child: Column(
                      children: [
                        _CostField(
                            label: 'Material cost',
                            controller: _material,
                            prefix: '₹'),
                        Row(children: [
                          Expanded(
                              child: _CostField(
                                  label: 'Labour hours',
                                  controller: _hours,
                                  prefix: '')),
                          const SizedBox(width: 12),
                          Expanded(
                              child: _CostField(
                                  label: 'Rate / hour',
                                  controller: _rate,
                                  prefix: '₹')),
                        ]),
                        Row(children: [
                          Expanded(
                              child: _CostField(
                                  label: 'Packaging',
                                  controller: _packaging,
                                  prefix: '₹')),
                          const SizedBox(width: 12),
                          Expanded(
                              child: _CostField(
                                  label: 'Logistics',
                                  controller: _logistics,
                                  prefix: '₹')),
                        ]),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  ElevatedButton.icon(
                    onPressed: _calc,
                    icon: const Icon(Icons.calculate_rounded),
                    label: Text(r == null ? 'Calculate fair price' : 'Recalculate'),
                  ),
                  if (flow.error != null) ...[
                    const SizedBox(height: 12),
                    Text(flow.error!,
                        style: const TextStyle(color: AppTheme.danger)),
                  ],
                  if (r != null) ...[
                    const SizedBox(height: 18),
                    _PriceResultView(
                      r: r,
                      showTechnical: _showTechnical,
                      onToggleTechnical: () =>
                          setState(() => _showTechnical = !_showTechnical),
                    ),
                    const SizedBox(height: 18),
                    if (widget.inFlow)
                      ElevatedButton.icon(
                        onPressed: () => context
                            .pushReplacement('/preview/${widget.productId}'),
                        icon: const Icon(Icons.publish_rounded),
                        label: Text(tr('Review & publish')),
                      ),
                  ],
                ],
              ),
            ),
    );
  }
}

class _CostField extends StatelessWidget {
  const _CostField(
      {required this.label, required this.controller, required this.prefix});
  final String label;
  final TextEditingController controller;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: TextField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(
          labelText: label,
          prefixText: prefix.isEmpty ? null : '$prefix ',
        ),
      ),
    );
  }
}

class _PriceResultView extends StatelessWidget {
  const _PriceResultView({
    required this.r,
    required this.showTechnical,
    required this.onToggleTechnical,
  });
  final PriceResult r;
  final bool showTechnical;
  final VoidCallback onToggleTechnical;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionCard(
          title: tr('Recommended price'),
          trailing: ModeBadge(r.meta['mode']?.toString() ?? 'REAL'),
          child: Column(
            children: [
              Text('₹${r.recommended}',
                  style: const TextStyle(
                      fontSize: 40,
                      fontWeight: FontWeight.w900,
                      color: AppTheme.terracotta)),
              const SizedBox(height: 12),
              _Band(
                  label: 'Sustainable floor',
                  value: '₹${r.floor}',
                  color: AppTheme.leaf,
                  strong: r.floorBinding),
              _Band(
                  label: 'Competitive range',
                  value: '₹${r.range.isNotEmpty ? r.range[0] : r.floor} – ₹${r.range.length > 1 ? r.range[1] : r.recommended}',
                  color: AppTheme.indigo),
              _Band(
                  label: 'Premium opportunity',
                  value: '₹${r.premium}',
                  color: AppTheme.ochre),
              if (r.floorBinding) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.leafBg,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Row(children: [
                    Icon(Icons.shield_rounded, color: AppTheme.leaf, size: 18),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'The market price was below your making cost. We raised '
                        'it to the sustainable floor.',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                  ]),
                ),
              ],
            ],
          ),
        ),
        if (r.pricingPipeline.isNotEmpty) ...[
          const SizedBox(height: 12),
          SectionCard(
            title: 'How we got to ₹${r.recommended}',
            trailing: const ModeBadge('REAL'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final s in r.pricingPipeline)
                  _PipelineStep(
                    label: '${s['label']}',
                    value: s['value_inr'] == null ? '—' : '₹${s['value_inr']}',
                    detail: '${s['detail'] ?? ''}',
                    isFloor: s['stage'] == 'cost_floor',
                    isFinal: s['stage'] == 'final' || s['stage'] == 'floor_clamp',
                  ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(Icons.shield_moon_rounded,
                        size: 16, color: AppTheme.leaf),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'The cost floor is a hard constraint — the final price '
                        'can never drop below it.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
        if (r.trainingDataNote.isNotEmpty) ...[
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.science_outlined,
                  size: 15, color: AppTheme.inkSoft),
              const SizedBox(width: 6),
              Expanded(
                child: Text(r.trainingDataNote,
                    style: Theme.of(context).textTheme.bodySmall),
              ),
            ],
          ),
        ],
        const SizedBox(height: 12),
        SectionCard(
          title: tr('Why this price?'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(r.whyPlain, style: Theme.of(context).textTheme.bodyLarge),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final f in (r.explanation['top_positive_factors']
                          as List? ??
                      []))
                    InfoPill('+ $f', color: AppTheme.leaf),
                  for (final f in (r.explanation['top_negative_factors']
                          as List? ??
                      []))
                    InfoPill('– $f', color: AppTheme.terracotta),
                ],
              ),
              const SizedBox(height: 8),
              TextButton.icon(
                onPressed: onToggleTechnical,
                icon: Icon(showTechnical
                    ? Icons.expand_less_rounded
                    : Icons.expand_more_rounded),
                label: Text(showTechnical
                    ? 'Hide technical detail'
                    : 'Technical detail (for judges)'),
              ),
              if (showTechnical)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.cream,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Model: ${r.meta['model'] ?? '—'}',
                          style: Theme.of(context).textTheme.bodySmall),
                      Text('Latency: ${r.meta['latency_ms'] ?? '—'} ms',
                          style: Theme.of(context).textTheme.bodySmall),
                      const SizedBox(height: 6),
                      const Text('Feature contributions (tree SHAP):',
                          style: TextStyle(
                              fontWeight: FontWeight.w700, fontSize: 12)),
                      for (final e
                          in (r.explanation['shap'] as Map? ?? {}).entries)
                        Text('  ${e.key}: ${e.value}',
                            style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _PipelineStep extends StatelessWidget {
  const _PipelineStep({
    required this.label,
    required this.value,
    required this.detail,
    this.isFloor = false,
    this.isFinal = false,
  });
  final String label;
  final String value;
  final String detail;
  final bool isFloor;
  final bool isFinal;

  @override
  Widget build(BuildContext context) {
    final accent = isFloor
        ? AppTheme.leaf
        : isFinal
            ? AppTheme.terracotta
            : AppTheme.inkSoft;
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 3),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: (isFloor || isFinal) ? 0.10 : 0.04),
        borderRadius: BorderRadius.circular(8),
        border: isFloor ? Border.all(color: AppTheme.leaf, width: 1.3) : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(isFloor ? Icons.horizontal_rule_rounded : Icons.chevron_right_rounded,
                  size: 16, color: accent),
              const SizedBox(width: 4),
              Expanded(
                child: Text(label,
                    style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: isFloor ? AppTheme.leaf : AppTheme.ink)),
              ),
              Text(value,
                  style: TextStyle(fontWeight: FontWeight.w900, color: accent)),
            ],
          ),
          if (detail.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: 20, top: 2),
              child: Text(detail,
                  style: Theme.of(context).textTheme.bodySmall),
            ),
        ],
      ),
    );
  }
}

class _Band extends StatelessWidget {
  const _Band({
    required this.label,
    required this.value,
    required this.color,
    this.strong = false,
  });
  final String label;
  final String value;
  final Color color;
  final bool strong;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: strong ? 0.16 : 0.08),
        borderRadius: BorderRadius.circular(10),
        border: strong ? Border.all(color: color, width: 1.5) : null,
      ),
      child: Row(
        children: [
          Expanded(
              child: Text(label,
                  style: const TextStyle(fontWeight: FontWeight.w600))),
          Text(value,
              style: TextStyle(fontWeight: FontWeight.w900, color: color)),
        ],
      ),
    );
  }
}
