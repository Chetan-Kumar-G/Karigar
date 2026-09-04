import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _pc = PageController();
  int _page = 0;

  static const _slides = [
    (
      icon: Icons.camera_alt_rounded,
      title: 'Better photos, automatically',
      body: 'Take one photo. We score it, fix the lighting and background, '
          'and tell you if it is good enough to sell.',
    ),
    (
      icon: Icons.mic_rounded,
      title: 'Just speak about your craft',
      body: 'Describe your product in your own language. We write the English '
          'and Hindi listing — and never invent claims you did not make.',
    ),
    (
      icon: Icons.payments_rounded,
      title: 'A fair price, every time',
      body: 'We suggest a price that always covers your material and labour '
          'cost — never below what your work is worth.',
    ),
    (
      icon: Icons.groups_rounded,
      title: 'Big orders, shared fairly',
      body: 'When a buyer needs thousands of pieces, we split the work across '
          'your cluster and share the payment fairly.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => context.go('/login'),
                child: const Text('Skip'),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _pc,
                onPageChanged: (i) => setState(() => _page = i),
                itemCount: _slides.length,
                itemBuilder: (_, i) {
                  final s = _slides[i];
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          width: 120,
                          height: 120,
                          decoration: BoxDecoration(
                            color: AppTheme.terracotta,
                            borderRadius: BorderRadius.circular(36),
                          ),
                          child: Icon(s.icon, size: 60, color: Colors.white),
                        ),
                        const SizedBox(height: 34),
                        Text(s.title,
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 14),
                        Text(s.body,
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodyLarge),
                      ],
                    ),
                  );
                },
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _slides.length,
                (i) => AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  margin: const EdgeInsets.all(4),
                  width: i == _page ? 22 : 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: i == _page ? AppTheme.terracotta : AppTheme.sand,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: ElevatedButton(
                onPressed: () {
                  if (_page < _slides.length - 1) {
                    _pc.nextPage(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.easeOut);
                  } else {
                    context.go('/login');
                  }
                },
                child: Text(_page < _slides.length - 1 ? 'Next' : 'Get started'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

