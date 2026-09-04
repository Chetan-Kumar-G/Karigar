import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

import 'complaint_labels.dart';

/// Buyer / business "Report an issue" (spec §6). Creates a complaint record;
/// the backend attaches an advisory AI risk flag and routes to human review.
class ReportIssueScreen extends StatefulWidget {
  const ReportIssueScreen({
    required this.artisanId,
    this.artisanName,
    this.orderId,
    super.key,
  });
  final String artisanId;
  final String? artisanName;
  final String? orderId;

  @override
  State<ReportIssueScreen> createState() => _ReportIssueScreenState();
}

class _ReportIssueScreenState extends State<ReportIssueScreen> {
  String _category = kComplaintCategories.first.value;
  String _severity = 'medium';
  final _desc = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _desc.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      final res = await context.read<AppState>().api.createComplaint(
            subjectId: widget.artisanId,
            category: _category,
            severity: _severity,
            description: _desc.text.trim().isEmpty ? null : _desc.text.trim(),
            orderId: widget.orderId,
          );
      if (!mounted) return;
      final complaint = asMap(res['complaint']);
      final risk = asMap(res['risk_flag_result']);
      showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          icon: const Icon(Icons.assignment_turned_in_rounded,
              color: AppTheme.leaf, size: 40),
          title: Text('Issue recorded (${complaint['complaint_id']})'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Thank you. A platform reviewer will investigate.'),
              if (complaint['risk_flag'] != null) ...[
                const SizedBox(height: 10),
                Text('AI risk flag: ${complaint['risk_flag']}',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
              ],
              if (asBool(risk['moved_to_under_review'])) ...[
                const SizedBox(height: 6),
                const Text(
                    'The artisan account is now UNDER REVIEW. AI does not ban '
                    'anyone — a person decides the outcome.',
                    style: TextStyle(fontSize: 12.5)),
              ],
            ],
          ),
          actions: [
            FilledButton(
              onPressed: () {
                Navigator.pop(context);
                context.pop();
              },
              child: const Text('Done'),
            ),
          ],
        ),
      );
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
      appBar: AppBar(title: Text(tr('Report an issue'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('About ${widget.artisanName ?? widget.artisanId}',
              style: Theme.of(context).textTheme.titleMedium),
          if (widget.orderId != null)
            Text('Order ${widget.orderId}',
                style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 14),
          SectionCard(
            title: tr('What went wrong?'),
            child: Column(
              children: [
                for (final c in kComplaintCategories)
                  InkWell(
                    borderRadius: BorderRadius.circular(10),
                    onTap: () => setState(() => _category = c.value),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      child: Row(
                        children: [
                          Icon(
                            _category == c.value
                                ? Icons.radio_button_checked_rounded
                                : Icons.radio_button_unchecked_rounded,
                            color: _category == c.value
                                ? AppTheme.terracotta
                                : AppTheme.inkSoft,
                          ),
                          const SizedBox(width: 12),
                          Expanded(child: Text('${c.icon}  ${c.label}')),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: tr('How serious is it?'),
            child: SegmentedButton<String>(
              segments: [
                ButtonSegment(value: 'low', label: Text(tr('Low'))),
                ButtonSegment(value: 'medium', label: Text(tr('Medium'))),
                ButtonSegment(value: 'high', label: Text(tr('High'))),
              ],
              selected: {_severity},
              onSelectionChanged: (s) => setState(() => _severity = s.first),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _desc,
            maxLines: 4,
            decoration: InputDecoration(
              labelText: tr('Tell us more (optional)'),
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 18),
          ElevatedButton.icon(
            onPressed: _busy ? null : _submit,
            icon: _busy
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2.2, color: Colors.white))
                : const Icon(Icons.send_rounded),
            label: Text(tr('Submit report')),
          ),
          const SizedBox(height: 10),
          Text(
            'Reports are investigated by a person. Filing a report does not '
            'automatically penalise the artisan.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
