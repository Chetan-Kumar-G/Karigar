import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../models/models.dart';

/// One Business-Copilot recommendation card (spec §17). Every card is generated
/// from structured F1/F4/F5/F6 output — the badge shows which feature.
class CopilotCardWidget extends StatelessWidget {
  const CopilotCardWidget({required this.card, this.onAction, super.key});
  final CopilotCard card;
  final VoidCallback? onAction;

  IconData get _icon => switch (card.type) {
        'pricing' => Icons.payments_rounded,
        'listing' => Icons.photo_camera_rounded,
        'buyer' => Icons.handshake_rounded,
        _ => Icons.trending_up_rounded,
      };

  @override
  Widget build(BuildContext context) {
    final fg = Accent.fg[card.colour] ?? AppTheme.indigo;
    final bg = Accent.bg[card.colour] ?? AppTheme.skyBg;

    void defaultAction() {
      if (card.productId != null) {
        context.push('/product/${card.productId}');
      } else if (card.requirementId != null) {
        context.push('/buyer/requirement/${card.requirementId}');
      }
    }

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: bg,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(17)),
            ),
            child: Row(
              children: [
                Icon(_icon, color: fg, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(card.title,
                      style: TextStyle(
                          fontWeight: FontWeight.w800, color: fg)),
                ),
                Text(card.feature,
                    style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: fg.withValues(alpha: 0.8))),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(card.observation,
                    style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.cream,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.arrow_forward_rounded,
                          size: 16, color: AppTheme.terracotta),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(card.action,
                            style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                color: AppTheme.ink)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        card.signals.join(' · '),
                        style: const TextStyle(
                            fontSize: 11.5, color: AppTheme.inkSoft),
                      ),
                    ),
                    TextButton(
                      onPressed: onAction ?? defaultAction,
                      child: const Text('Open'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
