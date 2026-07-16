import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:map_estate_app/screens/complex_detail_screen.dart';
import 'package:map_estate_app/screens/home_screen.dart';
import 'package:map_estate_app/screens/settings_screen.dart';
import 'package:map_estate_app/theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: MapEstateApp()));
}

final _router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
    GoRoute(
      path: '/complex/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id']!);
        return ComplexDetailScreen(complexId: id);
      },
    ),
    GoRoute(
      path: '/settings',
      builder: (context, state) => const SettingsScreen(),
    ),
  ],
);

class MapEstateApp extends StatelessWidget {
  const MapEstateApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Map Estate',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      routerConfig: _router,
    );
  }
}
