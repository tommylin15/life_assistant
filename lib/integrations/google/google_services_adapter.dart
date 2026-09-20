import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:googleapis/calendar/v3.dart' as calendar;
import 'package:googleapis/drive/v3.dart' as drive;
import 'package:googleapis/gmail/v1.dart' as gmail;
import 'package:http/http.dart' as http;

import '../../data/folder_sync_engine.dart';

class GoogleServicesAdapter {
  static const calendarScope = 'https://www.googleapis.com/auth/calendar';
  static const gmailScope = 'https://www.googleapis.com/auth/gmail.readonly';
  static const driveScope = 'https://www.googleapis.com/auth/drive.file';
  static const folderSyncScope = 'https://www.googleapis.com/auth/drive';

  Future<bool> isSignedIn() => GoogleSignIn().isSignedIn();
  Future<void> disconnect() async {
    await GoogleSignIn().disconnect();
  }

  Future<_BearerClient> _client(List<String> scopes) async {
    final signIn = GoogleSignIn(scopes: scopes);
    final account = await signIn.signInSilently() ?? await signIn.signIn();
    if (account == null) throw StateError('GOOGLE_AUTH_REQUIRED');
    final auth = await account.authentication;
    if (auth.accessToken == null) throw StateError('GOOGLE_AUTH_REQUIRED');
    return _BearerClient(auth.accessToken!);
  }

  Future<List<calendar.Event>> readCalendar(DateTime from, DateTime to) async {
    final client = await _client([calendarScope]);
    try {
      final result = await calendar.CalendarApi(client).events.list(
        'primary',
        timeMin: from.toUtc(),
        timeMax: to.toUtc(),
        singleEvents: true,
        orderBy: 'startTime',
      );
      return result.items ?? const [];
    } finally {
      client.close();
    }
  }

  Future<calendar.Event> saveCalendarEvent(
    calendar.Event event, {
    String? eventId,
  }) async {
    final client = await _client([calendarScope]);
    try {
      final api = calendar.CalendarApi(client);
      return eventId == null
          ? api.events.insert(event, 'primary')
          : api.events.patch(event, 'primary', eventId);
    } finally {
      client.close();
    }
  }

  Future<void> deleteCalendarEvent(String eventId) async {
    final client = await _client([calendarScope]);
    try {
      await calendar.CalendarApi(client).events.delete('primary', eventId);
    } finally {
      client.close();
    }
  }

  Future<List<gmail.Message>> readGmailMetadata({int maxResults = 30}) async {
    final client = await _client([gmailScope]);
    try {
      final api = gmail.GmailApi(client);
      final refs = await api.users.messages.list(
        'me',
        maxResults: maxResults,
        q: 'newer_than:30d',
      );
      final messages = <gmail.Message>[];
      for (final ref in refs.messages ?? const <gmail.Message>[]) {
        if (ref.id != null)
          messages.add(
            await api.users.messages.get(
              'me',
              ref.id!,
              format: 'metadata',
              metadataHeaders: ['Subject', 'From', 'Date'],
            ),
          );
      }
      return messages;
    } finally {
      client.close();
    }
  }

  Future<String> ensureFolder(String name, {String? parentId}) async {
    final client = await _client([driveScope]);
    try {
      final api = drive.DriveApi(client);
      final escaped = name.replaceAll("'", "\\'");
      final parentQuery = parentId == null ? '' : " and '$parentId' in parents";
      final found = await api.files.list(
        q: "name='$escaped' and mimeType='application/vnd.google-apps.folder' and trashed=false$parentQuery",
        spaces: 'drive',
      );
      if (found.files?.isNotEmpty == true) return found.files!.first.id!;
      final created = await api.files.create(
        drive.File(
          name: name,
          mimeType: 'application/vnd.google-apps.folder',
          parents: parentId == null ? null : [parentId],
        ),
        $fields: 'id',
      );
      return created.id!;
    } finally {
      client.close();
    }
  }

  Future<void> writeJson(
    String folderId,
    String name,
    Map<String, Object?> value,
  ) async {
    return writeText(
      folderId,
      name,
      jsonEncode(value),
      contentType: 'application/json',
    );
  }

