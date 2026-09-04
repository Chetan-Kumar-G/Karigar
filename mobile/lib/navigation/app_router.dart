import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/connection_screen.dart';
import '../features/auth/login_screen.dart';
import '../features/auth/onboarding_screen.dart';
import '../features/auth/splash_screen.dart';
import '../features/buyers/allocation_result_screen.dart';
import '../features/buyers/buyer_home_screen.dart';
import '../features/buyers/new_requirement_screen.dart';
import '../features/buyers/requirement_detail_screen.dart';
import '../features/copilot/copilot_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/demand/demand_screen.dart';
import '../features/demo/demo_screen.dart';
import '../features/insights/insights_screen.dart';
import '../features/inventory/inventory_screen.dart';
import '../features/marketplace/product_detail_screen.dart';
import '../features/marketplace/search_screen.dart';
import '../features/notifications/notifications_screen.dart';
import '../features/orders/orders_screen.dart';
import '../features/pricing/pricing_screen.dart';
import '../features/product_studio/catalog_preview_screen.dart';
import '../features/product_studio/create_product_screen.dart';
import '../features/product_studio/studio_screen.dart';
import '../features/product_studio/voice_screen.dart';
import '../features/craft_passport/passport_screen.dart';
import '../features/products/products_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/settings/language_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/trust/order_commitment_screen.dart';
import '../features/trust/report_issue_screen.dart';
import '../features/trust/reviewer_dashboard_screen.dart';
import '../features/trust/reviewer_detail_screen.dart';
import '../features/trust/trust_card_screen.dart';
import '../features/trust/verification_screen.dart';
import '../providers/app_state.dart';
import 'app_shell.dart';

class AppRouter {
  static GoRouter build(AppState app) {
    return GoRouter(
      initialLocation: '/splash',
      refreshListenable: app,
      redirect: (context, state) {
        final loc = state.matchedLocation;
        if (app.status == AuthStatus.unknown) {
          return loc == '/splash' ? null : '/splash';
        }
        final authed = app.signedIn;
        final atAuthGate = loc == '/splash' ||
            loc == '/onboarding' ||
            loc == '/login' ||
            loc == '/connection' ||
            loc == '/demo';
        if (!authed && !atAuthGate) return '/login';
        // '/splash' is intentionally excluded — SplashScreen controls its own
        // exit so the intro animation always plays.
        if (authed && loc == '/login') {
          return app.isArtisan ? '/home' : '/buyer';
        }
        return null;
      },
      routes: [
        GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
        GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingScreen()),
        GoRoute(path: '/connection', builder: (_, __) => const ConnectionScreen()),
        GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
        GoRoute(path: '/demo', builder: (_, __) => const DemoScreen()),

        // ── artisan shell (bottom nav) — 4 tabs + centre Add FAB ──
        StatefulShellRoute.indexedStack(
          builder: (_, __, shell) => AppShell(shell: shell),
          branches: [
            StatefulShellBranch(routes: [
              GoRoute(path: '/home', builder: (_, __) => const DashboardScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/products', builder: (_, __) => const ProductsScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/orders', builder: (_, __) => const OrdersScreen()),
            ]),
            StatefulShellBranch(routes: [
              GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
            ]),
          ],
        ),

        // Marketplace / discovery — reached from the dashboard, not a bottom tab.
        GoRoute(path: '/market', builder: (_, __) => const SearchScreen()),

        // ── product creation flow ──
        GoRoute(path: '/create', builder: (_, __) => const CreateProductScreen()),
        GoRoute(
            path: '/studio/:id',
            builder: (_, s) => StudioScreen(productId: s.pathParameters['id']!)),
        GoRoute(
            path: '/voice/:id',
            builder: (_, s) => VoiceScreen(productId: s.pathParameters['id']!)),
        GoRoute(
            path: '/passport/:id',
            builder: (_, s) => PassportScreen(
                  productId: s.pathParameters['id']!,
                  inFlow: (s.extra as Map?)?['inFlow'] as bool? ?? true,
                )),
        GoRoute(
            path: '/pricing/:id',
            builder: (_, s) => PricingScreen(
                  productId: s.pathParameters['id']!,
                  inFlow: (s.extra as Map?)?['inFlow'] as bool? ?? true,
                )),
        GoRoute(
            path: '/preview/:id',
            builder: (_, s) =>
                CatalogPreviewScreen(productId: s.pathParameters['id']!)),
        GoRoute(
            path: '/product/:id',
            builder: (_, s) =>
                ProductDetailScreen(productId: s.pathParameters['id']!)),

        // ── trust & verification ──
        GoRoute(
            path: '/verification',
            builder: (_, __) => const VerificationScreen()),
        GoRoute(
            path: '/reviewer',
            builder: (_, __) => const ReviewerDashboardScreen()),
        GoRoute(
            path: '/reviewer/:id',
            builder: (_, s) =>
                ReviewerDetailScreen(profileId: s.pathParameters['id']!)),
        GoRoute(
            path: '/trust/artisan/:id',
            builder: (_, s) =>
                TrustCardScreen(subjectId: s.pathParameters['id']!)),
        GoRoute(
            path: '/trust/business/:id',
            builder: (_, s) => TrustCardScreen(
                subjectId: s.pathParameters['id']!, isBusiness: true)),
        GoRoute(
            path: '/report/:artisanId',
            builder: (_, s) => ReportIssueScreen(
                  artisanId: s.pathParameters['artisanId']!,
                  artisanName: (s.extra as Map?)?['artisanName'] as String?,
                  orderId: (s.extra as Map?)?['orderId'] as String?,
                )),
        GoRoute(
            path: '/order-commitment/:orderId',
            builder: (_, s) => OrderCommitmentScreen(
                orderId: s.pathParameters['orderId']!)),

        // ── standalone artisan tools ──
        GoRoute(path: '/demand', builder: (_, __) => const DemandScreen()),
        GoRoute(path: '/copilot', builder: (_, __) => const CopilotScreen()),
        GoRoute(path: '/insights', builder: (_, __) => const InsightsScreen()),
        GoRoute(path: '/inventory', builder: (_, __) => const InventoryScreen()),
        GoRoute(
            path: '/notifications',
            builder: (_, __) => const NotificationsScreen()),
        GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
        GoRoute(path: '/language', builder: (_, __) => const LanguageScreen()),

        // ── buyer flow ──
        GoRoute(path: '/buyer', builder: (_, __) => const BuyerHomeScreen()),
        GoRoute(
            path: '/buyer/requirement/:id',
            builder: (_, s) =>
                RequirementDetailScreen(requirementId: s.pathParameters['id']!)),
        GoRoute(
            path: '/buyer/new', builder: (_, __) => const NewRequirementScreen()),
        GoRoute(
            path: '/buyer/allocation/:orderId',
            builder: (_, s) => AllocationResultScreen(
                orderId: s.pathParameters['orderId']!)),
      ],
      errorBuilder: (_, state) => Scaffold(
        appBar: AppBar(title: const Text('Not found')),
        body: Center(child: Text('No screen for ${state.uri}')),
      ),
    );
  }
}
