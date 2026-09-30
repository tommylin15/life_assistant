(() => {
  const DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.file';
  let pickerReadyPromise;

  function waitFor(predicate, label, timeoutMs = 10000) {
    const startedAt = Date.now();
    return new Promise((resolve, reject) => {
      const check = () => {
        if (predicate()) {
          resolve();
          return;
        }
        if (Date.now() - startedAt >= timeoutMs) {
          reject(new Error(`${label} did not load`));
          return;
        }
        setTimeout(check, 50);
      };
      check();
    });
  }

  async function ensurePickerReady() {
    if (!pickerReadyPromise) {
      pickerReadyPromise = (async () => {
        await waitFor(() => window.gapi && window.google, 'Google APIs');
        await waitFor(
          () => window.google.accounts && window.google.accounts.oauth2,
          'Google Identity Services',
        );
        await new Promise((resolve, reject) => {
          window.gapi.load('picker', {
            callback: resolve,
            onerror: () => reject(new Error('Google Picker failed to load')),
            timeout: 10000,
            ontimeout: () => reject(new Error('Google Picker load timed out')),
          });
        });
      })().catch((error) => {
        pickerReadyPromise = undefined;
        throw error;
      });
    }
    return pickerReadyPromise;
  }

  function requestDriveToken(clientId, scope) {
    if (scope !== DRIVE_SCOPE) {
      return Promise.reject(new Error('Unexpected Google Picker scope'));
    }
    return new Promise((resolve, reject) => {
      let settled = false;
      const client = window.google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope,
        callback: (response) => {
          if (settled) return;
          settled = true;
          if (response && response.access_token) {
            resolve(response.access_token);
            return;
          }
          reject(new Error(response?.error || 'Google Drive authorization failed'));
        },
        error_callback: (error) => {
          if (settled) return;
          settled = true;
          reject(new Error(error?.type || 'Google Drive authorization failed'));
        },
      });
      client.requestAccessToken({prompt: ''});
    });
  }

  async function showPicker({
    clientId,
    developerKey,
    appId,
    scope,
    folderId,
    allowMultiple,
    folderMode,
  }) {
    await ensurePickerReady();
    const token = await requestDriveToken(clientId, scope);

    return new Promise((resolve) => {
      const view = new window.google.picker.DocsView(
        folderMode
          ? window.google.picker.ViewId.FOLDERS
          : window.google.picker.ViewId.DOCS,
      );
      view.setMode(window.google.picker.DocsViewMode.LIST);
      if (folderMode) {
        view.setIncludeFolders(true);
        view.setSelectFolderEnabled(true);
      } else {
        view.setIncludeFolders(false);
        if (folderId) view.setParent(folderId);
      }

      const builder = new window.google.picker.PickerBuilder()
        .addView(view)
        .setOAuthToken(token)
        .setDeveloperKey(developerKey)
        .setAppId(appId)
        .setCallback((data) => {
          if (data.action === window.google.picker.Action.PICKED) {
            const ids = (data.docs || [])
              .map((doc) => doc.id)
              .filter((id) => typeof id === 'string' && id.length > 0);
            resolve(ids);
          } else if (data.action === window.google.picker.Action.CANCEL) {
            resolve([]);
          }
        });
      if (allowMultiple && !folderMode) {
        builder.enableFeature(window.google.picker.Feature.MULTISELECT_ENABLED);
      }
      builder.build().setVisible(true);
    });
  }

  window.lifeAssistantPickDriveFiles = async (
    clientId,
    developerKey,
    appId,
    scope,
    folderId,
    allowMultiple,
  ) => showPicker({
    clientId,
    developerKey,
    appId,
    scope,
    folderId,
    allowMultiple,
    folderMode: false,
  });

  window.lifeAssistantPickDriveFolder = async (
    clientId,
    developerKey,
    appId,
    scope,
  ) => {
    const ids = await showPicker({
      clientId,
      developerKey,
      appId,
      scope,
      folderId: '',
      allowMultiple: false,
      folderMode: true,
    });
    return ids[0] || '';
  };

  window.lifeAssistantOpenExternalUrl = (url) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };
})();
