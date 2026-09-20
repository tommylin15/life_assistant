import 'package:speech_to_text/speech_to_text.dart';

class SpeechAdapter {
  SpeechAdapter({SpeechToText? speech}) : _speech = speech ?? SpeechToText();
  final SpeechToText _speech;

  Future<bool> initialize() => _speech.initialize();
  bool get isListening => _speech.isListening;

  Future<void> listen(void Function(String words, bool finalResult) onResult) =>
      _speech.listen(
        listenOptions: SpeechListenOptions(
          localeId: 'zh_TW',
          partialResults: true,
          cancelOnError: true,
        ),
        onResult: (result) =>
            onResult(result.recognizedWords, result.finalResult),
      );

  Future<void> stop() => _speech.stop();
}
