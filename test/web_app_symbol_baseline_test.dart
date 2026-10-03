import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/web_app.dart';

void main() {
  test('MorePage symbol constructs after importing web_app', () {
    const widget = MorePage();
    expect(widget, isA<Widget>());
  });
}
