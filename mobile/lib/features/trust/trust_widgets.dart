import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

/// Colour for a trust tone. Deliberately simple — green / blue / amber / red.
Color trustToneColor(String tone) => switch (tone) {
      'green' => AppTheme.leaf,
      'amber' => AppTheme.ochre,
      'red' => AppTheme.danger,
      _ => AppTheme.indigo,
    };

IconData trustToneIcon(String key) => switch (key) {
      'verified' || 'business' => Icons.verified_rounded,
      'identity' => Icons.badge_rounded,
      'craft' => Icons.brush_rounded,
      'product' => Icons.inventory_2_rounded,
      'contact' => Icons.call_rounded,
      'gi_verified' => Icons.workspace_premium_rounded,
      'gi_pending' || 'gi_reported' || 'pending' => Icons.hourglass_bottom_rounded,
      'under_review' => Icons.gpp_maybe_rounded,
      'suspended' => Icons.gpp_bad_rounded,
      _ => Icons.check_circle_rounded,
    };

String giLabel(String s) => switch (s) {
      'government_verified' => 'Government verified',
      'pending_verification' => 'Pending verification',
      'artisan_reported' => 'Artisan reported',
      _ => 'Not registered',
    };

String statusLabel(String s) => switch (s) {
      'VERIFIED' => 'Verified',
      'REINSTATED' => 'Reinstated (verified)',
      'UNDER_REVIEW' => 'Under review',
      'SUSPENDED' => 'Suspended',
      'REJECTED' => 'Not verified',
      _ => 'Verification pending',
    };

/// A single "what was verified" chip — icon + short text (low-literacy friendly).
class TrustBadgeChip extends StatelessWidget {
  const TrustBadgeChip(this.badge, {this.compact = false, super.key});
  final TrustBadge badge;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final c = trustToneColor(badge.tone);
    return Container(
      padding: EdgeInsets.symmetric(
          horizontal: compact ? 8 : 11, vertical: compact ? 4 : 7),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: c.withValues(alpha: 0.30)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(trustToneIcon(badge.key), size: compact ? 13 : 15, color: c),
          const SizedBox(width: 5),
          Text(badge.label,
              style: TextStyle(
                  color: c,
                  fontWeight: FontWeight.w700,
                  fontSize: compact ? 11 : 12.5)),
        ],
      ),
    );
  }
}

/// Small pill used next to a name/title anywhere in the app.
class VerifiedTag extends StatelessWidget {
  const VerifiedTag(this.status, {this.label, super.key});
  final String status;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final (tone, icon) = switch (status) {
      'VERIFIED' || 'REINSTATED' => ('green', Icons.verified_rounded),
      'UNDER_REVIEW' => ('amber', Icons.gpp_maybe_rounded),
      'SUSPENDED' => ('red', Icons.gpp_bad_rounded),
      'REJECTED' => ('red', Icons.block_rounded),
      _ => ('amber', Icons.hourglass_bottom_rounded),
    };
    final c = trustToneColor(tone);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: c.withValues(alpha: 0.35)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 12, color: c),
        const SizedBox(width: 4),
        Text(label ?? statusLabel(status),
            style: TextStyle(
                fontSize: 10.5, fontWeight: FontWeight.w800, color: c)),
      ]),
    );
  }
}

/// The full "Verified Artisan / Verified Business" card (spec §1, §13).
class VerifiedCardView extends StatelessWidget {
  const VerifiedCardView(this.card, {this.onPassport, super.key});
  final VerifiedCard card;
  final VoidCallback? onPassport;

