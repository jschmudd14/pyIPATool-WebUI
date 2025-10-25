class IPAToolUI {
  constructor() {
    this.loginForm = document.querySelector('#login-form');
    this.logoutButton = document.querySelector('#logout-button');
    this.accountBox = document.querySelector('#account-info');
    this.accountFields = this.accountBox?.querySelectorAll('[data-field]') || [];
    this.toast = document.querySelector('#toast');
    this.sections = document.querySelectorAll('#app-finder-section, #versions-section');

    this.baseUrl = window.APP_BASE_URL || '';
    if (this.baseUrl === '/') {
      this.baseUrl = '';
    } else if (this.baseUrl.endsWith('/') && this.baseUrl.length > 1) {
      this.baseUrl = this.baseUrl.slice(0, -1);
    }

    this.authCodeField = document.querySelector('#auth-code-field');
    this.authCodeMessage = document.querySelector('#auth-code-message');
    this.authCodeInput = this.authCodeField ? this.authCodeField.querySelector('input') : null;
  this.authModal = document.querySelector('#auth-modal');
  this.authModalForm = document.querySelector('#auth-modal-form');
  this.authModalMessage = document.querySelector('#auth-modal-message');
  this.authModalError = document.querySelector('#auth-modal-error');
  this.authModalInput = document.querySelector('#auth-modal-input');
  this.authModalCancel = document.querySelector('#auth-modal-cancel');
  this.pendingCredentials = null;

    this.currentAppId = null;
    this.currentBundleId = null;

    this.tabs = document.querySelectorAll('.tab-btn');
    this.tabContents = document.querySelectorAll('.tab-content');
    this.searchForm = document.querySelector('#search-form');
    this.directLookupForm = document.querySelector('#direct-lookup-form');
    this.searchResults = document.querySelector('#search-results');
    this.versionsSection = document.querySelector('#versions-section');
    this.versionsList = document.querySelector('#versions-list');
    this.appTitle = document.querySelector('#app-title');
    this.appSubtitle = document.querySelector('#app-subtitle');
    this.downloadProgress = document.querySelector('#download-progress');
    this.downloadProgressText = document.querySelector('#download-progress-text');
    this.downloadProgressFilename = document.querySelector('#download-progress-filename');
  }

  apiUrl(path) {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${this.baseUrl}${normalizedPath}`;
  }

  toggleAuthCode(show) {
    if (!this.authCodeField) {
      return;
    }
    this.authCodeField.hidden = !show;
    if (this.authCodeMessage) {
      this.authCodeMessage.hidden = !show;
    }
    if (!show && this.authCodeInput) {
      this.authCodeInput.value = '';
    }
    if (show && this.authCodeInput) {
      this.authCodeInput.focus();
    }
  }

  init() {
    // Hide versions section on initial load
    if (this.versionsSection) {
      this.versionsSection.hidden = true;
    }

    this.loginForm?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handleLogin();
    });

    this.logoutButton?.addEventListener('click', () => this.handleLogout());

    this.authModalForm?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handleAuthModalSubmit();
    });

    this.authModalCancel?.addEventListener('click', () => {
      this.hideAuthCodeModal();
      this.pendingCredentials = null;
    });

    this.tabs?.forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
    });

    // Toggle tvOS hint visibility
    const tvosCheckbox = document.querySelector('#tvos-checkbox');
    const tvosHint = document.querySelector('#tvos-hint');
    if (tvosCheckbox && tvosHint) {
      tvosCheckbox.addEventListener('change', (e) => {
        tvosHint.hidden = !e.target.checked;
      });
    }

    this.searchForm?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handleSearch();
    });

    this.directLookupForm?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handleDirectLookup();
    });

    this.refreshAccountState();
  }

  switchTab(tabName) {
    this.tabs.forEach(tab => {
      tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    this.tabContents.forEach(content => {
      content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
    
    // Hide versions section when switching tabs
    if (this.versionsSection) {
      this.versionsSection.hidden = true;
    }
    
    // Clear search results when switching away from search tab
    if (tabName !== 'search' && this.searchResults) {
      this.searchResults.hidden = true;
    }
  }

  setLoggedIn(isLoggedIn) {
    if (this.loginForm) {
      this.loginForm.hidden = isLoggedIn;
      if (isLoggedIn) {
        this.loginForm.style.display = 'none';
      } else {
        this.loginForm.style.removeProperty('display');
      }
    }
    if (this.logoutButton) {
      this.logoutButton.hidden = !isLoggedIn;
    }
    if (this.accountBox) {
      this.accountBox.hidden = !isLoggedIn;
    }
    this.sections.forEach((section) => {
      if (section.id === 'app-finder-section') {
        section.hidden = !isLoggedIn;
      } else if (section.id === 'versions-section') {
        // Always hide versions section when logging in/out
        section.hidden = true;
      }
    });
    if (!isLoggedIn) {
      this.clearAccountFields();
      this.toggleAuthCode(false);
    }
  }

  clearAccountFields() {
    this.accountFields.forEach((node) => {
      node.textContent = 'N/A';
    });
  }

  async refreshAccountState() {
    try {
      const response = await fetch(this.apiUrl('/api/account'));
      if (!response.ok) {
        this.setLoggedIn(false);
        return;
      }
      const payload = await response.json();
      this.updateAccountBox(payload.account);
      this.setLoggedIn(true);
    } catch (error) {
      console.error(error);
      this.setLoggedIn(false);
    }
  }

  updateAccountBox(account) {
    if (!account) {
      this.setLoggedIn(false);
      return;
    }
    this.accountFields.forEach((node) => {
      const field = node.dataset.field;
      node.textContent = account?.[field] ?? 'N/A';
    });
  }

  async handleLogin() {
    if (!this.loginForm) {
      return;
    }

    const entries = Object.fromEntries(new FormData(this.loginForm).entries());
    const credentials = {
      email: entries.email || '',
      password: entries.password || '',
    };
    if (entries.authCode) {
      credentials.authCode = entries.authCode;
    }

    this.pendingCredentials = { ...credentials };
    await this.performLogin(credentials);
  }

  async performLogin(credentials) {
    const baseCredentials = {
      email: credentials.email || '',
      password: credentials.password || '',
    };
    const payload = { ...credentials };
    if (payload.authCode) {
      payload.authCode = String(payload.authCode).replace(/\s+/g, '');
    } else {
      delete payload.authCode;
    }

    try {
      const response = await fetch(this.apiUrl('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();

      if (!response.ok) {
        if (response.status === 401 && result.authCodeRequired) {
          this.pendingCredentials = baseCredentials;
          this.showAuthCodeModal(result.error || 'Verification code required');
          return;
        }
        throw new Error(result.error || 'Login failed');
      }

      this.pendingCredentials = null;
      this.toggleAuthCode(false);
      this.hideAuthCodeModal();
      if (this.loginForm) {
        this.loginForm.reset();
      }
      this.showToast('Signed in successfully');
      this.updateAccountBox(result.account);
      this.setLoggedIn(true);
    } catch (error) {
      if (credentials.authCode) {
        this.pendingCredentials = baseCredentials;
        this.showAuthCodeModal(error.message || 'Login failed');
        if (this.authModalError) {
          this.authModalError.textContent = error.message || 'Login failed';
          this.authModalError.hidden = false;
        }
      } else {
        this.pendingCredentials = null;
      }
      this.showToast(error.message || 'Login failed', true);
    }
  }

  handleAuthModalSubmit() {
    if (!this.pendingCredentials) {
      this.showToast('Please start the sign-in flow again', true);
      this.hideAuthCodeModal();
      return;
    }

    const code = this.authModalInput?.value.trim();
    if (!code) {
      if (this.authModalError) {
        this.authModalError.textContent = 'Enter the six-digit verification code to continue.';
        this.authModalError.hidden = false;
      }
      this.authModalInput?.focus();
      return;
    }

    if (this.authModalError) {
      this.authModalError.hidden = true;
    }

    const nextAttempt = {
      ...this.pendingCredentials,
      authCode: code,
    };

    if (this.authCodeInput) {
      this.authCodeInput.value = code;
    }

    this.hideAuthCodeModal();
    this.pendingCredentials = nextAttempt;
    this.performLogin(nextAttempt);
  }

  async handleLogout() {
    try {
      await fetch(this.apiUrl('/api/auth/logout'), { method: 'POST' });
    } finally {
      this.showToast('Signed out');
      this.setLoggedIn(false);
    }
  }

  async handleSearch() {
    const formData = this.serializeForm(this.searchForm);
    const params = new URLSearchParams();
    if (formData.term) params.set('term', formData.term);
    if (formData.limit) params.set('limit', formData.limit);
    
    // Store whether this is a tvOS search
    this.lastSearchWasTvOS = false;
    if (formData.includeTvos === 'on' || formData.includeTvos === true) {
      params.set('includeTvos', 'true');
      this.lastSearchWasTvOS = true;
    }
    
    try {
      const response = await fetch(`${this.apiUrl('/api/search')}?${params.toString()}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Search failed');
      }
      this.renderSearchResults(payload.results || []);
    } catch (error) {
      this.showToast(error.message || 'Search failed', true);
    }
  }

  renderSearchResults(results) {
    if (!this.searchResults) return;
    
    if (results.length === 0) {
      this.searchResults.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No apps found</p></div>';
      this.searchResults.hidden = false;
      return;
    }

    this.searchResults.innerHTML = results.map(app => `
      <div class="app-card" data-app-id="${app.trackId}" data-bundle-id="${app.bundleId}">
        <div class="app-card-header">
          <div>
            <h3 class="app-card-title">${app.trackName || 'Unknown'}</h3>
            <div class="app-card-meta">
              <span>📦 ${app.bundleId || 'N/A'}</span>
              <span>🏷️ v${app.version || 'N/A'}</span>
              ${app.price > 0 ? `<span>💰 $${app.price}</span>` : '<span class="badge">Free</span>'}
            </div>
            <div style="margin-top: 0.5rem;">
              <span class="copy-code" data-copy="${app.trackId}" title="Click to copy App ID">
                <span class="copy-icon">🆔</span>
                <span>${app.trackId}</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    `).join('');

    this.searchResults.querySelectorAll('.app-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.copy-code')) {
          return;
        }
        
        // Show alert if this was a tvOS search
        if (this.lastSearchWasTvOS) {
          alert('Note: The versions listed will be iOS versions by default. To view tvOS-specific versions, use the Direct Lookup tab and enter a tvOS Version ID to filter related tvOS versions.');
        }
        
        const appId = card.dataset.appId;
        const bundleId = card.dataset.bundleId;
        this.loadAppVersions(appId, bundleId);
      });
    });

    this.searchResults.querySelectorAll('.copy-code').forEach(code => {
      code.addEventListener('click', (e) => {
        e.stopPropagation();
        const text = code.dataset.copy;
        navigator.clipboard.writeText(text).then(() => {
          this.showToast(`Copied: ${text}`);
        }).catch(() => {
          this.showToast('Failed to copy', true);
        });
      });
    });

    this.searchResults.hidden = false;
  }

  async handleDirectLookup() {
    const formData = this.serializeForm(this.directLookupForm);
    if (!formData.appId && !formData.bundleId) {
      this.showToast('Please provide App ID or Bundle ID', true);
      return;
    }
    this.loadAppVersions(formData.appId, formData.bundleId, formData.externalVersionId);
  }

  async loadAppVersions(appId, bundleId, externalVersionId = null) {
    this.currentAppId = appId;
    this.currentBundleId = bundleId;

    const params = new URLSearchParams();
    if (appId) params.set('appId', appId);
    if (bundleId) params.set('bundleId', bundleId);
    if (externalVersionId) params.set('externalVersionId', externalVersionId);

    try {
      this.versionsSection.hidden = false;
      this.versionsList.innerHTML = '<div style="text-align:center;padding:2rem;"><div class="loading"></div></div>';
      this.appTitle.textContent = 'Loading...';
      this.appSubtitle.textContent = '';

      const response = await fetch(`${this.apiUrl('/api/versions')}?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) {
        // Check if it's a license error
        if (data.error && data.error.includes('license') || data.metadata?.failureType === '9610') {
          const shouldAcquire = confirm('A license is required to view versions for this app. Would you like to acquire it now?');
          if (shouldAcquire) {
            await this.acquireLicenseAndRetry(appId, bundleId, externalVersionId);
            return;
          }
        }
        throw new Error(data.error || 'Failed to load versions');
      }

      const versions = Array.isArray(data.externalVersionIdentifiers) ? data.externalVersionIdentifiers : [];
      await this.loadAndRenderVersions(versions);
    } catch (error) {
      this.showToast(error.message || 'Failed to load versions', true);
      this.versionsList.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>${error.message}</p></div>`;
      this.versionsSection.hidden = true;
    }
  }

  async acquireLicenseAndRetry(appId, bundleId, externalVersionId = null) {
    try {
      this.showToast('Acquiring license...');
      
      const payload = {};
      if (appId) payload.appId = appId;
      if (bundleId) payload.bundleId = bundleId;

      const response = await fetch(this.apiUrl('/api/purchase'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to acquire license');
      }
      
      this.showToast('License acquired successfully');
      
      // Retry loading versions
      await this.loadAppVersions(appId, bundleId, externalVersionId);
    } catch (error) {
      this.showToast(error.message || 'Failed to acquire license', true);
      this.versionsSection.hidden = true;
    }
  }

  async loadAndRenderVersions(versionIds) {
    if (versionIds.length === 0) {
      this.versionsList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📦</div><p>No versions found</p></div>';
      this.versionsSection.hidden = true;
      return;
    }

    const metadataPromises = versionIds.map(versionId => this.fetchVersionMetadata(versionId));
    const metadataResults = await Promise.allSettled(metadataPromises);
    
    const versions = metadataResults
      .map((result, index) => {
        if (result.status === 'fulfilled') {
          return { ...result.value, versionId: versionIds[index] };
        }
        return null;
      })
      .filter(Boolean);

    if (versions.length > 0) {
      this.appTitle.textContent = versions[0].itemName || 'App Versions';
      this.appSubtitle.textContent = `${versions[0].bundleId || this.currentBundleId} • ${versions.length} version${versions.length > 1 ? 's' : ''}`;
      this.renderVersionCards(versions);
      this.versionsSection.hidden = false;
    } else {
      this.versionsList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📦</div><p>No versions found</p></div>';
      this.versionsSection.hidden = true;
    }
  }

  async fetchVersionMetadata(versionId) {
    const params = new URLSearchParams();
    if (this.currentAppId) params.set('appId', this.currentAppId);
    if (this.currentBundleId) params.set('bundleId', this.currentBundleId);
    params.set('versionId', versionId);

    const response = await fetch(`${this.apiUrl('/api/version-metadata')}?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) {
      // For metadata errors, we'll just skip this version instead of prompting
      // since we're loading multiple versions at once
      throw new Error(data.error || 'Failed to load metadata');
    }
    return data;
  }

  renderVersionCards(versions) {
    this.versionsList.innerHTML = versions.map((version, index) => {
      const fileSizeMB = (version.fileSize / (1024 * 1024)).toFixed(2);
      const releaseDate = new Date(version.releaseDate).toLocaleDateString();

      return `
        <div class="version-card" data-version-id="${version.versionId}" data-index="${index}">
          <div class="version-header">
            <div class="version-basic">
              <div><strong>Version:</strong> ${version.displayVersion}</div>
              <div><strong>Build:</strong> ${version.buildNumber}</div>
              <div><strong>Size:</strong> ${fileSizeMB} MB</div>
              <div><strong>Released:</strong> ${releaseDate}</div>
            </div>
            <span class="expand-icon">▼</span>
          </div>
          <div class="version-details">
            <dl>
              <dt>Version ID:</dt>
              <dd>
                <span class="copy-code" data-copy="${version.versionId}" title="Click to copy Version ID">
                  <span>${version.versionId}</span>
                </span>
              </dd>
              <dt>Bundle ID:</dt><dd>${version.bundleId}</dd>
              <dt>Developer:</dt><dd>${version.artistName}</dd>
              <dt>Genre:</dt><dd>${version.genre}</dd>
              <dt>Age Rating:</dt><dd>${version.ageRating}</dd>
              <dt>Copyright:</dt><dd>${version.copyright}</dd>
            </dl>
            <div class="version-actions">
              <button type="button" class="download-version-btn" data-version-id="${version.versionId}">Download IPA</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    this.versionsList.querySelectorAll('.version-card').forEach(card => {
      const header = card.querySelector('.version-header');
      header.addEventListener('click', () => {
        card.classList.toggle('expanded');
      });

      const downloadBtn = card.querySelector('.download-version-btn');
      
      downloadBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        this.downloadVersion(card.dataset.versionId, false);
      });
    });

    this.versionsList.querySelectorAll('.copy-code').forEach(code => {
      code.addEventListener('click', (e) => {
        e.stopPropagation();
        const text = code.dataset.copy;
        navigator.clipboard.writeText(text).then(() => {
          this.showToast(`Copied: ${text}`);
        }).catch(() => {
          this.showToast('Failed to copy', true);
        });
      });
    });
  }

  async downloadVersion(versionId, purchaseIfNeeded) {
    const payload = {
      externalVersionId: versionId
    };
    if (this.currentAppId) payload.appId = this.currentAppId;
    if (this.currentBundleId) payload.bundleId = this.currentBundleId;
    if (purchaseIfNeeded) payload.purchaseIfNeeded = true;

    try {
      this.showToast('Starting download...');
      this.showDownloadProgress('Preparing download...');
      
      const response = await fetch(this.apiUrl('/api/download-stream'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Download failed');
      }
      
      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'app.ipa';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (match && match[1]) {
          filename = match[1].replace(/['"]/g, '');
        }
      }
      
      this.updateDownloadProgress('Downloading...', filename);
      
      // Create blob from response
      const blob = await response.blob();
      
      this.updateDownloadProgress('Saving file...', filename);
      
      // Create download link and trigger download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      this.hideDownloadProgress();
      this.showToast(`Downloaded: ${filename}`);
    } catch (error) {
      this.hideDownloadProgress();
      this.showToast(error.message || 'Download failed', true);
    }
  }

  showDownloadProgress(message, filename = '') {
    if (!this.downloadProgress) return;
    if (this.downloadProgressText) {
      this.downloadProgressText.textContent = message;
    }
    if (this.downloadProgressFilename) {
      this.downloadProgressFilename.textContent = filename;
      this.downloadProgressFilename.hidden = !filename;
    }
    this.downloadProgress.hidden = false;
  }

  updateDownloadProgress(message, filename = '') {
    if (this.downloadProgressText) {
      this.downloadProgressText.textContent = message;
    }
    if (this.downloadProgressFilename && filename) {
      this.downloadProgressFilename.textContent = filename;
      this.downloadProgressFilename.hidden = false;
    }
  }

  hideDownloadProgress() {
    if (this.downloadProgress) {
      this.downloadProgress.hidden = true;
    }
  }

  serializeForm(form) {
    const result = {};
    if (!form) return result;
    const formData = new FormData(form);
    for (const [key, value] of formData.entries()) {
      if (value === '') continue;
      if (result[key]) {
        if (Array.isArray(result[key])) {
          result[key].push(value);
        } else {
          result[key] = [result[key], value];
        }
      } else {
        result[key] = value;
      }
    }
    return result;
  }

  showToast(message, isError = false) {
    if (!this.toast) return;
    this.toast.textContent = message;
    
    // Remove all toast type classes
    this.toast.classList.remove('success', 'error', 'info');
    
    // Add appropriate class
    if (isError) {
      this.toast.classList.add('error');
    } else if (message.toLowerCase().includes('copied')) {
      this.toast.classList.add('info');
    } else {
      this.toast.classList.add('success');
    }
    
    this.toast.style.removeProperty('background');
    this.toast.hidden = false;
    
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => {
      this.toast.hidden = true;
    }, 2500);
  }

  showAuthCodeModal(message) {
    if (!this.authModal) {
      this.toggleAuthCode(true);
      if (this.authCodeMessage) {
        this.authCodeMessage.hidden = false;
        this.authCodeMessage.textContent = message;
      }
      return;
    }

    if (this.authModalMessage) {
      this.authModalMessage.textContent = message || 'Enter the verification code to continue.';
    }
    if (this.authModalInput) {
      this.authModalInput.value = '';
    }
    if (this.authModalError) {
      this.authModalError.hidden = true;
    }
    this.authModal.hidden = false;
    this.authModalInput?.focus();
  }

  hideAuthCodeModal() {
    if (this.authModal) {
      this.authModal.hidden = true;
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const ui = new IPAToolUI();
  ui.init();
});
