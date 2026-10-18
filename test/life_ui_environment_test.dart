import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/life_ui_environment.dart';

void main() {
  test('only staging and its Preview channels show developer information', () {
    expect(LifeUiEnvironment.isCandidateHost('life-assistant-v3-stage-tl15.web.app'), isTrue);
    expect(LifeUiEnvironment.isCandidateHost('life-assistant-v3-stage-tl15--sha123.web.app'), isTrue);
    expect(LifeUiEnvironment.isCandidateHost('gen-lang-client-0593591102.web.app'), isFalse);
    expect(LifeUiEnvironment.isCandidateHost('life-assistant-v3-stage-tl15.web.app.evil.test'), isFalse);
  });
}
