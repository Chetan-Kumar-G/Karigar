import 'dart:async';
import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:record/record.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/product_flow.dart';
import '../../widgets/ai_progress.dart';
import '../../widgets/common.dart';
import '../product_studio/create_product_screen.dart';

/// F2 — Multilingual Grounded Auto-Cataloger (spec §9, §10).
class VoiceScreen extends StatefulWidget {
  const VoiceScreen({required this.productId, super.key});
  final String productId;

  @override
  State<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends State<VoiceScreen> {
  final _recorder = AudioRecorder();
  final _typed = TextEditingController();
  String _lang = 'hi';
  bool _recording = false;
  int _seconds = 0;
  Timer? _timer;
  String? _recordedPath;

  static const _langs = {'hi': 'हिन्दी', 'mai': 'मैथिली', 'as': 'অসমীয়া', 'en': 'English'};

  @override
  void dispose() {
    _timer?.cancel();
    _recorder.dispose();
    _typed.dispose();
    super.dispose();
  }

  Future<void> _toggleRecord() async {
    if (_recording) {
      final path = await _recorder.stop();
      _timer?.cancel();
      setState(() {
        _recording = false;
        _recordedPath = path;
      });
      return;
    }
    if (!await _recorder.hasPermission()) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(appSnack(
            'Microphone permission is needed. You can type your description instead.',
            danger: true));
      }
      return;
    }
    final stamp = DateTime.now().millisecondsSinceEpoch;
    final p = kIsWeb
        ? 'voice_$stamp.webm' // record_web ignores this and returns a blob URL
        : '${(await getTemporaryDirectory()).path}/voice_$stamp.m4a';
    await _recorder.start(const RecordConfig(), path: p);
    setState(() {
      _recording = true;
      _seconds = 0;
    });
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _seconds++);
    });
  }

  Future<void> _run({bool demo = false}) async {
    final flow = context.read<ProductFlow>();
    final typed = _typed.text.trim();
    Uint8List? audioBytes;
    if (!demo && _recordedPath != null && typed.isEmpty) {
      try {
        audioBytes = await XFile(_recordedPath!).readAsBytes();
      } catch (_) {
        audioBytes = null;
      }
      // A real recording is at least a few KB. Near-empty = the mic captured
      // nothing (common on an emulator without host-audio input).
      if (!kIsWeb && (audioBytes == null || audioBytes.length < 1500)) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(appSnack(
            'That recording had no sound. On an emulator, open Extended Controls '
            '(•••) → Microphone → enable host audio. Or type your description below.',
            danger: true,
          ));
        }
        return;
      }
    }
    await flow.runCatalog(
      audioBytes: audioBytes,
      typedTranscript: (!demo && typed.isNotEmpty) ? typed : null,
      languageHint: _lang,
    );
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<ProductFlow>();
    final result = flow.catalog;

    return Scaffold(
      appBar: AppBar(title: Text(tr('Add voice'))),
      body: flow.busy
          ? const AiProgress(steps: AiProgress.catalog, title: 'Auto-Cataloger')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const StepDots(active: 2),
                  const SizedBox(height: 16),
                  if (result == null)
                    _Recorder(
                      recording: _recording,
                      seconds: _seconds,
                      hasRecording: _recordedPath != null,
                      lang: _lang,
                      langs: _langs,
                      typed: _typed,
                      onLang: (l) => setState(() => _lang = l),
                      onToggle: _toggleRecord,
                      onGenerate: () => _run(),
                      onDemo: () => _run(demo: true),
                      error: flow.error,
                    )
                  else
                    _CatalogResultView(
                      result: result,
                      onContinue: () =>
                          context.pushReplacement('/passport/${widget.productId}'),
                      onRedo: flow.clearCatalog,
                    ),
                ],
              ),
            ),
    );
  }
}

