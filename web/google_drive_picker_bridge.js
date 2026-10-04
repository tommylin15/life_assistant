(() => {
  'use strict';

  const DRIVE_FILE_SCOPE = 'https://www.googleapis.com/auth/drive.file';
  const LOAD_TIMEOUT_MS = 10000;
  let pickerLibraryPromise;

  function waitFor(check, label) {
    return new Promise((resolve, reject) => {
      const started = Date.now();
      const poll = () => {
        if (check()) {
          resolve();
          return;
        }
        if (Date.now() - started >= LOAD_TIMEOUT_MS) {
          reject(new Error(`${label} did not load.`));
          return;
        }
        window.setTimeout(poll, 50);
      };
      poll();
    });
  }

  async function loadPickerLibrary() {
    if (!pickerLibraryPromise) {
      pickerLibraryPromise = (async () => {
        await waitFor(() => typeof window.gapi !== 'undefined', 'Google API');
        await new Promise((resolve, reject) => {
          window.gapi.load('picker', {
            callback: resolve,
            onerror: () => reject(new Error('Google Picker library failed to load.')),
            timeout: LOAD_TIMEOUT_MS,
            ontimeout: () => reject(new Error('Google Picker library timed out.')),
          });
        });
      })();
    }
    return pickerLibraryPromise;
  }

  async function requestDriveFileToken(clientId, scope) {
    if (scope !== DRIVE_FILE_SCOPE) {
      throw new Error('Google Drive Picker must use the drive.file scope.');
    }
    await waitFor(
      () => window.google?.accounts?.oauth2?.initTokenClient,
      'Google Identity Services',
    );

    return new Promise((resolve, reject) => {
      const tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope,
        callback: (response) => {
          if (response?.error || !response?.access_token) {
            reject(new Error(response?.error || 'Google authorization did not return an access token.'));
            return;
          }
          resolve(response.access_token);
        },
        error_callback: (error) => {
          reject(new Error(error?.type || 'Google authorization popup failed.'));
        },
      });
      tokenClient.requestAccessToken({prompt: ''});
    });
  }

  async function pick(clientId, developerKey, appId, scope, folders, multiSelect) {
    if (!clientId || !developerKey || !appId) {
      throw new Error('Google Drive Picker configuration is incomplete.');
    }
    if (scope !== DRIVE_FILE_SCOPE) {
      throw new Error('Google Drive Picker must use the drive.file scope.');
    }

    await Promise.all([
      loadPickerLibrary(),
      waitFor(() => typeof window.google?.picker !== 'undefined', 'Google Picker'),
    ]);
    const accessToken = await requestDriveFileToken(clientId, scope);

    return new Promise((resolve, reject) => {
      try {
        const view = new window.google.picker.DocsView();
        if (folders) {
          view.setIncludeFolders(true);
          view.setSelectFolderEnabled(true);
          view.setMimeTypes('application/vnd.google-apps.folder');
        }

        const builder = new window.google.picker.PickerBuilder()
          .setAppId(appId)
          .setDeveloperKey(developerKey)
          .setOAuthToken(accessToken)
          .addView(view)
          .setCallback((data) => {
            if (data.action === window.google.picker.Action.PICKED) {
              const ids = (data.docs || [])
                .map((doc) => doc.id)
                .filter((id) => typeof id === 'string' && id.length > 0);
              resolve([...new Set(ids)]);
            } else if (data.action === window.google.picker.Action.CANCEL) {
              resolve([]);
            }
          });

        if (multiSelect && !folders) {
          builder.enableFeature(window.google.picker.Feature.MULTISELECT_ENABLED);
        }
        builder.build().setVisible(true);
      } catch (error) {
        reject(error);
      }
    });
  }

  // The GIS access token stays inside this call's closure. It is never written to
  // local/session storage, cookies, logs, or a Flutter-visible configuration map.
  window.lifeAssistantDrivePickerPick = pick;
})();
