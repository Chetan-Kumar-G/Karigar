import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../providers/product_flow.dart';
import '../../widgets/common.dart';
import 'create_product_screen.dart';

/// Final review + Publish (spec §18 → "Listing Created").
class CatalogPreviewScreen extends StatefulWidget {
  const CatalogPreviewScreen({required this.productId, super.key});
  final String productId;

  @override
  State<CatalogPreviewScreen> createState() => _CatalogPreviewScreenState();
}

class _CatalogPreviewScreenState extends State<CatalogPreviewScreen> {
  bool _publishing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final flow = context.read<ProductFlow>();
      if (flow.product?.id != widget.productId) {
        flow.loadExisting(widget.productId);
      }
    });
  }

  Future<void> _publish() async {
    setState(() {
      _publishing = true;
      _error = null;
    });
    try {
      final p = await context.read<ProductFlow>().publish();
      if (!mounted) return;
      showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          icon: const Icon(Icons.check_circle_rounded,
              color: AppTheme.leaf, size: 44),
          title: const Text('Listing created'),
          content: Text(
              '"${p.title}" is now live in the marketplace at ₹${p.price?.round() ?? '—'}.'),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                context.go('/home');
                context.push('/market');
              },
              child: const Text('See it in the market'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(context);
                context.go('/home');
              },
              child: const Text('Done'),
            ),
          ],
        ),
      );
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _publishing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<ProductFlow>();
    final p = flow.product;
    final cat = flow.catalog;
    final price = flow.price;

    return Scaffold(
      appBar: AppBar(title: const Text('Review & publish')),
      body: p == null
          ? const LoadingView()
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const StepDots(active: 4),
                const SizedBox(height: 16),
                if (p.primaryImage != null)
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 260),
                    child: AspectRatio(
                      aspectRatio: 16 / 10,
                      child: RemoteImage(p.primaryImage, radius: 18),
                    ),
                  ),
                const SizedBox(height: 14),
                Text(cat?.seoTitle ?? p.title,
                    style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 6),
                if (price != null)
                  Text('₹${price.recommended}',
                      style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                          color: AppTheme.terracotta)),
                const SizedBox(height: 14),
                SectionCard(
                  title: 'Listing summary',
                  child: Column(
                    children: [
                      KeyValueRow('Craft', p.craftName ?? '—'),
                      KeyValueRow(
                          'Photo readiness',
                          p.images.isNotEmpty &&
                                  p.images.first.readinessScore != null
                              ? '${p.images.first.readinessScore}/100'
                              : '—'),
                      KeyValueRow('Catalog', cat != null ? 'Ready (EN + HI)' : '—'),
                      KeyValueRow(
                          'Price floor',
                          price != null ? '₹${price.floor}' : '—'),
                      KeyValueRow('Passport',
                          flow.passport != null ? 'Generated' : '—'),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                if (cat != null && cat.flags.isNotEmpty)
                  SectionCard(
                    title: 'Before you publish',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        for (final f in cat.flags)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(Icons.info_rounded,
                                    color: AppTheme.ochre, size: 18),
                                const SizedBox(width: 8),
                                Expanded(child: Text(f)),
                              ],
                            ),
                          ),
                        const SizedBox(height: 4),
                        Text(
                          'You can still publish. Unverified origin claims will '
                          'show as "artisan-reported" until documented.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: AppTheme.danger)),
                ],
                const SizedBox(height: 18),
                ElevatedButton.icon(
                  onPressed: _publishing ? null : _publish,
                  icon: _publishing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.2, color: Colors.white))
                      : const Icon(Icons.publish_rounded),
                  label: const Text('Publish listing'),
                ),
              ],
            ),
    );
  }
}
