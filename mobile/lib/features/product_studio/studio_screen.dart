import 'dart:typed_data';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show PlatformException;
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/product_flow.dart';
import '../../widgets/ai_progress.dart';
import '../../widgets/common.dart';
import '../../widgets/score_bar.dart';
import '../product_studio/create_product_screen.dart';

/// F1 — AI Product Studio + Product Readiness Quality Gate (spec §8).
class StudioScreen extends StatefulWidget {
  const StudioScreen({required this.productId, super.key});
  final String productId;

  @override
  State<StudioScreen> createState() => _StudioScreenState();
}

class _StudioScreenState extends State<StudioScreen> {
  final _picker = ImagePicker();
  Uint8List? _localImage;

  static const _labels = {
    'sharpness': 'Sharpness',
    'exposure': 'Lighting',
    'framing': 'Framing',
    'background_cleanliness': 'Background',
    'resolution': 'Resolution',
    'colour_fidelity': 'Colour accuracy',
  };

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

  Future<void> _pick(ImageSource src) async {
    final flow = context.read<ProductFlow>();
    final messenger = ScaffoldMessenger.of(context);
    // Desktop browsers have no camera picker — fall back to the file chooser.
    final effective =
        kIsWeb && src == ImageSource.camera ? ImageSource.gallery : src;
    try {
      final x = await _picker.pickImage(
        source: effective,
        maxWidth: 2200,
        imageQuality: 92,
      );
      if (x == null) return; // user cancelled — not an error
      final bytes = await x.readAsBytes();
      if (bytes.isEmpty) {
        messenger.showSnackBar(appSnack(
            'That photo came back empty. Try again or pick from the gallery.',
            danger: true));
        return;
      }
      setState(() => _localImage = bytes);
      await flow.analyze(bytes, filename: x.name);
    } on PlatformException catch (e) {
      _handlePickFailure(e.code, src);
    } catch (e) {
      // Never crash on a device-capability problem — offer the gallery instead.
      _handlePickFailure('$e', src);
    }
  }

  void _handlePickFailure(String code, ImageSource src) {
    final messenger = ScaffoldMessenger.of(context);
    final lc = code.toLowerCase();
    final permissionDenied = lc.contains('access_denied') ||
        lc.contains('permission') ||
        lc.contains('denied');
    final noCamera = lc.contains('no_available_camera') ||
        lc.contains('no camera') ||
        lc.contains('cameradelegate') ||
        lc.contains('not available');

    if (src == ImageSource.camera && permissionDenied) {
      messenger.showSnackBar(appSnack(
        'Camera permission is off. Turn it on in Settings, or choose a photo '
        'from the gallery.',
        danger: true,
      ));
      return;
    }
    if (src == ImageSource.camera && (noCamera || !permissionDenied)) {
      // Emulator with no camera, or any other camera failure: guide to gallery.
      _offerGalleryFallback();
      return;
    }
    messenger.showSnackBar(appSnack(
      permissionDenied
          ? 'Photo permission is off. Turn it on in Settings to pick a photo.'
          : 'Could not open that photo. Please try another one.',
      danger: true,
    ));
  }

  void _offerGalleryFallback() {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Camera not available'),
        content: const Text(
          'This device or emulator has no working camera. You can still add '
          'your product photo from the gallery.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Not now'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              _pick(ImageSource.gallery);
            },
            child: const Text('Choose from gallery'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<ProductFlow>();
    final r = flow.readiness;

    return Scaffold(
      appBar: AppBar(title: Text(tr('AI Product Studio'))),
      body: flow.busy
          ? const AiProgress(steps: AiProgress.analyze, title: 'AI Product Studio')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const StepDots(active: 1),
                  const SizedBox(height: 16),
                  if (r == null) ...[
                    _PhotoPlaceholder(local: _localImage),
                    const SizedBox(height: 16),
                    Text('Take one photo of your product',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 6),
                    Text(
                      'Place it on a plain cloth or wall, in good light. '
                      'We will check it and fix what we can.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    Row(children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () => _pick(ImageSource.camera),
                          icon: const Icon(Icons.camera_alt_rounded),
                          label: const Text('Camera'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _pick(ImageSource.gallery),
                          icon: const Icon(Icons.photo_library_rounded),
                          label: const Text('Gallery'),
                        ),
                      ),
                    ]),
                    const SizedBox(height: 8),
                    Text(
                      'No working camera (e.g. on an emulator)? Gallery works '
                      'exactly the same for this step.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    if (flow.error != null) ...[
                      const SizedBox(height: 14),
                      Text(flow.error!,
                          style: const TextStyle(color: AppTheme.danger)),
                    ],
                  ] else
                    _Result(
                      result: r,
                      local: _localImage,
                      onRetake: () {
                        setState(() => _localImage = null);
                        context.read<ProductFlow>().clearReadiness();
                      },
                      onContinue: () =>
                          context.pushReplacement('/voice/${widget.productId}'),
                      labels: _labels,
                    ),
                ],
              ),
            ),
    );
  }
}

