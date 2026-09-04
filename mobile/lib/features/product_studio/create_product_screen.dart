import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../providers/product_flow.dart';

/// Step 1 of the creation flow (spec §18): name the product + pick the craft.
class CreateProductScreen extends StatefulWidget {
  const CreateProductScreen({super.key});

  @override
  State<CreateProductScreen> createState() => _CreateProductScreenState();
}

class _CreateProductScreenState extends State<CreateProductScreen> {
  final _title = TextEditingController();
  RefItem? _craft;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    if (_title.text.trim().isEmpty) {
      setState(() => _error = 'Give your product a short name first.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    final flow = context.read<ProductFlow>();
    await flow.start(
      title: _title.text.trim(),
      craftId: _craft?.id,
      category: _craft?.extra['name'] as String?,
    );
    if (!mounted) return;
    setState(() => _busy = false);
    if (flow.error != null) {
      setState(() => _error = flow.error);
    } else {
      context.pushReplacement('/studio/${flow.product!.id}');
    }
  }

  @override
  Widget build(BuildContext context) {
    final crafts = context.watch<AppState>().reference?.crafts ?? [];
    return Scaffold(
      appBar: AppBar(title: Text(tr('Add product'))),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const _StepDots(active: 0),
            const SizedBox(height: 18),
            Text('What are you selling?',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            TextField(
              controller: _title,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Product name',
                hintText: 'e.g. Madhubani cotton dupatta',
                prefixIcon: Icon(Icons.label_rounded),
              ),
            ),
            const SizedBox(height: 18),
            Text('Which craft is this?',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('This links your product to its heritage records.',
                style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 10),
            if (crafts.isEmpty)
              const LinearProgressIndicator()
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final c in crafts)
                    ChoiceChip(
                      label: Text(c.name),
                      selected: _craft?.id == c.id,
                      onSelected: (_) => setState(() => _craft = c),
                    ),
                ],
              ),
            if (_error != null) ...[
              const SizedBox(height: 14),
              Text(_error!,
                  style: const TextStyle(
                      color: AppTheme.danger, fontWeight: FontWeight.w600)),
            ],
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _busy ? null : _start,
              icon: _busy
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2.2, color: Colors.white))
                  : const Icon(Icons.arrow_forward_rounded),
              label: const Text('Continue to photo'),
            ),
          ],
        ),
      ),
    );
  }
}

class _StepDots extends StatelessWidget {
  const _StepDots({required this.active});
  final int active;
  static const _labels = ['Name', 'Photo', 'Voice', 'Price', 'Publish'];

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (var i = 0; i < _labels.length; i++) ...[
          Column(
            children: [
              CircleAvatar(
                radius: 13,
                backgroundColor:
                    i <= active ? AppTheme.terracotta : AppTheme.sand,
                child: Text('${i + 1}',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        color: i <= active ? Colors.white : AppTheme.inkSoft)),
              ),
              const SizedBox(height: 4),
              Text(_labels[i],
                  style: TextStyle(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                      color: i <= active ? AppTheme.ink : AppTheme.inkSoft)),
            ],
          ),
          if (i < _labels.length - 1)
            const Expanded(
                child: Divider(color: AppTheme.line, thickness: 1.5)),
        ],
      ],
    );
  }
}

/// Reusable outside this file too.
class StepDots extends StatelessWidget {
  const StepDots({required this.active, super.key});
  final int active;
  @override
  Widget build(BuildContext context) => _StepDots(active: active);
}
