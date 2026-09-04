import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/theme.dart';
import '../l10n/i18n.dart';
import '../providers/app_state.dart';

/// Bottom-navigation shell for the artisan (spec §24). The centre "Add" action
/// is a prominent FAB that launches the product-creation flow.
class AppShell extends StatelessWidget {
  const AppShell({required this.shell, super.key});
  final StatefulNavigationShell shell;

  // 4 tabs so the centre-docked Add FAB sits in the true middle (2 | FAB | 2).
  static const _items = [
    (icon: Icons.home_rounded, label: 'Home'),
    (icon: Icons.grid_view_rounded, label: 'Products'),
    (icon: Icons.local_shipping_rounded, label: 'Orders'),
    (icon: Icons.person_rounded, label: 'Profile'),
  ];

  void _go(int i) => shell.goBranch(i, initialLocation: i == shell.currentIndex);

  @override
  Widget build(BuildContext context) {
    final isArtisan = context.select<AppState, bool>((s) => s.isArtisan);

    return Scaffold(
      body: shell,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: isArtisan
          ? FloatingActionButton(
              heroTag: 'add-product',
              onPressed: () => context.push('/create'),
              backgroundColor: AppTheme.terracotta,
              foregroundColor: Colors.white,
              elevation: 2,
              child: const Icon(Icons.add_a_photo_rounded, size: 26),
            )
          : null,
      bottomNavigationBar: BottomAppBar(
        color: Colors.white,
        elevation: 8,
        height: 64,
        padding: EdgeInsets.zero,
        shape: isArtisan ? const CircularNotchedRectangle() : null,
        notchMargin: 8,
        child: Row(
          children: [
            for (var i = 0; i < _items.length; i++) ...[
              if (isArtisan && i == 2) const SizedBox(width: 72),
              Expanded(
                child: _NavButton(
                  icon: _items[i].icon,
                  label: tr(_items[i].label),
                  selected: shell.currentIndex == i,
                  onTap: () => _go(i),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = selected ? AppTheme.terracotta : AppTheme.inkSoft;
    return InkWell(
      onTap: onTap,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: c, size: 24),
          const SizedBox(height: 2),
          Text(label,
              style: TextStyle(
                  color: c,
                  fontSize: 11,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600)),
        ],
      ),
    );
  }
}