  @override
  Widget build(BuildContext context) {
    final verified = card.status == 'VERIFIED' || card.status == 'REINSTATED';
    final headline = card.isBusiness ? 'VERIFIED BUSINESS' : 'VERIFIED ARTISAN';
    final tone = verified
        ? AppTheme.leaf
        : card.status == 'SUSPENDED' || card.status == 'REJECTED'
            ? AppTheme.danger
            : AppTheme.ochre;

    return SectionCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 24,
                backgroundColor: AppTheme.indigo,
                child: Text(
                  card.name.isNotEmpty ? card.name[0].toUpperCase() : '?',
                  style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 20),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Icon(
                          verified
                              ? Icons.verified_rounded
                              : Icons.gpp_maybe_rounded,
                          color: tone,
                          size: 18),
                      const SizedBox(width: 6),
                      Text(verified ? headline : statusLabel(card.status),
                          style: TextStyle(
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.6,
                              fontSize: 12.5,
                              color: tone)),
                    ]),
                    const SizedBox(height: 2),
                    Text(card.name,
                        style: Theme.of(context).textTheme.titleMedium),
                  ],
                ),
              ),
              if (card.isDemo) const InfoPill('Demo Data', color: AppTheme.ochre),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            [
              if (!card.isBusiness) card.craft,
              if (!card.isBusiness && card.region != null)
                '${card.region}${card.state != null ? ', ${card.state}' : ''}',
              if (card.isBusiness) card.businessType,
            ].whereType<String>().join(' · '),
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [for (final b in card.badges) TrustBadgeChip(b)],
          ),
          const SizedBox(height: 14),
          _StatRow(card: card),
          if (!card.isBusiness) ...[
            const SizedBox(height: 8),
            KeyValueRow('GI / certification', giLabel(card.giStatus)),
            KeyValueRow('Joined', card.joinedDate ?? '—'),
          ] else ...[
            const SizedBox(height: 8),
            KeyValueRow('Order history', '${card.orderHistoryCount} orders'),
            KeyValueRow('B2B eligibility',
                card.b2bEligible ? 'Eligible' : 'Not eligible yet'),
          ],
          if (onPassport != null && card.passportProductId != null) ...[
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: onPassport,
              icon: const Icon(Icons.menu_book_rounded),
              label: const Text('Open Craft Passport'),
            ),
          ],
          const SizedBox(height: 10),
          Text(card.disclaimer,
              style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _StatRow extends StatelessWidget {
  const _StatRow({required this.card});
  final VerifiedCard card;

  @override
  Widget build(BuildContext context) {
    final tiles = card.isBusiness
        ? [
            ('Orders', '${card.orderHistoryCount}'),
            ('Completed', '${card.ordersCompleted}'),
            ('Reliability', '${card.reliabilityScore.round()}/100'),
          ]
        : [
            ('Completed orders', '${card.completedOrders}'),
            ('On-time', '${card.onTimePct.round()}%'),
            ('Reliability', '${card.reliabilityScore.round()}/100'),
          ];
    return Row(
      children: [
        for (final t in tiles)
          Expanded(
            child: Column(
              children: [
                Text(t.$2,
                    style: const TextStyle(
                        fontWeight: FontWeight.w900, fontSize: 18)),
                const SizedBox(height: 2),
                Text(t.$1,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
      ],
    );
  }
}

/// Explainable reliability breakdown — every term shown (spec §8).
class ReliabilityBreakdownView extends StatelessWidget {
  const ReliabilityBreakdownView(this.breakdown, {super.key});
  final Map<String, dynamic> breakdown;

  @override
  Widget build(BuildContext context) {
    final terms = (breakdown['terms'] as Map?)?.cast<String, dynamic>() ?? {};
    final signals =
        (breakdown['signals'] as Map?)?.cast<String, dynamic>() ?? {};
    final score = (breakdown['score'] as num?)?.toDouble() ?? 0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Text('${score.round()}',
              style: const TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.w900,
                  color: AppTheme.leaf)),
          const Text(' / 100',
              style: TextStyle(fontWeight: FontWeight.w700)),
        ]),
        const SizedBox(height: 8),
        for (final e in terms.entries)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(
              children: [
                Expanded(
                    child: Text(
                        e.key.replaceAll('_', ' '),
                        style: Theme.of(context).textTheme.bodyMedium)),
                Text(
                  '${(e.value as num) >= 0 ? '+' : ''}${(e.value as num).toStringAsFixed(1)}',
                  style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: (e.value as num) >= 0
                          ? AppTheme.leaf
                          : AppTheme.danger),
                ),
              ],
            ),
          ),
        const Divider(height: 18),
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: [
            InfoPill('${signals['completed_orders'] ?? 0} completed',
                icon: Icons.check_circle_rounded, color: AppTheme.leaf),
            InfoPill('${signals['on_time_pct'] ?? 0}% on-time',
                icon: Icons.schedule_rounded, color: AppTheme.indigo),
            InfoPill('${signals['cancellation_rate_pct'] ?? 0}% cancels',
                icon: Icons.cancel_schedule_send_rounded,
                color: AppTheme.ochre),
            InfoPill('${signals['quality_complaints'] ?? 0} quality issues',
                icon: Icons.report_gmailerrorred_rounded,
                color: AppTheme.danger),
          ],
        ),
        const SizedBox(height: 8),
        Text('${breakdown['note'] ?? ''}',
            style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

/// Compact link-row that opens the public Verified Artisan card.
class ViewVerifiedArtisanButton extends StatelessWidget {
  const ViewVerifiedArtisanButton({required this.artisanId, super.key});
  final String artisanId;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: () => context.push('/trust/artisan/$artisanId'),
      icon: const Icon(Icons.verified_user_rounded),
      label: const Text('View Verified Artisan card'),
    );
  }
}
