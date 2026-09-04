import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/app_config.dart';
import '../core/theme.dart';

/// Rounded, outlined content card (spec §23).
class SectionCard extends StatelessWidget {
  const SectionCard({
    required this.child,
    this.title,
    this.trailing,
    this.padding = const EdgeInsets.all(16),
    super.key,
  });
  final Widget child;
  final String? title;
  final Widget? trailing;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: padding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (title != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(title!,
                          style: Theme.of(context).textTheme.titleMedium),
                    ),
                    if (trailing != null) trailing!,
                  ],
                ),
              ),
            child,
          ],
        ),
      ),
    );
  }
}

/// Small labelled pill used for attributes / chips.
class InfoPill extends StatelessWidget {
  const InfoPill(this.label, {this.icon, this.color, super.key});
  final String label;
  final IconData? icon;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? AppTheme.indigo;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: c.withValues(alpha: 0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 15, color: c),
            const SizedBox(width: 6),
          ],
          Text(label,
              style: TextStyle(
                  color: c, fontWeight: FontWeight.w700, fontSize: 13)),
        ],
      ),
    );
  }
}

/// REAL / PROTOTYPE / SIMULATED_DATA / FALLBACK honesty badge (spec §49).
class ModeBadge extends StatelessWidget {
  const ModeBadge(this.mode, {super.key});
  final String mode;

  @override
  Widget build(BuildContext context) {
    final m = mode.toUpperCase();
    final color = m.contains('REAL')
        ? AppTheme.leaf
        : m.contains('SIMULATED')
            ? AppTheme.ochre
            : m.contains('FALLBACK')
                ? AppTheme.inkSoft
                : AppTheme.indigoLight;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(m,
          style: TextStyle(
              fontSize: 10, fontWeight: FontWeight.w800, color: color, letterSpacing: 0.4)),
    );
  }
}

class LoadingView extends StatelessWidget {
  const LoadingView({this.label = 'Loading…', super.key});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(strokeWidth: 3),
          const SizedBox(height: 16),
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class ErrorView extends StatelessWidget {
  const ErrorView(this.error, {this.onRetry, super.key});
  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final isNet = error is ApiException && (error as ApiException).isNetwork;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(isNet ? Icons.wifi_off_rounded : Icons.error_outline_rounded,
                size: 46, color: AppTheme.terracotta),
            const SizedBox(height: 14),
            Text(
              '$error',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 18),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Try again'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class EmptyView extends StatelessWidget {
  const EmptyView({
    required this.title,
    this.message,
    this.icon = Icons.inbox_rounded,
    this.action,
    super.key,
  });
  final String title;
  final String? message;
  final IconData icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 78,
              height: 78,
              decoration: BoxDecoration(
                color: AppTheme.sand,
                borderRadius: BorderRadius.circular(24),
              ),
              child: Icon(icon, size: 38, color: AppTheme.inkSoft),
            ),
            const SizedBox(height: 16),
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            if (message != null) ...[
              const SizedBox(height: 6),
              Text(message!,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium),
            ],
            if (action != null) ...[const SizedBox(height: 18), action!],
          ],
        ),
      ),
    );
  }
}

/// Network image with graceful placeholder + error fallback.
class RemoteImage extends StatelessWidget {
  const RemoteImage(this.path,
      {this.height, this.width, this.fit = BoxFit.cover, this.radius = 14, super.key});
  final String? path;
  final double? height;
  final double? width;
  final BoxFit fit;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final url = AppConfig.media(path);
    Widget ph(IconData i) => Container(
          height: height,
          width: width,
          color: AppTheme.sand,
          child: Icon(i, color: AppTheme.inkSoft, size: 34),
        );
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: url.isEmpty
          ? ph(Icons.image_outlined)
          : Image.network(
              url,
              height: height,
              width: width,
              fit: fit,
              loadingBuilder: (c, w, p) =>
                  p == null ? w : ph(Icons.image_outlined),
              errorBuilder: (c, e, s) => ph(Icons.broken_image_outlined),
            ),
    );
  }
}

/// Full-width label + value row.
class KeyValueRow extends StatelessWidget {
  const KeyValueRow(this.k, this.v, {this.strong = false, super.key});
  final String k;
  final String v;
  final bool strong;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 128,
            child: Text(k,
                style: const TextStyle(
                    color: AppTheme.inkSoft, fontWeight: FontWeight.w600)),
          ),
          Expanded(
            child: Text(v,
                style: TextStyle(
                    fontWeight: strong ? FontWeight.w800 : FontWeight.w600,
                    color: AppTheme.ink)),
          ),
        ],
      ),
    );
  }
}

SnackBar appSnack(String message, {bool danger = false}) => SnackBar(
      content: Text(message),
      backgroundColor: danger ? AppTheme.danger : AppTheme.ink,
    );
