import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/json.dart';
import '../../core/theme.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

class InventoryScreen extends StatefulWidget {
  const InventoryScreen({super.key});

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  late Future<J> _future;
  // Product ids with a write in flight — blocks a second tap on the same row
  // from racing the first one (the usual cause of a transient DB-lock error).
  final Set<String> _pending = {};

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.inventory();
  }

  void _reload() => setState(() {
        _future = context.read<AppState>().api.inventory();
      });

  Future<void> _adjust(String id, int units) async {
    if (_pending.contains(id)) return; // already saving this row
    setState(() => _pending.add(id));
    final api = context.read<AppState>().api;
    final target = units.clamp(0, 99999);
    try {
      try {
        await api.setInventory(id, target);
      } on ApiException catch (e) {
        if (!e.isRetryable) rethrow;
        await Future<void>.delayed(const Duration(milliseconds: 400));
        await api.setInventory(id, target); // one automatic retry
      }
      _reload();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(appSnack('$e', danger: true));
      }
    } finally {
      if (mounted) setState(() => _pending.remove(id));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Inventory')),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<J>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView();
            }
            if (snap.hasError) {
              return ErrorView(snap.error!, onRetry: _reload);
            }
            final items = asMapList(snap.data!['items']);
            if (items.isEmpty) {
              return const EmptyView(
                icon: Icons.inventory_2_rounded,
                title: 'Nothing published yet',
                message: 'Publish a product to start tracking stock.',
              );
            }
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
              children: [
                SectionCard(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      const Icon(Icons.warehouse_rounded,
                          color: AppTheme.indigo),
                      const SizedBox(width: 10),
                      Text('${asInt(snap.data!['total_units'])} units in stock',
                          style: const TextStyle(
                              fontWeight: FontWeight.w800, fontSize: 16)),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                for (final it in items)
                  _InvTile(
                    it: it,
                    busy: _pending.contains(asStr(it['product_id'])),
                    onDelta: (d) => _adjust(
                        asStr(it['product_id']), asInt(it['available_units']) + d),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _InvTile extends StatelessWidget {
  const _InvTile({required this.it, required this.onDelta, this.busy = false});
  final J it;
  final ValueChanged<int> onDelta;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final units = asInt(it['available_units']);
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            RemoteImage(it['primary_image'] as String?, width: 58, height: 58),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(asStr(it['title']),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  if (it['price_inr'] != null)
                    Text('₹${asInt(it['price_inr'])}',
                        style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            IconButton.filledTonal(
              onPressed: (busy || units <= 0) ? null : () => onDelta(-1),
              icon: const Icon(Icons.remove_rounded),
            ),
            SizedBox(
              width: 40,
              child: busy
                  ? const Center(
                      child: SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2)),
                    )
                  : Text('$units',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                          fontWeight: FontWeight.w900, fontSize: 16)),
            ),
            IconButton.filledTonal(
              onPressed: busy ? null : () => onDelta(1),
              icon: const Icon(Icons.add_rounded),
            ),
          ],
        ),
      ),
    );
  }
}
