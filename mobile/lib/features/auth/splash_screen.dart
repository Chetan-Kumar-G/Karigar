import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/app_config.dart';
import '../../core/theme.dart';
import '../../providers/app_state.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  static const _name = AppConfig.appName; // "Kārigar" — keeps the macron on ā

  // types the name out one character at a time
  late final AnimationController _typeCtrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );
  late final Animation<int> _chars = StepTween(begin: 0, end: _name.length)
      .animate(CurvedAnimation(parent: _typeCtrl, curve: Curves.easeOut));

  // blinking caret while typing
  late final AnimationController _caretCtrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 550),
  )..repeat(reverse: true);

  bool _navigated = false;

  @override
  void initState() {
    super.initState();
    _typeCtrl.forward();
    _bootAndGo();
  }

  Future<void> _bootAndGo() async {
    final app = context.read<AppState>();
    // let the intro animation finish, then wait for bootstrap to settle
    await Future<void>.delayed(const Duration(milliseconds: 1900));
    while (mounted && app.status == AuthStatus.unknown) {
      await Future<void>.delayed(const Duration(milliseconds: 100));
    }
    // Wait (bounded) for the health probe kicked off in bootstrap() to resolve.
    // The probe itself retries a cold backend, so give it room; if it still
    // hasn't settled, fall through to the connection screen rather than hang.
    var waited = 0;
    while (mounted &&
        waited < 28000 &&
        (app.conn == ConnStatus.unknown || app.conn == ConnStatus.checking)) {
      await Future<void>.delayed(const Duration(milliseconds: 100));
      waited += 100;
    }
    if (!mounted || _navigated) return;
    _navigated = true;
    if (app.conn == ConnStatus.online && app.status == AuthStatus.signedIn) {
      context.go(app.isArtisan ? '/home' : '/buyer');
    } else if (app.conn == ConnStatus.online) {
      context.go('/onboarding');
    } else {
      // offline, or the probe never settled — let the user retry / fix the URL
      context.go('/connection');
    }
  }

  @override
  void dispose() {
    _typeCtrl.dispose();
    _caretCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.terracotta,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 148,
              height: 148,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(28),
              ),
              child: Image.asset(
                'assets/logo.png',
                fit: BoxFit.contain,
                errorBuilder: (context, _, __) => const Icon(
                    Icons.spa_rounded,
                    size: 52,
                    color: AppTheme.terracotta),
              ),
            ),
            const SizedBox(height: 22),
            AnimatedBuilder(
              animation: Listenable.merge([_typeCtrl, _caretCtrl]),
              builder: (context, _) {
                final shown = _name.substring(0, _chars.value);
                final typing = _chars.value < _name.length;
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      shown,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 32,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.5,
                      ),
                    ),
                    Opacity(
                      opacity: typing
                          ? _caretCtrl.value
                          : (1 - _typeCtrl.value).clamp(0.0, 1.0),
                      child: Container(
                        width: 3,
                        height: 30,
                        margin: const EdgeInsets.only(left: 3, bottom: 2),
                        color: Colors.white,
                      ),
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: 6),
            Text(AppConfig.appTagline,
                style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.9), fontSize: 15)),
            const SizedBox(height: 34),
            const SizedBox(
              width: 26,
              height: 26,
              child: CircularProgressIndicator(
                  strokeWidth: 2.5, color: Colors.white),
            ),
          ],
        ),
      ),
    );
  }
}
