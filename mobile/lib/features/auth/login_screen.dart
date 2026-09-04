import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../widgets/common.dart';
import '../../providers/app_state.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phone = TextEditingController(text: '9800000001');
  final _otp = TextEditingController();
  String _role = 'artisan';
  bool _otpSent = false;
  bool _busy = false;
  String? _error;
  String _mockOtp = '123456';

  @override
  void dispose() {
    _phone.dispose();
    _otp.dispose();
    super.dispose();
  }

  Future<void> _sendOtp() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final res =
          await context.read<AppState>().api.requestOtp(_phone.text.trim(), _role);
      setState(() {
        _otpSent = true;
        _mockOtp = '${res['mock_otp'] ?? '123456'}';
        _otp.text = _mockOtp;
      });
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final s = await context
          .read<AppState>()
          .signIn(_phone.text.trim(), _otp.text.trim(), _role);
      if (!mounted) return;
      context.go(s.role == 'buyer' ? '/buyer' : '/home');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: () => context.push('/language'),
                  icon: const Icon(Icons.translate_rounded, size: 18),
                  label: Text(tr('Language')),
                ),
              ),
              const SizedBox(height: 8),
              const Icon(Icons.spa_rounded, size: 46, color: AppTheme.terracotta),
              const SizedBox(height: 14),
              Text(tr('Sign in'),
                  style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 6),
              Text('Use your phone number. We will send a one-time code.',
                  style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 24),
              SegmentedButton<String>(
                segments: [
                  ButtonSegment(
                      value: 'artisan',
                      label: Text(tr('Artisan')),
                      icon: const Icon(Icons.handyman_rounded)),
                  ButtonSegment(
                      value: 'buyer',
                      label: Text(tr('Buyer')),
                      icon: const Icon(Icons.business_center_rounded)),
                ],
                selected: {_role},
                onSelectionChanged: (v) => setState(() {
                  _role = v.first;
                  _phone.text =
                      _role == 'buyer' ? '9900000001' : '9800000001';
                  _otpSent = false;
                }),
              ),
              const SizedBox(height: 20),
              TextField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(10),
                ],
                decoration: InputDecoration(
                  labelText: tr('Phone number'),
                  prefixIcon: const Icon(Icons.phone_rounded),
                  prefixText: '+91  ',
                ),
              ),
              const SizedBox(height: 14),
              if (_otpSent)
                TextField(
                  controller: _otp,
                  keyboardType: TextInputType.number,
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    LengthLimitingTextInputFormatter(6),
                  ],
                  decoration: InputDecoration(
                    labelText: 'One-time code',
                    helperText: 'Prototype code: $_mockOtp',
                    prefixIcon: const Icon(Icons.lock_rounded),
                  ),
                ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!,
                    style: const TextStyle(
                        color: AppTheme.danger, fontWeight: FontWeight.w600)),
              ],
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _busy
                    ? null
                    : _otpSent
                        ? _verify
                        : _sendOtp,
                child: _busy
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(
                            strokeWidth: 2.4, color: Colors.white))
                    : Text(_otpSent ? tr('Verify') : tr('Send OTP')),
              ),
              const SizedBox(height: 10),
              TextButton.icon(
                onPressed: () => context.go('/demo'),
                icon: const Icon(Icons.slideshow_rounded),
                label: Text(tr('Open SIH Demo Mode')),
              ),
              const SizedBox(height: 10),
              const _DemoAccountsHint(),
            ],
          ),
        ),
      ),
    );
  }
}

class _DemoAccountsHint extends StatelessWidget {
  const _DemoAccountsHint();

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      padding: const EdgeInsets.all(14),
      child: DefaultTextStyle(
        style: Theme.of(context).textTheme.bodyMedium!,
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Demo accounts  ·  OTP 123456 for all',
                style: TextStyle(
                    fontWeight: FontWeight.w800, color: AppTheme.ink)),
            SizedBox(height: 6),
            Text('Artisan  ·  9800000001  (Meera, Madhubani)'),
            Text('Buyer    ·  9900000001  (Meridian Hotels)'),
            SizedBox(height: 8),
            Text('Thanjavur cluster walkthrough',
                style: TextStyle(
                    fontWeight: FontWeight.w800, color: AppTheme.ink)),
            SizedBox(height: 4),
            Text('Buyers   ·  Agneay 9600000001 · Cynthiya 9600000002 · '
                'Prarthana 9600000003'),
            Text('Artisans ·  Chetan 9700000001 · Prasannaa 9700000002 · '
                'Deeraj 9700000003'),
            SizedBox(height: 4),
            Text('Agneay → "Thanjavur art plates" requirement → Find Artisan '
                'Cluster → splits across all three → confirm → log in as '
                'Prasannaa to see the order.',
                style: TextStyle(fontSize: 12.5, color: AppTheme.inkSoft)),
          ],
        ),
      ),
    );
  }
}
