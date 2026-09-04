import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

import 'trust_widgets.dart';

/// Public Verified Artisan / Verified Business card (spec §1).
class TrustCardScreen extends StatefulWidget {
  const TrustCardScreen({
    required this.subjectId,
    this.isBusiness = false,
    super.key,
  });
  final String subjectId;
  final bool isBusiness;

  @override
  State<TrustCardScreen> createState() => _TrustCardScreenState();
}

class _TrustCardScreenState extends State<TrustCardScreen> {
  late Future<VerifiedCard> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<VerifiedCard> _load() {
    final api = context.read<AppState>().api;
    return widget.isBusiness
        ? api.businessTrustCard(widget.subjectId)
        : api.artisanTrustCard(widget.subjectId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
          title: Text(widget.isBusiness ? tr('Verified Business') : tr('Verified Artisan'))),
      body: FutureBuilder<VerifiedCard>(
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
          final card = snap.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              VerifiedCardView(
                card,
                onPassport: card.passportProductId == null
                    ? null
                    : () => context.push('/passport/${card.passportProductId}',
                        extra: {'inFlow': false}),
              ),
              const SizedBox(height: 12),
              if (!card.isBusiness && card.reliabilityBreakdown.isNotEmpty)
                SectionCard(
                  title: 'Reliability score — how it is calculated',
                  child: ReliabilityBreakdownView(card.reliabilityBreakdown),
                ),
              const SizedBox(height: 12),
              SectionCard(
                title: 'What this means',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _line(Icons.check_rounded,
                        'Each badge shows exactly what was checked.'),
                    _line(Icons.shield_moon_rounded,
                        'Private KYC documents are never shown here.'),
                    _line(Icons.smart_toy_outlined,
                        'AI helps collect evidence and flag risk. People make the final decision.'),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _line(IconData i, String t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(i, size: 18),
          const SizedBox(width: 10),
          Expanded(child: Text(t)),
        ]),
      );
}
