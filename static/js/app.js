class IPAToolUI {
  constructor() {
    this.loginForm = document.querySelector('#login-form');
    this.logoutButton = document.querySelector('#logout-button');
    this.accountBox = document.querySelector('#account-info');
    this.accountFields = this.accountBox?.querySelectorAll('[data-field]') || [];
    this.toast = document.querySelector('#toast');
    this.sections = document.querySelectorAll('#search-section, #purchase-section, #versions-section, #metadata-section, #download-section');

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

    this.forms = {
      search: document.querySelector('#search-form'),
      purchase: document.querySelector('#purchase-form'),
      versions: document.querySelector('#versions-form'),
      metadata: document.querySelector('#metadata-form'),
      download: document.querySelector('#download-form'),
    };

    this.outputs = {
      searchTableBody: document.querySelector('#search-results tbody'),
      searchWrapper: document.querySelector('#search-results'),
      versions: document.querySelector('#versions-output'),
      metadata: document.querySelector('#metadata-output'),
      download: document.querySelector('#download-status'),
    };
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

    this.forms.search?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handleSearch();
    });

    this.forms.purchase?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handlePurchase();
    });

    this.forms.versions?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handleVersions();
    });

    this.forms.metadata?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handleMetadata();
    });

    this.forms.download?.addEventListener('submit', (event) => {
      event.preventDefault();
      this.handleDownload();
    });

    this.toggleAuthCode(false);
    this.refreshAccountState();
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
      section.hidden = !isLoggedIn;
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
    const formData = this.serializeForm(this.forms.search);
    const params = new URLSearchParams();
    if (formData.term) params.set('term', formData.term);
    if (formData.limit) params.set('limit', formData.limit);
    if (formData.includeTvos === 'on' || formData.includeTvos === true) {
      params.set('includeTvos', 'true');
    }
    
    try {
      const response = await fetch(`${this.apiUrl('/api/search')}?${params.toString()}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Search failed');
      }
      this.renderSearchResults(payload.results || []);
      this.outputs.searchWrapper.hidden = false;
    } catch (error) {
      this.showToast(error.message || 'Search failed', true);
    }
  }

  renderSearchResults(results) {
    if (!this.outputs.searchTableBody) return;
    this.outputs.searchTableBody.innerHTML = '';
    results.forEach((app) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${app.trackName || 'N/A'}</td>
        <td>${app.bundleId || 'N/A'}</td>
        <td>${app.version || 'N/A'}</td>
        <td>${app.price ?? 0}</td>
        <td>${app.trackId || 'N/A'}</td>
      `;
      this.outputs.searchTableBody.append(row);
    });
  }

  async handlePurchase() {
    const payload = this.serializeForm(this.forms.purchase);
    try {
      const response = await fetch(this.apiUrl('/api/purchase'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Purchase failed');
      }
      this.showToast('License acquired');
    } catch (error) {
      this.showToast(error.message || 'Purchase failed', true);
    }
  }

  async handleVersions() {
    const formData = this.serializeForm(this.forms.versions);
    const params = new URLSearchParams();
    if (formData.appId) params.set('appId', formData.appId);
    if (formData.bundleId) params.set('bundleId', formData.bundleId);
    if (formData.externalVersionId) params.set('externalVersionId', formData.externalVersionId);
    
    try {
      const response = await fetch(`${this.apiUrl('/api/versions')}?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to load versions');
      }
      // Format the versions output: bold labels and indented list for "All"
      const latest = data.latestExternalVersionId ?? 'N/A';
      const allVersions = Array.isArray(data.externalVersionIdentifiers) ? data.externalVersionIdentifiers : [];
      this.outputs.versions.innerHTML = `
        <div><strong>Latest:</strong> ${latest}</div>
        <div><strong>All:</strong></div>
        <ul style="margin:0.25rem 0 0 1.25rem; padding-left:1rem;">
          ${allVersions.map((v) => `<li>${v}</li>`).join('')}
        </ul>
      `;
      this.outputs.versions.hidden = false;
    } catch (error) {
      this.showToast(error.message || 'Failed to load versions', true);
    }
  }

  async handleMetadata() {
    const formData = this.serializeForm(this.forms.metadata);
    const params = new URLSearchParams();
    if (formData.appId) params.set('appId', formData.appId);
    if (formData.bundleId) params.set('bundleId', formData.bundleId);
    if (formData.versionId) params.set('versionId', formData.versionId);
    
    try {
      const response = await fetch(`${this.apiUrl('/api/version-metadata')}?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to load metadata');
      }
      
      const fileSizeMB = (data.fileSize / (1024 * 1024)).toFixed(2);
      const platformInfo = data.runsOnAppleSilicon 
        ? (data.requiresRosetta ? 'Apple Silicon (Rosetta)' : 'Apple Silicon (Native)')
        : 'Intel only';
      
      this.outputs.metadata.innerHTML = `
        <h3>${data.itemName || 'App'}</h3>
        <dl>
          <dt>Display Version:</dt><dd>${data.displayVersion}</dd>
          <dt>Build Number:</dt><dd>${data.buildNumber}</dd>
          <dt>Bundle ID:</dt><dd>${data.bundleId}</dd>
          <dt>Release Date:</dt><dd>${new Date(data.releaseDate).toLocaleString()}</dd>
          <dt>File Size:</dt><dd>${fileSizeMB} MB</dd>
          <dt>Developer:</dt><dd>${data.artistName}</dd>
          <dt>Genre:</dt><dd>${data.genre}</dd>
          <dt>Age Rating:</dt><dd>${data.ageRating}</dd>
          <dt>Platform:</dt><dd>${platformInfo}</dd>
          <dt>Copyright:</dt><dd>${data.copyright}</dd>
        </dl>
      `;
      this.outputs.metadata.hidden = false;
    } catch (error) {
      this.showToast(error.message || 'Failed to load metadata', true);
    }
  }

  async handleDownload() {
    const payload = this.serializeForm(this.forms.download);
    const shouldPurchase = payload.purchaseIfNeeded === true || payload.purchaseIfNeeded === 'on';
    if (shouldPurchase) {
      payload.purchaseIfNeeded = true;
    } else {
      delete payload.purchaseIfNeeded;
    }
    try {
      const response = await fetch(this.apiUrl('/api/download'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Download failed');
      }
      this.outputs.download.innerHTML = `
        <div><strong>Saved to:</strong> ${data.destinationPath}</div>
        <div><strong>SINF files:</strong> ${data.sinfCount}</div>
      `;
      this.outputs.download.hidden = false;
      this.showToast('Download finished');
    } catch (error) {
      this.showToast(error.message || 'Download failed', true);
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
    this.toast.style.background = isError ? '#ef4444' : '#22c55e';
    this.toast.hidden = false;
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => {
      this.toast.hidden = true;
    }, 4000);
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