class _Recorder extends StatelessWidget {
  const _Recorder({
    required this.recording,
    required this.seconds,
    required this.hasRecording,
    required this.lang,
    required this.langs,
    required this.typed,
    required this.onLang,
    required this.onToggle,
    required this.onGenerate,
    required this.onDemo,
    required this.error,
  });
  final bool recording;
  final int seconds;
  final bool hasRecording;
  final String lang;
  final Map<String, String> langs;
  final TextEditingController typed;
  final ValueChanged<String> onLang;
  final VoidCallback onToggle;
  final VoidCallback onGenerate;
  final VoidCallback onDemo;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Speak in your own language',
            style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 6),
        Text('Say the material, technique, colours, region and how long it took.',
            style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 14),
        Wrap(
          spacing: 8,
          children: [
            for (final e in langs.entries)
              ChoiceChip(
                label: Text(e.value),
                selected: lang == e.key,
                onSelected: (_) => onLang(e.key),
              ),
          ],
        ),
        const SizedBox(height: 24),
        Center(
          child: GestureDetector(
            onTap: onToggle,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 128,
              height: 128,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: recording ? AppTheme.danger : AppTheme.terracotta,
                boxShadow: [
                  BoxShadow(
                    color: (recording ? AppTheme.danger : AppTheme.terracotta)
                        .withValues(alpha: 0.3),
                    blurRadius: recording ? 30 : 12,
                    spreadRadius: recording ? 6 : 0,
                  ),
                ],
              ),
              child: Icon(recording ? Icons.stop_rounded : Icons.mic_rounded,
                  color: Colors.white, size: 54),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Center(
          child: Text(
            recording
                ? '00:${seconds.toString().padLeft(2, '0')}  ·  tap to stop'
                : hasRecording
                    ? 'Recording ready'
                    : 'Tap to record',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
        const SizedBox(height: 20),
        const Row(children: [
          Expanded(child: Divider()),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 8),
            child: Text('or type it', style: TextStyle(color: AppTheme.inkSoft)),
          ),
          Expanded(child: Divider()),
        ]),
        const SizedBox(height: 12),
        TextField(
          controller: typed,
          maxLines: 3,
          decoration: const InputDecoration(
            hintText:
                'e.g. This is a cotton dupatta, hand block printed in Madhubani, '
                'yellow and red, took 4 days.',
          ),
        ),
        if (error != null) ...[
          const SizedBox(height: 12),
          Text(error!, style: const TextStyle(color: AppTheme.danger)),
        ],
        const SizedBox(height: 18),
        ElevatedButton.icon(
          onPressed: onGenerate,
          icon: const Icon(Icons.auto_awesome_rounded),
          label: Text(tr('Generating catalog…')),
        ),
        const SizedBox(height: 8),
        TextButton(
          onPressed: onDemo,
          child: const Text('Use the demo recording instead'),
        ),
      ],
    );
  }
}

class _CatalogResultView extends StatelessWidget {
  const _CatalogResultView({
    required this.result,
    required this.onContinue,
    required this.onRedo,
  });
  final CatalogResult result;
  final VoidCallback onContinue;
  final VoidCallback onRedo;

  @override
  Widget build(BuildContext context) {
    final attrs = result.attributes;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (result.asrIsDemoFallback) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.amberBg,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.ochre),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.info_rounded, color: AppTheme.ochre, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Speech-to-text is not enabled on this server, so the '
                    'transcript below is a sample — not your recording. Tap '
                    '“Record again” and type your description for an accurate '
                    'listing.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],
        SectionCard(
          title: result.asrIsDemoFallback ? 'Sample transcript' : tr('Transcript'),
          trailing: ModeBadge(result.asrIsDemoFallback
              ? 'DEMO'
              : (result.asrMode == 'REAL' ? 'REAL' : 'TYPED')),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('"${result.transcript}"',
                  style: const TextStyle(
                      fontStyle: FontStyle.italic, color: AppTheme.ink)),
              const SizedBox(height: 8),
              Text(
                'Language: ${result.language.toUpperCase()} · '
                'ASR confidence ${(result.asrConfidence * 100).round()}% · '
                '${result.asrEngine}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        SectionCard(
          title: 'What we understood',
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (attrs['material'] != null)
                InfoPill('Material: ${attrs['material']}',
                    icon: Icons.texture_rounded),
              if (attrs['technique'] != null)
                InfoPill('Technique: ${attrs['technique']}',
                    icon: Icons.brush_rounded),
              if (attrs['region_claimed'] != null)
                InfoPill('Region: ${attrs['region_claimed']}',
                    icon: Icons.place_rounded, color: AppTheme.ochre),
              if ((attrs['colors'] as List?)?.isNotEmpty ?? false)
                InfoPill('Colours: ${(attrs['colors'] as List).join(', ')}',
                    icon: Icons.palette_rounded),
              if (attrs['effort_days'] != null)
                InfoPill('${attrs['effort_days']} days to make',
                    icon: Icons.schedule_rounded),
            ],
          ),
        ),
        const SizedBox(height: 12),
        SectionCard(
          title: tr('Claim consistency check'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                result.verificationSummary['headline'] as String? ??
                    'AI checks whether the artisan\'s claims are consistent with '
                        'available visual evidence and trusted craft data.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 10),
              if (result.claims.isNotEmpty)
                for (final c in result.claims)
                  _ClaimRow(data: c)
              else ...[
                for (final e in result.grounding.entries)
                  _GroundRow(label: e.key, status: e.value),
                for (final e in result.visual.entries)
                  if ((e.value as Map)['label'] != 'not_visually_checkable')
                    _VisualRow(
                        label: e.key,
                        data: Map<String, dynamic>.from(e.value as Map)),
              ],
              if ((result.verificationSummary['disclaimer'] as String?)
                      ?.isNotEmpty ??
                  false) ...[
                const SizedBox(height: 8),
                Text(
                  result.verificationSummary['disclaimer'] as String,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(fontStyle: FontStyle.italic),
                ),
              ],
              if (result.flags.isNotEmpty) ...[
                const SizedBox(height: 8),
                for (final f in result.flags)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.warning_amber_rounded,
                          color: AppTheme.ochre, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(f,
                            style: const TextStyle(
                                color: AppTheme.terracottaDark,
                                fontWeight: FontWeight.w600)),
                      ),
                    ],
                  ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 12),
        _GeneratedCopy(result: result),
        const SizedBox(height: 18),
        Row(children: [
          Expanded(
            child: OutlinedButton(
                onPressed: onRedo, child: const Text('Record again')),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: ElevatedButton.icon(
              onPressed: onContinue,
              icon: const Icon(Icons.verified_rounded),
              label: Text(tr('Digital Craft Passport')),
            ),
          ),
        ]),
      ],
    );
  }
}

