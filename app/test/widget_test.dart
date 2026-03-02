import 'package:flutter_test/flutter_test.dart';
import 'package:doohub/main.dart';

void main() {
  testWidgets('App renders', (WidgetTester tester) async {
    await tester.pumpWidget(const DooHubApp());
    expect(find.text('DooHub'), findsAny);
  });
}
