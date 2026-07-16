import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:map_estate_app/theme.dart';

void main() {
  testWidgets('Theme builds a MaterialApp shell', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: const Scaffold(
          body: Center(child: Text('Map Estate')),
        ),
      ),
    );
    expect(find.text('Map Estate'), findsOneWidget);
  });
}