/// One artisan claim + its consistency status (F2 claim-consistency).
class _ClaimRow extends StatelessWidget {
  const _ClaimRow({required this.data});
  final Map<String, dynamic> data;

  static (IconData, Color, String) _style(String status) => switch (status) {
        'SUPPORTED' => (
            Icons.verified_rounded,
            AppTheme.leaf,
            'Supported by craft data'
          ),
        'VISUALLY_CONSISTENT' => (
            Icons.image_rounded,
            AppTheme.leaf,
            'Consistent with the photo'
          ),
        'CONTRADICTED' => (
            Icons.report_rounded,
            AppTheme.danger,
            'Contradicted — review'
          ),
        'NEEDS_HUMAN_REVIEW' => (
            Icons.gavel_rounded,
            AppTheme.ochre,
            'Needs human review'
          ),
        _ => (Icons.help_rounded, AppTheme.inkSoft, 'Unknown — can\'t verify'),
      };

  @override
  Widget build(BuildContext context) {
    final status = '${data['status']}';
    final (icon, color, label) = _style(status);
    final conf = (data['confidence'] as num?)?.toDouble() ?? 0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${data['claim']}',
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 1),
                Text(
                  '$label${conf > 0 ? ' · ${(conf * 100).round()}%' : ''}',
                  style: TextStyle(
                      color: color, fontWeight: FontWeight.w600, fontSize: 12),
                ),
                if ((data['evidence'] as String?)?.isNotEmpty ?? false)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('${data['evidence']}',
                        style: Theme.of(context).textTheme.bodySmall),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GroundRow extends StatelessWidget {
  const _GroundRow({required this.label, required this.status});
  final String label;
  final String status;

  @override
  Widget build(BuildContext context) {
    final ok = status.startsWith('confirmed');
    final flagged = status.startsWith('flagged') || status == 'unsupported';
    final (icon, color) = ok
        ? (Icons.check_circle_rounded, AppTheme.leaf)
        : flagged
            ? (Icons.error_rounded, AppTheme.ochre)
            : (Icons.help_rounded, AppTheme.inkSoft);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '${_pretty(label)} — ${_human(status)}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  static String _pretty(String k) =>
      k.replaceAll('_claimed', '').replaceAll('_', ' ');
  static String _human(String s) => switch (s) {
        'confirmed_from_voice' => 'supported by what you said',
        'confirmed_gi_registered' => 'GI-registered craft',
        'flagged_unverified_gi_claim' =>
          'origin claim needs GI documentation to show as verified',
        'unsupported' => 'not found in your recording',
        _ => s.replaceAll('_', ' '),
      };
}

class _VisualRow extends StatelessWidget {
  const _VisualRow({required this.label, required this.data});
  final String label;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final lbl = '${data['label']}';
    final (icon, color) = switch (lbl) {
      'entailment' => (Icons.image_rounded, AppTheme.leaf),
      'contradiction' => (Icons.report_rounded, AppTheme.danger),
      _ => (Icons.image_search_rounded, AppTheme.inkSoft),
    };
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Photo vs "${label.replaceAll('_', ' ')}" claim: $lbl'
              '${data['score'] != null ? ' (${data['score']})' : ''}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _GeneratedCopy extends StatefulWidget {
  const _GeneratedCopy({required this.result});
  final CatalogResult result;

  @override
  State<_GeneratedCopy> createState() => _GeneratedCopyState();
}

class _GeneratedCopyState extends State<_GeneratedCopy> {
  bool _hi = false;

  @override
  Widget build(BuildContext context) {
    final r = widget.result;
    return SectionCard(
      title: 'AI generated catalog',
      trailing: SegmentedButton<bool>(
        style: const ButtonStyle(visualDensity: VisualDensity.compact),
        segments: const [
          ButtonSegment(value: false, label: Text('EN')),
          ButtonSegment(value: true, label: Text('हिं')),
        ],
        selected: {_hi},
        onSelectionChanged: (v) => setState(() => _hi = v.first),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('SEO title',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 2),
          Text(r.seoTitle,
              style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 12),
          Text('Description',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 2),
          Text(_hi ? r.descriptionHi : r.descriptionEn,
              style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 12),
          Text('Keywords',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [for (final k in r.seoKeywords) Chip(label: Text(k))],
          ),
        ],
      ),
    );
  }
}
