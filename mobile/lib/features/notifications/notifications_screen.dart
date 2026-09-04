import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

/// Notification feed — derived from the same structured signals as the Copilot
/// (F5/F4/F1/F6), plus B2B opportunities. Nothing here is a fake push.
class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<List<CopilotCard>> _future;

  @override
  void initState() {
    super.initState();
    final app = context.read<AppState>();
    _future = app.api.insights(app.session!.id);
  }

  IconData _icon(String type) => switch (type) {
        'pricing' => Icons.payments_rounded,
        'listing' => Icons.photo_camera_rounded,
        'buyer' => Icons.handshake_rounded,
        _ => Icons.trending_up_rounded,
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: RefreshIndicator(
        onRefresh: () async {
          final app = context.read<AppState>();
          setState(() {
            _future = app.api.insights(app.session!.id);
          });
        },
        child: FutureBuilder<List<CopilotCard>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView();
            }
            if (snap.hasError) {
              return ErrorView(snap.error!);
            }
            final cards = snap.data!;
            if (cards.isEmpty) {
              return const EmptyView(
                icon: Icons.notifications_none_rounded,
                title: 'You are all caught up',
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 100),
              itemCount: cards.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final c = cards[i];
                final fg = Accent.fg[c.colour] ?? AppTheme.indigo;
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: (Accent.bg[c.colour] ?? AppTheme.skyBg),
                    child: Icon(_icon(c.type), color: fg, size: 20),
                  ),
                  title: Text(c.title,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text(c.observation,
                      maxLines: 2, overflow: TextOverflow.ellipsis),
                  trailing: Text(c.feature,
                      style: TextStyle(
                          fontWeight: FontWeight.w800, color: fg, fontSize: 12)),
                  onTap: () {
                    if (c.productId != null) {
                      context.push('/product/${c.productId}');
                    } else if (c.requirementId != null) {
                      context.push('/buyer/requirement/${c.requirementId}');
                    } else {
                      context.push('/copilot');
                    }
                  },
                );
              },
            );
          },
        ),
      ),
    );
  }
}
