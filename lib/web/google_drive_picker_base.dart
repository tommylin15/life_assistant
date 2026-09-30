abstract class GoogleDrivePicker {
  Future<List<String>> pickFiles({
    String? folderId,
    bool allowMultiple = true,
  });

  Future<String?> pickFolder();

  Future<void> openUrl(String url);
}
