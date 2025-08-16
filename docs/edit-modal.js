class EditModal {
  constructor() {
    this.modal = null;
    this.currentItem = null;
    this.mediaFiles = [];
    this.maxFiles = 4;
    this.init();
  }

  init() {
    const modalHTML = `
      <div id="editModal" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Edit Micro Action</h2>
            <button class="modal-close">&times;</button>
          </div>
          <div class="modal-body">
            <div id="authSection" class="auth-section">
              <label for="editPassword">Enter GitHub Personal Access Token:</label>
              <input type="password" id="editPassword" placeholder="GitHub token with repo write access">
              <button id="authButton">Authenticate</button>
              <div id="authError" class="error-message"></div>
              <div class="auth-help">
                <small>Need a token? <a href="https://github.com/settings/tokens/new?scopes=repo" target="_blank">Create one here</a> with 'repo' scope</small>
              </div>
            </div>
            <div id="editSection" class="edit-section" style="display:none;">
              <div class="form-group">
                <label for="editTitle">Title:</label>
                <input type="text" id="editTitle" class="edit-input">
              </div>
              <div class="form-group">
                <label for="editDescription">Description:</label>
                <textarea id="editDescription" class="edit-textarea" rows="4"></textarea>
              </div>
              <div class="form-group">
                <label>Media Files (max 4):</label>
                <div id="dropZone" class="drop-zone">
                  <p>Drag & drop files here or click to browse</p>
                  <input type="file" id="fileInput" multiple accept="image/*,video/*,audio/*" style="display:none;">
                </div>
                <div id="mediaPreview" class="media-preview"></div>
              </div>
              <div class="modal-footer">
                <button id="saveButton" class="btn-save">Save Changes</button>
                <button id="cancelButton" class="btn-cancel">Cancel</button>
                <div id="uploadProgress" class="upload-progress" style="display:none;">
                  <div class="progress-bar"><div class="progress-fill"></div></div>
                  <span class="progress-text">Uploading...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    this.modal = document.getElementById('editModal');
    this.setupEventListeners();
  }

  setupEventListeners() {
    const closeBtn = this.modal.querySelector('.modal-close');
    const authBtn = document.getElementById('authButton');
    const passwordInput = document.getElementById('editPassword');
    const saveBtn = document.getElementById('saveButton');
    const cancelBtn = document.getElementById('cancelButton');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    closeBtn.addEventListener('click', () => this.close());
    cancelBtn.addEventListener('click', () => this.close());
    
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) this.close();
    });

    authBtn.addEventListener('click', () => this.authenticate());
    passwordInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.authenticate();
    });

    saveBtn.addEventListener('click', () => this.save());

    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('drag-over');
    });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      this.handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
      this.handleFiles(e.target.files);
    });
  }

  async authenticate() {
    const password = document.getElementById('editPassword').value;
    const errorDiv = document.getElementById('authError');
    
    if (!password) {
      errorDiv.textContent = 'Please enter your GitHub Personal Access Token';
      return;
    }

    try {
      const isValid = await window.githubAPI.authenticate(password);
      if (isValid) {
        document.getElementById('authSection').style.display = 'none';
        document.getElementById('editSection').style.display = 'block';
        this.loadItemData();
      } else {
        errorDiv.textContent = 'Invalid token or insufficient permissions. Token needs "repo" scope.';
      }
    } catch (error) {
      errorDiv.textContent = 'Authentication failed: ' + error.message;
    }
  }

  open(item) {
    this.currentItem = item;
    this.mediaFiles = [];
    
    if (window.githubAPI.isAuthenticated()) {
      document.getElementById('authSection').style.display = 'none';
      document.getElementById('editSection').style.display = 'block';
      this.loadItemData();
    } else {
      document.getElementById('authSection').style.display = 'block';
      document.getElementById('editSection').style.display = 'none';
      document.getElementById('editPassword').value = '';
      document.getElementById('authError').textContent = '';
    }
    
    this.modal.style.display = 'flex';
  }

  loadItemData() {
    if (!this.currentItem) return;
    
    document.getElementById('editTitle').value = this.currentItem.title || '';
    document.getElementById('editDescription').value = this.currentItem.description || '';
    
    this.renderMediaPreview();
  }

  handleFiles(files) {
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'video/mp4', 'audio/mpeg', 'audio/mp3'];
    const newFiles = Array.from(files).filter(file => {
      if (!validTypes.some(type => file.type.startsWith(type.split('/')[0]))) {
        alert(`Invalid file type: ${file.name}`);
        return false;
      }
      if (file.size > 50 * 1024 * 1024) {
        alert(`File too large: ${file.name} (max 50MB)`);
        return false;
      }
      return true;
    });

    const totalFiles = (this.currentItem.media?.length || 0) + this.mediaFiles.length + newFiles.length;
    if (totalFiles > this.maxFiles) {
      alert(`Maximum ${this.maxFiles} files allowed. You can upload ${this.maxFiles - (this.currentItem.media?.length || 0) - this.mediaFiles.length} more.`);
      return;
    }

    this.mediaFiles.push(...newFiles);
    this.renderMediaPreview();
  }

  renderMediaPreview() {
    const preview = document.getElementById('mediaPreview');
    preview.innerHTML = '';

    if (this.currentItem.media) {
      this.currentItem.media.forEach((media, index) => {
        const item = document.createElement('div');
        item.className = 'preview-item existing';
        item.innerHTML = `
          <img src="${media.thumb || media.url}" alt="Media">
          <button class="remove-media" data-index="${index}" data-existing="true">&times;</button>
          <span class="media-type">${media.type}</span>
        `;
        preview.appendChild(item);
      });
    }

    this.mediaFiles.forEach((file, index) => {
      const item = document.createElement('div');
      item.className = 'preview-item new';
      const url = URL.createObjectURL(file);
      
      if (file.type.startsWith('image/')) {
        item.innerHTML = `
          <img src="${url}" alt="${file.name}">
          <button class="remove-media" data-index="${index}">&times;</button>
          <span class="media-type">image</span>
        `;
      } else if (file.type.startsWith('video/')) {
        item.innerHTML = `
          <video src="${url}"></video>
          <button class="remove-media" data-index="${index}">&times;</button>
          <span class="media-type">video</span>
        `;
      } else if (file.type.startsWith('audio/')) {
        item.innerHTML = `
          <div class="audio-icon">🎵</div>
          <button class="remove-media" data-index="${index}">&times;</button>
          <span class="media-type">audio</span>
        `;
      }
      
      preview.appendChild(item);
    });

    preview.querySelectorAll('.remove-media').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.target.dataset.index);
        const isExisting = e.target.dataset.existing === 'true';
        
        if (isExisting) {
          if (confirm('Remove this existing media file?')) {
            this.currentItem.media.splice(index, 1);
          }
        } else {
          this.mediaFiles.splice(index, 1);
        }
        this.renderMediaPreview();
      });
    });
  }

  async save() {
    const title = document.getElementById('editTitle').value;
    const description = document.getElementById('editDescription').value;
    const progressDiv = document.getElementById('uploadProgress');
    const progressFill = progressDiv.querySelector('.progress-fill');
    const progressText = progressDiv.querySelector('.progress-text');

    if (!title || !description) {
      alert('Title and description are required');
      return;
    }

    try {
      progressDiv.style.display = 'block';
      progressText.textContent = 'Uploading media...';
      
      const uploadedMedia = [];
      for (let i = 0; i < this.mediaFiles.length; i++) {
        const file = this.mediaFiles[i];
        progressFill.style.width = `${(i / this.mediaFiles.length) * 50}%`;
        progressText.textContent = `Uploading ${file.name}...`;
        
        const mediaData = await window.githubAPI.uploadMedia(file, this.currentItem.hash);
        uploadedMedia.push(mediaData);
      }

      progressFill.style.width = '75%';
      progressText.textContent = 'Updating project data...';

      const items = window.__items || [];
      const itemIndex = items.findIndex(item => item.hash === this.currentItem.hash);
      
      if (itemIndex !== -1) {
        items[itemIndex].title = title;
        items[itemIndex].description = description;
        items[itemIndex].media = [...(this.currentItem.media || []), ...uploadedMedia];
        items[itemIndex].lastEdited = new Date().toISOString();
        
        await window.githubAPI.updateProjects(items);
        
        progressFill.style.width = '100%';
        progressText.textContent = 'Success!';
        
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      }
    } catch (error) {
      console.error('Save error:', error);
      alert('Failed to save changes: ' + error.message);
      progressDiv.style.display = 'none';
    }
  }

  close() {
    this.modal.style.display = 'none';
    this.currentItem = null;
    this.mediaFiles = [];
    document.getElementById('mediaPreview').innerHTML = '';
  }
}

window.editModal = new EditModal();