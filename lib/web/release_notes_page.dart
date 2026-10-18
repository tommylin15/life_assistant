import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_state.dart';
import 'life_ui_environment.dart';
import 'release_info.dart';

class ReleaseNotesPage extends ConsumerStatefulWidget {
  const ReleaseNotesPage({super.key});

  @override
  ConsumerState<ReleaseNotesPage> createState() => _ReleaseNotesPageState();
}

class _ReleaseNotesPageState extends ConsumerState<ReleaseNotesPage> {
  @override
  void initState() {
    super.initState();
    // Mark on opening the page, never simply because the user logged in.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      markReleaseNotesRead(ref.read(authProvider).asData?.value?['email']);
    });
  }

  @override
  Widget build(BuildContext context) {
    final notes = releaseNotesFor(lifeAppVersion);
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
                    Text('v${note.version}  ${note.title}',
                        style: Theme.of(context).textTheme.titleMedium),
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
