import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

import 'trust_widgets.dart';

/// Artisan-facing "My verification" — simple, icon-led, no jargon (spec §16).
class VerificationScreen extends StatefulWidget {
  const VerificationScreen({super.key});

  @override
  State<VerificationScreen> createState() => _VerificationScreenState();
}

class _VerificationScreenState extends State<VerificationScreen> {
  late Future<VerificationProfileM> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<VerificationProfileM> _load() {
    final app = context.read<AppState>();
    return app.api.trustProfile(app.session!.id);
  }

  void _reload() => setState(() {
        _future = _load();
      });

  Future<void> _submit(String kind, String axis, String label) async {
    final app = context.read<AppState>();
    setState(() => _busy = true);
    try {
      await app.api.submitEvidence(
        subjectId: app.session!.id,
        kind: kind,
        axis: axis,
        label: label,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          appSnack('Sent. A reviewer will check it soon.'));
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
      appBar: AppBar(title: Text(tr('My verification'))),
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
          final verified = p.status == 'VERIFIED' || p.status == 'REINSTATED';
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _StatusBanner(status: p.status, reason: p.suspensionReason),
              const SizedBox(height: 14),
              SectionCard(
                title: tr('What we have checked'),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [for (final b in p.badges) TrustBadgeChip(b)],
                ),
              ),
              const SizedBox(height: 12),
              SectionCard(
                title: tr('Your proofs'),
                child: Column(
                  children: [
                    for (final e in p.evidence)
                      _EvidenceRow(
                        label: '${e['label']}',
                        status: '${e['status']}',
                        note: e['note'] as String?,
                      ),
                    if (p.evidence.isEmpty)
                      Text('No proofs added yet.',
                          style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              SectionCard(
                title: tr('Add one more proof'),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'We ask for proof so buyers can trust your work. '
                      'Pick what you can share now.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 12),
                    _AddProofButton(
                      icon: Icons.badge_rounded,
                      label: 'My ID (Aadhaar / voter card)',
                      onTap: _busy
                          ? null
                          : () => _submit('gov_kyc', 'identity', 'Government ID'),
                    ),
                    _AddProofButton(
                      icon: Icons.photo_camera_rounded,
                      label: 'Photos of me making the craft',
                      onTap: _busy
                          ? null
                          : () => _submit(
                              'product_sample', 'craft', 'Craft work photos'),
                    ),
                    _AddProofButton(
                      icon: Icons.groups_rounded,
                      label: 'My craft cluster / society letter',
                      onTap: _busy
                          ? null
                          : () => _submit(
                              'cluster_record', 'craft', 'Cluster letter'),
                    ),
                    _AddProofButton(
                      icon: Icons.workspace_premium_rounded,
                      label: 'GI / award certificate (if I have one)',
                      onTap: _busy
                          ? null
                          : () =>
                              _submit('gi_document', 'gi', 'GI / award document'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: () =>
                    context.push('/trust/artisan/${p.subjectId}'),
                icon: const Icon(Icons.visibility_rounded),
                label: Text(tr('See my public card')),
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                    color: AppTheme.skyBg,
                    borderRadius: BorderRadius.circular(12)),
                child: const Row(children: [
                  Icon(Icons.info_rounded, color: AppTheme.indigo),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                        'A person from the platform checks every proof. '
                        'AI only helps — it does not decide.',
                        style: TextStyle(fontWeight: FontWeight.w600)),
                  ),
                ]),
              ),
              if (verified) const SizedBox(height: 8),
            ],
          );
        },
      ),
    );
  }
}

class _StatusBanner extends StatelessWidget {
  const _StatusBanner({required this.status, this.reason});
  final String status;
  final String? reason;

  @override
  Widget build(BuildContext context) {
    final verified = status == 'VERIFIED' || status == 'REINSTATED';
    final review = status == 'UNDER_REVIEW';
    final suspended = status == 'SUSPENDED' || status == 'REJECTED';
    final color = verified
        ? AppTheme.leaf
        : suspended
            ? AppTheme.danger
            : AppTheme.ochre;
    final msg = verified
        ? 'You are a Verified Artisan. Buyers can see your badges.'
        : review
            ? 'We are checking something on your account. Nothing to do right now.'
            : suspended
                ? (reason ?? 'Your verified status is paused while we review a report.')
                : 'Add your proofs below to become a Verified Artisan.';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: [
          Icon(
              verified
                  ? Icons.verified_rounded
                  : suspended
                      ? Icons.gpp_bad_rounded
                      : Icons.hourglass_bottom_rounded,
              color: color,
              size: 30),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(statusLabel(status),
                    style: TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 16,
                        color: color)),
                const SizedBox(height: 2),
                Text(msg, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _EvidenceRow extends StatelessWidget {
  const _EvidenceRow({required this.label, required this.status, this.note});
  final String label;
  final String status;
  final String? note;

  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (status) {
      'accepted' => (Icons.check_circle_rounded, AppTheme.leaf),
      'more_needed' => (Icons.error_rounded, AppTheme.ochre),
      'rejected' => (Icons.cancel_rounded, AppTheme.danger),
      _ => (Icons.hourglass_bottom_rounded, AppTheme.inkSoft),
    };
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                if (note != null && note!.isNotEmpty)
                  Text(note!, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
          Text(
            switch (status) {
              'accepted' => 'Done',
              'more_needed' => 'Need more',
              'rejected' => 'Not ok',
              _ => 'Checking',
            },
            style: TextStyle(fontWeight: FontWeight.w800, color: color, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _AddProofButton extends StatelessWidget {
  const _AddProofButton({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: OutlinedButton.icon(
        style: OutlinedButton.styleFrom(
          alignment: Alignment.centerLeft,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
        ),
        onPressed: onTap,
        icon: Icon(icon),
        label: Text(label, textAlign: TextAlign.left),
      ),
    );
  }
}
