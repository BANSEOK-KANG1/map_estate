import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:auction_insight_app/screens/beginner_guide_screen.dart';
import 'package:auction_insight_app/screens/home_screen.dart';
import 'package:auction_insight_app/screens/lot_detail_screen.dart';
import 'package:auction_insight_app/screens/settings_screen.dart';
import 'package:auction_insight_app/theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: AuctionInsightApp()));
}

final _router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
    GoRoute(
      path: '/lot/:id',
      builder: (context, state) {
        final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
        return LotDetailScreen(
          lotId: id,
          source: state.uri.queryParameters['source'],
          externalId: state.uri.queryParameters['ext'],
        );
      },
    ),
    GoRoute(
      path: '/settings',
      builder: (context, state) => const SettingsScreen(),
    ),
    GoRoute(
      path: '/guide',
      builder: (context, state) => const BeginnerGuideScreen(),
    ),
  ],
);

class AuctionInsightApp extends StatelessWidget {
  const AuctionInsightApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: '경공매 인사이트',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      routerConfig: _router,
    );
  }
}
