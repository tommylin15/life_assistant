import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

class AttachmentService {
  AttachmentService({ImagePicker? imagePicker})
    : _imagePicker = imagePicker ?? ImagePicker();
  final ImagePicker _imagePicker;
  final _uuid = const Uuid();

  Future<File?> pickFile() async {
    final result = await FilePicker.platform.pickFiles();
    final path = result?.files.single.path;
    return path == null ? null : _store(File(path));
  }

  Future<File?> pickImage({bool camera = false}) async {
    final image = await _imagePicker.pickImage(
      source: camera ? ImageSource.camera : ImageSource.gallery,
    );
    return image == null ? null : _store(File(image.path));
  }

  Future<File> _store(File source) async {
    final root = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(root.path, 'attachments'));
    await dir.create(recursive: true);
    final extension = p.extension(source.path);
    return source.copy(p.join(dir.path, '${_uuid.v4()}$extension'));
  }

  Future<void> delete(String localPath) async {
    final root = await getApplicationDocumentsDirectory();
    final target = File(localPath);
    final allowed = p.isWithin(p.join(root.path, 'attachments'), target.path);
    if (!allowed)
      throw ArgumentError('Attachment path outside private storage');
    if (await target.exists()) await target.delete();
  }
}
