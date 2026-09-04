import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';

class NewRequirementScreen extends StatefulWidget {
  const NewRequirementScreen({super.key});

  @override
  State<NewRequirementScreen> createState() => _NewRequirementScreenState();
}

class _NewRequirementScreenState extends State<NewRequirementScreen> {
  final _title = TextEditingController(text: '2,000 handmade baskets for gift kits');
  final _qty = TextEditingController(text: '2000');
  final _min = TextEditingController(text: '210');
  final _max = TextEditingController(text: '290');
  RefItem? _craft;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [_title, _qty, _min, _max]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await context.read<AppState>().api.createRequirement({
        'title': _title.text.trim(),
        'craft_id': _craft?.id,
        'quantity': int.tryParse(_qty.text.trim()) ?? 0,
        'price_min': double.tryParse(_min.text.trim()) ?? 0,
        'price_max': double.tryParse(_max.text.trim()) ?? 0,
      });
      if (!mounted) return;
      context.pushReplacement('/buyer/requirement/${r.id}');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final crafts = context.watch<AppState>().reference?.crafts ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('Post a requirement')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _title,
            decoration: const InputDecoration(labelText: 'Title'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _qty,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Quantity (units)'),
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: TextField(
                controller: _min,
                keyboardType: TextInputType.number,
                decoration:
                    const InputDecoration(labelText: 'Min ₹/unit', prefixText: '₹ '),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextField(
                controller: _max,
                keyboardType: TextInputType.number,
                decoration:
                    const InputDecoration(labelText: 'Max ₹/unit', prefixText: '₹ '),
              ),
            ),
          ]),
          const SizedBox(height: 16),
          Text('Craft', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
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
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppTheme.danger)),
          ],
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: _busy ? null : _submit,
            icon: const Icon(Icons.send_rounded),
            label: const Text('Post & find cluster'),
          ),
        ],
      ),
    );
  }
}