class _PhotoPlaceholder extends StatelessWidget {
  const _PhotoPlaceholder({this.local});
  final Uint8List? local;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: 240),
      child: AspectRatio(
        aspectRatio: 4 / 3,
        child: Container(
          decoration: BoxDecoration(
            color: AppTheme.sand,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: AppTheme.line),
          ),
          clipBehavior: Clip.antiAlias,
          child: local != null
              ? Image.memory(local!, fit: BoxFit.cover)
              : const Center(
                  child: Icon(Icons.add_a_photo_outlined,
                      size: 46, color: AppTheme.inkSoft),
                ),
        ),
      ),
    );
  }
}

class _Result extends StatelessWidget {
  const _Result({
    required this.result,
    required this.local,
    required this.onRetake,
    required this.onContinue,
    required this.labels,
  });
  final ReadinessResult result;
  final Uint8List? local;
  final VoidCallback onRetake;
  final VoidCallback onContinue;
  final Map<String, String> labels;

  @override
  Widget build(BuildContext context) {
    final decisionColor = scoreColor(result.score);
    final ba = result.beforeAfter;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionCard(
          title: tr('Readiness score'),
          trailing: ModeBadge(result.meta['mode']?.toString() ?? 'REAL'),
          child: Column(
            children: [
              Center(child: ScoreDial(value: result.score)),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: decisionColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  switch (result.decision) {
                    'accept' => 'Good to publish',
                    'auto_enhance' => 'We improved it automatically',
                    _ => 'Please retake this photo',
                  },
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      fontWeight: FontWeight.w800, color: decisionColor),
                ),
              ),
              const SizedBox(height: 12),
              for (final e in result.components.entries)
                ScoreBar(label: labels[e.key] ?? e.key, value: e.value),
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (ba != null)
          SectionCard(
            title: '${tr('Before')}  →  ${tr('After')}',
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                        child: _BAImage(
                            label: 'Before',
                            child: local != null
                                ? Image.memory(local!, fit: BoxFit.cover)
                                : RemoteImage(result.originalUrl))),
                    const SizedBox(width: 10),
                    Expanded(
                        child: _BAImage(
                            label: 'After',
                            child: RemoteImage(result.enhancedUrl))),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Lighting ${_delta(ba, "exposure")}   ·   '
                  'Background ${_delta(ba, "background_cleanliness")}   ·   '
                  'Colour ${_delta(ba, "colour_fidelity")}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                if (result.gateReasons.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(result.gateReasons.first,
                      style: Theme.of(context).textTheme.bodySmall),
                ],
              ],
            ),
          )
        else if (result.gateVerdict == 'ACCEPT_ORIGINAL' &&
            result.gateReasons.isNotEmpty &&
            result.decision == 'accept')
          SectionCard(
            title: 'We kept your original photo',
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.verified_user_rounded, color: AppTheme.leaf),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    result.gateReasons.first,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          )
        else if (result.retakeGuidance != null)
          SectionCard(
            title: tr('How to fix it'),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.lightbulb_rounded, color: AppTheme.ochre),
                const SizedBox(width: 10),
                Expanded(
                  child: Text('${result.retakeGuidance!['en']}',
                      style: Theme.of(context).textTheme.bodyLarge),
                ),
              ],
            ),
          ),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: onRetake,
              icon: const Icon(Icons.replay_rounded),
              label: Text(tr('Retake photo')),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: ElevatedButton.icon(
              onPressed: onContinue,
              icon: const Icon(Icons.mic_rounded),
              label: Text(tr('Add voice')),
            ),
          ),
        ]),
        const SizedBox(height: 8),
        Text(
          'Confidence ${(result.confidence * 100).round()}% · '
          '${result.meta['model'] ?? 'OpenCV pipeline'}',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  static String _delta(Map ba, String key) {
    final before = (ba['before']?['component_scores']?[key] ?? 0) as num;
    final after = (ba['after']?['component_scores']?[key] ?? 0) as num;
    final d = (after - before).round();
    return d >= 0 ? '+$d' : '$d';
  }
}

class _BAImage extends StatelessWidget {
  const _BAImage({required this.label, required this.child});
  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AspectRatio(
          aspectRatio: 1,
          child: ClipRRect(
              borderRadius: BorderRadius.circular(12), child: child),
        ),
        const SizedBox(height: 6),
        Text(label,
            style: const TextStyle(
                fontWeight: FontWeight.w700, color: AppTheme.inkSoft)),
      ],
    );
  }
}