  Future<void> writeText(
    String folderId,
    String name,
    String value, {
    String contentType = 'text/plain',
  }) async {
    final client = await _client([driveScope]);
    try {
      final api = drive.DriveApi(client);
      final query = await api.files.list(
        q: "name='${name.replaceAll("'", "\\'")}' and '$folderId' in parents and trashed=false",
        spaces: 'drive',
      );
      final bytes = utf8.encode(value);
      final media = drive.Media(
        Stream.value(Uint8List.fromList(bytes)),
        bytes.length,
        contentType: contentType,
      );
      final metadata = drive.File(
        name: name,
        parents: [folderId],
        mimeType: contentType,
      );
      if (query.files?.isNotEmpty == true)
        await api.files.update(
          metadata,
          query.files!.first.id!,
          uploadMedia: media,
        );
      else
        await api.files.create(metadata, uploadMedia: media);
    } finally {
      client.close();
    }
  }

  Future<String?> readText(String folderId, String name) async {
    final client = await _client([driveScope]);
    try {
      final api = drive.DriveApi(client);
      final found = await api.files.list(
        q: "name='${name.replaceAll("'", "\\'")}' and '$folderId' in parents and trashed=false",
        spaces: 'drive',
      );
      if (found.files?.isEmpty != false) return null;
      final media = await api.files.get(
        found.files!.first.id!,
        downloadOptions: drive.DownloadOptions.fullMedia,
      ) as drive.Media;
      return utf8.decode(await media.stream.expand((e) => e).toList());
    } finally {
      client.close();
    }
  }
}

class GoogleDriveFileGateway implements DriveFileGateway {
  GoogleDriveFileGateway(this.google);
  final GoogleServicesAdapter google;

  @override
  Future<List<DriveFolderChoice>> listFolders() async {
    final client = await google._client([GoogleServicesAdapter.folderSyncScope]);
    try {
      final result = await drive.DriveApi(client).files.list(q: "mimeType='application/vnd.google-apps.folder' and trashed=false", spaces: 'drive', orderBy: 'name', $fields: 'files(id,name)');
      return (result.files ?? const <drive.File>[]).where((e) => e.id != null && e.name != null).map((e) => DriveFolderChoice(id: e.id!, name: e.name!)).toList();
    } finally { client.close(); }
  }

  @override
  Future<List<DriveFileEntry>> listFiles(String folderId) async {
    final client = await google._client([GoogleServicesAdapter.folderSyncScope]);
    try {
      final api = drive.DriveApi(client), result = <DriveFileEntry>[];
      await _walk(api, folderId, '', result);
      return result;
    } finally {
      client.close();
    }
  }

  Future<void> _walk(
    drive.DriveApi api,
    String folderId,
    String prefix,
    List<DriveFileEntry> out,
  ) async {
    String? token;
    do {
      final page = await api.files.list(
        q: "'$folderId' in parents and trashed=false",
        spaces: 'drive',
        pageToken: token,
        $fields:
            'nextPageToken,files(id,name,mimeType,modifiedTime,appProperties)',
      );
      for (final file in page.files ?? const <drive.File>[]) {
        if (file.id == null || file.name == null) continue;
        final path = prefix.isEmpty ? file.name! : '$prefix/${file.name!}';
        if (file.mimeType == 'application/vnd.google-apps.folder') {
          await _walk(api, file.id!, path, out);
        } else {
          var hash = file.appProperties?['sha256'];
          if (hash == null) {
            final media = await api.files.get(
              file.id!,
              downloadOptions: drive.DownloadOptions.fullMedia,
            ) as drive.Media;
            hash = sha256
                .convert(await media.stream.expand((e) => e).toList())
                .toString();
          }
          out.add(
            DriveFileEntry(
              id: file.id!,
              path: path,
              hash: hash,
              modifiedAt:
                  file.modifiedTime ?? DateTime.fromMillisecondsSinceEpoch(0),
              mimeType: file.mimeType,
            ),
          );
        }
      }
      token = page.nextPageToken;
    } while (token != null);
  }

