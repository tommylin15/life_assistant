import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_state.dart';
import 'life_ui_environment.dart';
import 'platform_api.dart';
import 'release_info.dart';

class ReleaseNotesPage extends ConsumerStatefulWidget {
  const ReleaseNotesPage({super.key});

  @override
  ConsumerState<ReleaseNotesPage> createState() => _ReleaseNotesPageState();
}

class _ReleaseNotesPageState extends ConsumerState<ReleaseNotesPage> {
  String? _markedToken;

  @override
  Widget build(BuildContext context) {
    final featuresAsync = ref.watch(effectiveFeaturesProvider);
    final backendAsync = ref.watch(backendReleaseNotesProvider);
    final notes = releaseNotesFor(lifeAppVersion,
      features: featuresAsync.asData?.value,
      backendNotes: backendAsync.asData?.value ?? const []);
    final email = ref.watch(authProvider).asData?.value?['email'];
    final token = releaseReadToken(notes);
    // Do not mark a partial feed as fully read during initial loading.
    if (!featuresAsync.isLoading && !backendAsync.isLoading &&
        token != null && token != _markedToken) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || token == _markedToken) return;
        markReleaseNotesRead(email, notes);
        _markedToken = token;
        ref.read(releaseNotesReadRevisionProvider.notifier).state++;
      });
    }

    final candidate = LifeUiEnvironment.isCandidate;
    return Scaffold(
      appBar: AppBar(title: const Text('最新消息')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            '目前版本：$lifeVersionLabel${candidate ? '（候選版）' : ''}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          if (candidate && lifeReleaseSha.length >= 8) ...[
            const SizedBox(height: 4),
            Text('測試版識別碼：${lifeReleaseSha.substring(0, 8)}',
                style: Theme.of(context).textTheme.bodySmall),
          ],
          const SizedBox(height: 12),
          if (notes.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Text('目前沒有可顯示的更新公告。'),
            ),
          for (final note in notes)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${note.version == null ? '維護更新' : 'v${note.version}'}  ${note.title}',
                        style: Theme.of(context).textTheme.titleMedium),
                    if (note.publishedOn != null) ...[
                      const SizedBox(height: 4),
                      Text(note.publishedOn!,
                          style: Theme.of(context).textTheme.bodySmall),
                    ],
                    const SizedBox(height: 12),
                    for (final change in note.changes)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.check_circle_outline, size: 18),
                            const SizedBox(width: 8),
                            Expanded(child: Text(change)),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
