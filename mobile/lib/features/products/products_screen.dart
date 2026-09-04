import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

class ProductsScreen extends StatefulWidget {
  const ProductsScreen({super.key});

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  late Future<List<Product>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.myProducts();
  }

  void _reload() => setState(() {
        _future = context.read<AppState>().api.myProducts();
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('My products'))),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<Product>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const LoadingView();
            }
            if (snap.hasError) {
              return ErrorView(snap.error!, onRetry: _reload);
            }
            final products = snap.data!;
            if (products.isEmpty) {
              return EmptyView(
                icon: Icons.add_a_photo_rounded,
                title: tr('No products yet'),
                message:
                    'Add your first product — it only takes a photo and a voice note.',
                action: ElevatedButton(
                  onPressed: () => context.push('/create'),
                  child: Text(tr('Add product')),
                ),
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
              itemCount: products.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _ProductTile(
                product: products[i],
                onTap: () => context.push('/product/${products[i].id}'),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _ProductTile extends StatelessWidget {
  const _ProductTile({required this.product, required this.onTap});
  final Product product;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              RemoteImage(product.primaryImage, width: 74, height: 74),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(product.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w800)),
                    const SizedBox(height: 4),
                    Text(product.craftName ?? product.category ?? '—',
                        style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: 6),
                    Row(children: [
                      _StatusChip(status: product.status),
                      const SizedBox(width: 8),
                      if (product.price != null)
                        Text('₹${product.price!.round()}',
                            style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                color: AppTheme.terracotta)),
                    ]),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: AppTheme.inkSoft),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (status) {
      'published' => (tr('Live'), AppTheme.leaf),
      'priced' => (tr('Priced'), AppTheme.indigo),
      'catalogued' => (tr('Catalogued'), AppTheme.indigo),
      'analyzing' => (tr('Photo added'), AppTheme.ochre),
      _ => (tr('Draft'), AppTheme.inkSoft),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w800, color: color)),
    );
  }
}