  @override
  Future<List<int>> download(String fileId) async {
    final client = await google._client([GoogleServicesAdapter.folderSyncScope]);
    try {
      final media = await drive.DriveApi(client).files.get(
        fileId,
        downloadOptions: drive.DownloadOptions.fullMedia,
      ) as drive.Media;
      return media.stream.expand((e) => e).toList();
    } finally {
      client.close();
    }
  }

  @override
  Future<DriveFileEntry> upload(
    String folderId,
    String relativePath,
    List<int> bytes, {
    String? existingId,
  }) async {
    final client = await google._client([GoogleServicesAdapter.folderSyncScope]);
    try {
      final api = drive.DriveApi(client);
      final parts = relativePath.replaceAll('\\', '/').split('/');
      var parent = folderId;
      for (final segment in parts.take(parts.length - 1)) {
        parent = await _ensureFolder(api, parent, segment);
      }
      final hash = sha256.convert(bytes).toString();
      final metadata = drive.File(
        name: parts.last,
        parents: existingId == null ? [parent] : null,
        appProperties: {'sha256': hash},
      );
      final media = drive.Media(Stream.value(bytes), bytes.length);
      final result = existingId == null
          ? await api.files.create(
              metadata,
              uploadMedia: media,
              $fields: 'id,name,mimeType,modifiedTime',
            )
          : await api.files.update(
              metadata,
              existingId,
              uploadMedia: media,
              $fields: 'id,name,mimeType,modifiedTime',
            );
      return DriveFileEntry(
        id: result.id!,
        path: relativePath,
        hash: hash,
        modifiedAt: result.modifiedTime ?? DateTime.now(),
        mimeType: result.mimeType,
      );
    } finally {
      client.close();
    }
  }

  @override
  Future<DriveFileEntry> move(
    String folderId,
    String fileId,
    String relativePath,
  ) async {
    final client = await google._client([GoogleServicesAdapter.folderSyncScope]);
    try {
      final api = drive.DriveApi(client),
          parts = relativePath.replaceAll('\\', '/').split('/');
      var parent = folderId;
      for (final segment in parts.take(parts.length - 1)) {
        parent = await _ensureFolder(api, parent, segment);
      }
      final current = await api.files.get(
        fileId,
        $fields: 'parents,appProperties',
      ) as drive.File;
      final result = await api.files.update(
        drive.File(name: parts.last),
        fileId,
        addParents: parent,
        removeParents: current.parents?.join(','),
        $fields: 'id,name,mimeType,modifiedTime,appProperties',
      );
      var hash = result.appProperties?['sha256'] ?? current.appProperties?['sha256'];
      if (hash == null) {
        final media = await api.files.get(fileId, downloadOptions: drive.DownloadOptions.fullMedia) as drive.Media;
        hash = sha256.convert(await media.stream.expand((e) => e).toList()).toString();
      }
      return DriveFileEntry(
        id: result.id!,
        path: relativePath,
        hash: hash,
        modifiedAt: result.modifiedTime ?? DateTime.now(),
        mimeType: result.mimeType,
      );
    } finally {
      client.close();
    }
  }

  Future<String> _ensureFolder(
    drive.DriveApi api,
    String parent,
    String name,
  ) async {
    final escaped = name.replaceAll("'", "\\'");
    final found = await api.files.list(
      q: "name='$escaped' and '$parent' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
      spaces: 'drive',
    );
    if (found.files?.isNotEmpty == true) return found.files!.first.id!;
    return (await api.files.create(
      drive.File(
        name: name,
        parents: [parent],
        mimeType: 'application/vnd.google-apps.folder',
      ),
      $fields: 'id',
    )).id!;
  }

  @override
  Future<void> delete(String fileId) async {
    final client = await google._client([GoogleServicesAdapter.folderSyncScope]);
    try {
      await drive.DriveApi(client).files
          .update(drive.File(trashed: true), fileId);
    } finally {
      client.close();
    }
  }
}

class _BearerClient extends http.BaseClient {
  _BearerClient(this.token);
  final String token;
  final http.Client _inner = http.Client();
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    request.headers['Authorization'] = 'Bearer $token';
    return _inner.send(request);
  }

  @override
  void close() => _inner.close();
}
