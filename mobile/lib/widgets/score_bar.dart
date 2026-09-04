import 'package:flutter/material.dart';

import '../core/theme.dart';

Color scoreColor(num v) {
  if (v >= 80) return AppTheme.leaf;
  if (v >= 50) return AppTheme.ochre;
  return AppTheme.danger;
}

/// Labelled 0–100 progress bar used across F1 / F3 / F4 (spec §8, §23).
class ScoreBar extends StatelessWidget {
  const ScoreBar({
    required this.label,
    required this.value,
    this.max = 100,
    this.showValue = true,
    this.color,
    super.key,
  });
  final String label;
  final num value;
  final num max;
  final bool showValue;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final pct = (value / max).clamp(0.0, 1.0).toDouble();
    final c = color ?? scoreColor(value / max * 100);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(label,
                    style: const TextStyle(
                        fontWeight: FontWeight.w600, color: AppTheme.ink)),
              ),
              if (showValue)
                Text('${value.round()}',
                    style: TextStyle(fontWeight: FontWeight.w800, color: c)),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: pct),
              duration: const Duration(milliseconds: 700),
              curve: Curves.easeOutCubic,
              builder: (_, v, __) => LinearProgressIndicator(
                value: v,
                minHeight: 10,
                backgroundColor: AppTheme.sand,
                valueColor: AlwaysStoppedAnimation(c),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Big circular readiness / confidence dial.
class ScoreDial extends StatelessWidget {
  const ScoreDial({
    required this.value,
    this.max = 100,
    this.caption,
    this.size = 150,
    super.key,
  });
  final num value;
  final num max;
  final String? caption;
  final double size;

  @override
  Widget build(BuildContext context) {
    final pct = (value / max).clamp(0.0, 1.0).toDouble();
    final c = scoreColor(value / max * 100);
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: size,
            height: size,
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: pct),
              duration: const Duration(milliseconds: 900),
              curve: Curves.easeOutCubic,
              builder: (_, v, __) => CircularProgressIndicator(
                value: v,
                strokeWidth: 12,
                backgroundColor: AppTheme.sand,
                valueColor: AlwaysStoppedAnimation(c),
                strokeCap: StrokeCap.round,
              ),
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('${value.round()}',
                  style: TextStyle(
                      fontSize: size * 0.28,
                      fontWeight: FontWeight.w900,
                      color: c)),
              Text(caption ?? '/ ${max.round()}',
                  style: const TextStyle(
                      color: AppTheme.inkSoft, fontWeight: FontWeight.w600)),
            ],
          ),
        ],
      ),
    );
  }
}
