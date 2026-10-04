import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app/design_system/design_system.dart';
import 'browser_navigation.dart';
import 'drive_api.dart';

class NoteDriveRelations extends ConsumerStatefulWidget {
  const NoteDriveRelations({
    super.key,
    required this.noteId,
  });

  final String noteId;

  @override
  ConsumerState<NoteDriveRelations> createState() => _NoteDriveRelationsState();
}

class _NoteDriveRelationsState extends ConsumerState<NoteDriveRelations> {
  bool _loading = true;
  List<Map<String, dynamic>> _relations = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final values =
          await ref.read(driveNoteApiProvider).getNoteDocuments(widget.noteId);
      if (!mounted) return;
      setState(() {
        _relations = values;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _relations = const [];
        _loading = false;
      });
    }
  }

  Future<void> _open(String url) async {
    try {
      await ref.read(browserNavigationProvider).openExternal(url);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('無法開啟 Drive 原始文件：$error')),
      );
    }
  }

  Future<void> _unlink(String documentId, String name) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('解除 Drive 關聯？'),
        content: Text('解除與「$name」的相關文件關聯？Drive 原始文件不會被刪除。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('解除關聯'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      await ref
          .read(driveNoteApiProvider)
          .unlinkDocumentNote(documentId, widget.noteId);
      await _load();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('解除 Drive 關聯失敗：$error')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading || _relations.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        0,
        AppSpacing.sm,
        AppSpacing.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: _relations.map((relation) {
          final document =
              (relation['document'] as Map?)?.cast<String, dynamic>() ??
                  const <String, dynamic>{};
          final documentId = document['id']?.toString() ?? '';
          final rawName = document['name']?.toString().trim();
          final name = rawName == null || rawName.isEmpty ? '未命名文件' : rawName;
          final link = document['web_view_link']?.toString().trim() ?? '';
          final isSource = relation['relation_type'] == 'source_import';

          return Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    isSource
                        ? '來源：Google Drive · $name'
                        : '相關 Drive：$name',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
                if (link.isNotEmpty)
                  IconButton(
                    tooltip: isSource ? '開啟原始文件' : '在 Drive 開啟',
                    visualDensity: VisualDensity.compact,
                    onPressed: () => _open(link),
                    icon: const Icon(Icons.open_in_new, size: 18),
                  ),
                if (!isSource && documentId.isNotEmpty)
                  IconButton(
                    tooltip: '解除 Drive 關聯',
                    visualDensity: VisualDensity.compact,
                    onPressed: () => _unlink(documentId, name),
                    icon: const Icon(Icons.link_off, size: 18),
                  ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}
