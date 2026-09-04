import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  late Future<_OrdersData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_OrdersData> _load() async {
    final app = context.read<AppState>();
    if (app.isArtisan) {
      final mine = await app.api.artisanOrders(app.session!.id);
      final reqs = await app.api.requirements();
      return _OrdersData(artisanOrders: mine, requirements: reqs);
    }
    final orders = await app.api.orders();
    final reqs = await app.api.requirements();
    return _OrdersData(buyerOrders: orders, requirements: reqs);
  }

  void _reload() => setState(() {
        _future = _load();
      });

  @override
  Widget build(BuildContext context) {
    final isArtisan = context.read<AppState>().isArtisan;
    return Scaffold(
      appBar: AppBar(
          title: Text(isArtisan ? tr('Orders & buyers') : tr('Orders'))),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<_OrdersData>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView();
            }
            if (snap.hasError) {
              return ErrorView(snap.error!, onRetry: _reload);
            }
            final d = snap.data!;
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
              children: [
                if (isArtisan) ...[
                  Text(tr('B2B opportunities'),
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  if (d.requirements.isEmpty)
                    EmptyView(
                        icon: Icons.handshake_rounded,
                        title: tr('No requirements yet'))
                  else
                    for (final r in d.requirements)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _OppTile(r: r),
                      ),
                  const SizedBox(height: 18),
                  Text(tr('Your allocations'),
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  if (d.artisanOrders.isEmpty)
                    Text('No cluster orders assigned yet.',
                        style: Theme.of(context).textTheme.bodyMedium)
                  else
                    for (final o in d.artisanOrders)
                      _MyAllocationTile(o: o),
                ] else ...[
                  Text(tr('Your orders'),
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  if (d.buyerOrders.isEmpty)
                    EmptyView(
                        icon: Icons.receipt_long_rounded,
                        title: tr('No orders yet'),
                        message: 'Post a requirement and run cluster matching.')
                  else
                    for (final o in d.buyerOrders)
                      _BuyerOrderTile(o: OrderResult(asMap(o))),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

class _OrdersData {
  _OrdersData({
    this.artisanOrders = const [],
    this.buyerOrders = const [],
    this.requirements = const [],
  });
  final List<J> artisanOrders;
  final List<J> buyerOrders;
  final List<Requirement> requirements;
}

class _OppTile extends StatelessWidget {
  const _OppTile({required this.r});
  final Requirement r;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => context.push('/buyer/requirement/${r.id}'),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(r.buyerName,
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, color: AppTheme.indigo)),
              const SizedBox(height: 4),
              Text('Looking for ${r.quantity} ${r.craftName ?? 'units'}',
                  style: Theme.of(context).textTheme.bodyLarge),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 6, children: [
                InfoPill('₹${r.priceMin.round()}–₹${r.priceMax.round()}',
                    color: AppTheme.leaf),
                if (r.daysLeft != null)
                  InfoPill('${r.daysLeft} days', color: AppTheme.ochre),
              ]),
              const SizedBox(height: 6),
              const Align(
                alignment: Alignment.centerRight,
                child: Text('View opportunity  →',
                    style: TextStyle(
                        fontWeight: FontWeight.w700, color: AppTheme.terracotta)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MyAllocationTile extends StatelessWidget {
  const _MyAllocationTile({required this.o});
  final J o;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          const Icon(Icons.inventory_2_rounded, color: AppTheme.indigo),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${asStr(o['buyer_name'], 'Buyer')} · ${asStr(o['status'])}',
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${asInt(o['my_units'])} units · ₹${asInt(o['my_payment_inr'])}',
                    style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BuyerOrderTile extends StatelessWidget {
  const _BuyerOrderTile({required this.o});
  final OrderResult o;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => context.push('/buyer/allocation/${o.id}'),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Order ${o.id}',
                        style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text(
                        '${o.totalAllocated}/${o.totalQuantity} units · ${o.status.replaceAll('_', ' ')}',
                        style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              Text('${o.fulfillmentPct}%',
                  style: const TextStyle(
                      fontWeight: FontWeight.w900, color: AppTheme.leaf)),
            ],
          ),
        ),
      ),
    );
  }
}
