import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'core/app_config.dart';
import 'core/theme.dart';
import 'l10n/i18n.dart';
import 'navigation/app_router.dart';
import 'providers/app_state.dart';
import 'providers/product_flow.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Pick up any device-local server-address override before the first request.
  await AppConfig.loadOverride();
  runApp(const ArtisanMarketApp());
}

class ArtisanMarketApp extends StatelessWidget {
  const ArtisanMarketApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => LocaleProvider()..load()),
        ChangeNotifierProvider(create: (_) => AppState()..bootstrap()),
        ChangeNotifierProxyProvider<AppState, ProductFlow>(
          create: (ctx) => ProductFlow(ctx.read<AppState>().api),
          update: (ctx, app, prev) => prev ?? ProductFlow(app.api),
        ),
      ],
      child: Builder(
        builder: (context) {
          final router = AppRouter.build(context.read<AppState>());
          // Rebuilds the whole tree on language change so every tr(...) re-evaluates.
          return Consumer<LocaleProvider>(
            builder: (context, l10n, _) => MaterialApp.router(
              title: 'Kārigar — Artisan Market',
              debugShowCheckedModeBanner: false,
              theme: AppTheme.light(),
              routerConfig: router,
              locale: l10n.materialLocale,
              supportedLocales: l10n.supportedLocales,
              localizationsDelegates: const [
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
            ),
          );
        },
      ),
    );
  }
}
