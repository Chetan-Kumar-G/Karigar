import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';

/// Language picker — all 22 Eighth-Schedule languages + English.
/// Languages without a full dictionary yet fall back to English and are marked.
class LanguageScreen extends StatelessWidget {
  const LanguageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<LocaleProvider>();
    return Scaffold(
      appBar: AppBar(title: Text(tr('Choose your language'))),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          Text(tr('App language'),
              style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          for (final lang in kAppLanguages)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: _LangTile(
                code: lang.code,
                english: lang.english,
                native: lang.native,
                filled: lang.filled,
                selected: provider.code == lang.code,
                onTap: () => provider.setLanguage(lang.code),
              ),
            ),
          const SizedBox(height: 8),
          Text(
            'Languages marked “English for now” are listed but not yet fully '
            'translated — the app stays in English until a translation is added.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _LangTile extends StatelessWidget {
  const _LangTile({
    required this.code,
    required this.english,
    required this.native,
    required this.filled,
    required this.selected,
    required this.onTap,
  });
  final String code;
  final String english;
  final String native;
  final bool filled;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? AppTheme.terracotta.withValues(alpha: 0.10) : Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
                color: selected ? AppTheme.terracotta : AppTheme.line,
                width: selected ? 1.6 : 1),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(native,
                        style: const TextStyle(
                            fontWeight: FontWeight.w800, fontSize: 16)),
                    const SizedBox(height: 2),
                    Text(
                      filled ? english : '$english · English for now',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              if (selected)
                const Icon(Icons.check_circle_rounded,
                    color: AppTheme.terracotta),
            ],
          ),
        ),
      ),
    );
  }
}
