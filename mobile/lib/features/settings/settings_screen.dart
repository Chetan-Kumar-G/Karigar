import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/app_config.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../providers/app_state.dart';
import '../../providers/product_flow.dart';
import '../../widgets/common.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _largeText = false;
  bool _voiceFirst = true;
  bool _draftPresent = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    setState(() {
      _largeText = p.getBool('pref_large_text') ?? false;
      _voiceFirst = p.getBool('pref_voice_first') ?? true;
      _draftPresent = p.getString('sih_product_draft') != null;
    });
  }

  Future<void> _set(String key, Object value) async {
    final p = await SharedPreferences.getInstance();
    if (value is bool) await p.setBool(key, value);
    if (value is String) await p.setString(key, value);
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final langProvider = context.watch<LocaleProvider>();
    final langName = kAppLanguages
        .firstWhere((l) => l.code == langProvider.code,
            orElse: () => kAppLanguages.first)
        .native;
    return Scaffold(
      appBar: AppBar(title: Text(tr('Settings'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SectionCard(
            title: tr('Language & accessibility'),
            child: Column(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.translate_rounded),
                  title: Text(tr('App language')),
                  subtitle: Text(langName),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => context.push('/language'),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(tr('Larger text')),
                  value: _largeText,
                  onChanged: (v) {
                    setState(() => _largeText = v);
                    _set('pref_large_text', v);
                  },
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(tr('Voice-first input')),
                  subtitle: const Text(
                      'Open the mic automatically when describing a product'),
                  value: _voiceFirst,
                  onChanged: (v) {
                    setState(() => _voiceFirst = v);
                    _set('pref_voice_first', v);
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: 'Offline',
            child: Column(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(
                    _draftPresent
                        ? Icons.cloud_off_rounded
                        : Icons.cloud_done_rounded,
                    color: _draftPresent ? AppTheme.ochre : AppTheme.leaf,
                  ),
                  title: Text(_draftPresent
                      ? 'You have an unfinished product draft'
                      : 'No pending offline work'),
                  trailing: _draftPresent
                      ? TextButton(
                          onPressed: () async {
                            final p = await SharedPreferences.getInstance();
                            await p.remove('sih_product_draft');
                            if (context.mounted) {
                              context.read<ProductFlow>().reset();
                              setState(() => _draftPresent = false);
                            }
                          },
                          child: const Text('Discard'),
                        )
                      : null,
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: tr('Demo & diagnostics'),
            child: Column(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.slideshow_rounded),
                  title: Text(tr('SIH Demo Mode')),
                  onTap: () => context.push('/demo'),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.insights_rounded),
                  title: Text(tr('AI System Insights (judge view)')),
                  onTap: () => context.push('/insights'),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.swap_horiz_rounded),
                  title: Text(app.isArtisan
                      ? tr('Switch to Buyer mode')
                      : tr('Switch to Artisan mode')),
                  onTap: () async {
                    await app.switchRole(app.isArtisan ? 'buyer' : 'artisan');
                    if (context.mounted) {
                      context.go(app.isArtisan ? '/home' : '/buyer');
                    }
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: tr('About'),
            child: Column(
              children: [
                const KeyValueRow('App', '${AppConfig.appName} · prototype 0.1'),
                KeyValueRow('Backend', AppConfig.apiBaseUrl),
                const KeyValueRow('Problem statement', 'SIH 26090'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
