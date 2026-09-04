import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';
import '../trust/trust_widgets.dart';

class ProductDetailScreen extends StatefulWidget {
  const ProductDetailScreen({required this.productId, super.key});
  final String productId;

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  late Future<Product> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.product(widget.productId);
  }

  @override
  Widget build(BuildContext context) {
    final isArtisan = context.read<AppState>().isArtisan;
    return Scaffold(
      appBar: AppBar(title: const Text('Product')),
      body: FutureBuilder<Product>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const LoadingView();
          }
          if (snap.hasError) {
            return ErrorView(snap.error!,
                onRetry: () => setState(() {
                      _future = context
                          .read<AppState>()
                          .api
                          .product(widget.productId);
                    }));
          }
          final p = snap.data!;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 280),
                child: AspectRatio(
                  aspectRatio: 16 / 11,
                  child: RemoteImage(p.primaryImage, radius: 18),
                ),
              ),
              const SizedBox(height: 14),
              Text(p.seoTitle ?? p.title,
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 6),
              Row(children: [
                if (p.price != null)
                  Text('₹${p.price!.round()}',
                      style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                          color: AppTheme.terracotta)),
                const Spacer(),
                Text(p.craftName ?? '',
                    style: Theme.of(context).textTheme.bodyMedium),
              ]),
              const SizedBox(height: 14),
              if (p.descriptionEn != null)
                SectionCard(
                  title: 'Description',
                  child: Text(p.descriptionEn!,
                      style: Theme.of(context).textTheme.bodyLarge),
                ),
              const SizedBox(height: 12),
              if (p.seoKeywords.isNotEmpty)
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [for (final k in p.seoKeywords) Chip(label: Text(k))],
                ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: () => context.push('/passport/${p.id}',
                    extra: {'inFlow': false}),
                icon: const Icon(Icons.verified_rounded),
                label: const Text('View Craft Passport'),
              ),
              if (p.artisanId != null) ...[
                const SizedBox(height: 10),
                ViewVerifiedArtisanButton(artisanId: p.artisanId!),
              ],
              if (isArtisan && p.artisanId == context.read<AppState>().session!.id) ...[
                const SizedBox(height: 10),
                if (p.status != 'published')
                  ElevatedButton.icon(
                    onPressed: () => context.push('/studio/${p.id}'),
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('Continue setup'),
                  )
                else
                  OutlinedButton.icon(
                    onPressed: () => context.push('/pricing/${p.id}',
                        extra: {'inFlow': false}),
                    icon: const Icon(Icons.calculate_rounded),
                    label: const Text('Re-check price'),
                  ),
              ],
            ],
          );
        },
      ),
    );
  }
}
