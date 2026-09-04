import 'dart:async';

import 'package:flutter/material.dart';

import '../core/theme.dart';

/// Stepped AI loading experience (spec §25) — cycles through phase captions
/// while a real backend call is in flight. It does NOT fake latency; the
/// captions simply advance on a timer and stop when the future completes.
class AiProgress extends StatefulWidget {
  const AiProgress({required this.steps, this.title, super.key});
  final List<String> steps;
  final String? title;

  static const analyze = [
    'Analyzing your product…',
    'Checking sharpness and lighting…',
    'Finding the product edges…',
    'Scoring the framing and background…',
    'Preparing the studio image…',
  ];
  static const catalog = [
    'Listening to your recording…',
    'Understanding your language…',
    'Extracting product details…',
    'Checking each claim against our craft records…',
    'Writing your catalog in English and Hindi…',
  ];
  static const price = [
    'Adding up your costs…',
    'Finding the sustainable floor…',
    'Comparing market signals…',
    'Calculating a fair price…',
  ];
  static const match = [
    'Finding compatible artisans…',
    'Checking capacity and craft match…',
    'Running the allocation optimizer…',
    'Splitting the payment fairly…',
  ];
  static const demand = [
    'Loading demand history…',
    'Running the forecast model…',
    'Turning the forecast into an action…',
  ];

  @override
  State<AiProgress> createState() => _AiProgressState();
}

class _AiProgressState extends State<AiProgress> {
  int _i = 0;
  Timer? _t;

  @override
  void initState() {
    super.initState();
    _t = Timer.periodic(const Duration(milliseconds: 1100), (_) {
      if (!mounted) return;
      setState(() => _i = (_i + 1).clamp(0, widget.steps.length - 1));
    });
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 54,
              height: 54,
              child: CircularProgressIndicator(strokeWidth: 3.5),
            ),
            const SizedBox(height: 22),
            if (widget.title != null) ...[
              Text(widget.title!,
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
            ],
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 350),
              child: Text(
                widget.steps[_i],
                key: ValueKey(_i),
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 15,
                    color: AppTheme.inkSoft,
                    fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(height: 18),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                widget.steps.length,
                (k) => Container(
                  width: 7,
                  height: 7,
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: k <= _i ? AppTheme.terracotta : AppTheme.sand,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
