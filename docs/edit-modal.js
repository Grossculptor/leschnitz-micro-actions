class EditModal {
  constructor() {
    this.modal = null;
    this.currentItem = null;
    this.mediaFiles = [];
    this.maxFiles = 4;
    this.initRetries = 0;
    this.maxRetries = 50; // Maximum 2.5 seconds of retrying
    this.init();
  }

  init() {
    // Check if document.body exists with retry limit
    if (!document.body) {
      if (this.initRetries < this.maxRetries) {
        this.initRetries++;
        console.log(`document.body not ready, retry ${this.initRetries}/${this.maxRetries}`);
        setTimeout(() => this.init(), 50);
        return;
      } else {
        console.error('Failed to initialize modal after maximum retries - document.body never became available');
        return;
      }
    }
    
    // Check if modal already exists
    if (document.getElementById('editModal')) {
      this.modal = document.getElementById('editModal');
      console.log('Modal already exists, reusing it');
      return;
    }
    
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
                <br>
                <small><strong>Important:</strong> You need write access to this repository. Either:</small>
                <br>
                <small>1. Use a token from the repository owner (Grossculptor)</small>
                <br>
                <small>2. <a href="https://github.com/Grossculptor/leschnitz-micro-actions/fork" target="_blank">Fork this repository</a> and edit your fork</small>
              </div>
            </div>
            <div id="editSection" class="edit-section" style="display:none;">
              <div style="text-align: right; margin-bottom: 1rem;">
                <button id="logoutButton" class="btn-logout" style="padding: 0.5rem 1rem; background: #444; color: white; border: none; border-radius: 4px; cursor: pointer;">Logout</button>
              </div>
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

    try {
      // Extra safety check before inserting HTML
      if (!document.body) {
        throw new Error('document.body is still null after passing initial check');
      }
      
      document.body.insertAdjacentHTML('beforeend', modalHTML);
      this.modal = document.getElementById('editModal');
      
      if (!this.modal) {
        throw new Error('Failed to create modal element - insertAdjacentHTML may have failed');
      }
      
      this.setupEventListeners();
      console.log('Edit modal initialized successfully with body present');
      this.initRetries = 0; // Reset retry counter on success
    } catch (error) {
      console.error('Failed to initialize edit modal:', error);
      // Try to recover if possible
      if (this.initRetries < this.maxRetries) {
        this.initRetries++;
        console.log(`Retrying modal init after error, attempt ${this.initRetries}/${this.maxRetries}`);
        setTimeout(() => this.init(), 100);
      }
    }
  }

  setupEventListeners() {
    if (!this.modal) {
      console.error('Modal not initialized, cannot setup event listeners');
      return;
    }
    
    const closeBtn = this.modal.querySelector('.modal-close');
    const authBtn = document.getElementById('authButton');
    const passwordInput = document.getElementById('editPassword');
    const saveBtn = document.getElementById('saveButton');
    const cancelBtn = document.getElementById('cancelButton');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const logoutBtn = document.getElementById('logoutButton');
    
    // Add connection test functionality
    setTimeout(() => {
      const testBtn = document.querySelector('#authSection button:not(#authButton)');
      if (!testBtn) {
        const authSection = document.getElementById('authSection');
        const testButton = document.createElement('button');
        testButton.textContent = 'Test Connection';
        testButton.style.cssText = 'margin-top: 10px; padding: 5px 10px; background: #555; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 12px;';
        testButton.onclick = async () => {
          testButton.textContent = 'Testing...';
          await window.githubAPI.testConnection();
          testButton.textContent = 'Test Connection (check console)';
        };
        authSection.appendChild(testButton);
      }
    }, 100);

    closeBtn.addEventListener('click', () => this.close());
    cancelBtn.addEventListener('click', () => this.close());
    
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        if (confirm('Logout and clear saved authentication?')) {
          window.githubAPI.logout();
          this.close();
          alert('Logged out successfully. You can now use a different token.');
        }
      });
    }
    
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
      errorDiv.textContent = 'Authenticating...';
      const isValid = await window.githubAPI.authenticate(password);
      
      if (isValid) {
        document.getElementById('authSection').style.display = 'none';
        document.getElementById('editSection').style.display = 'block';
        const user = sessionStorage.getItem('github_user');
        console.log(`Authenticated as GitHub user: ${user}`);
        this.loadItemData();
      } else {
        errorDiv.innerHTML = `
          <div style="color: #ff6b6b;">Authentication failed</div>
          <div style="margin-top: 0.5rem; font-size: 0.85rem; color: #aaa;">
            Please ensure your token:
            <ul style="text-align: left; margin: 0.5rem 0;">
              <li>Has "repo" scope (full repository access)</li>
              <li>Is not expired</li>
              <li>Belongs to the repository owner</li>
            </ul>
          </div>
          <div style="margin-top: 0.5rem;">
            <a href="https://github.com/settings/tokens/new?scopes=repo" target="_blank" style="color: #cfcfcf;">Create new token →</a>
          </div>
        `;
      }
    } catch (error) {
      errorDiv.textContent = 'Authentication error: ' + error.message;
    }
  }

  open(item) {
    // Deep clone the item to prevent reference issues
    this.currentItem = JSON.parse(JSON.stringify(item));
    this.mediaFiles = [];
    
    // Always show auth section if user clicks edit, even if previously authenticated
    // This allows users to change tokens
    if (window.githubAPI.isAuthenticated()) {
      const user = sessionStorage.getItem('github_user');
      document.getElementById('authSection').style.display = 'none';
      document.getElementById('editSection').style.display = 'block';
      
      // Show current user in console
      console.log(`Currently authenticated as: ${user}`);
      this.loadItemData();
    } else {
      document.getElementById('authSection').style.display = 'block';
      document.getElementById('editSection').style.display = 'none';
      document.getElementById('editPassword').value = '';
      document.getElementById('authError').innerHTML = '';
    }
    
    // Ensure modal exists before trying to display it
    if (this.modal) {
      this.modal.style.display = 'flex';
    } else {
      console.error('Modal element not found - reinitializing...');
      this.init();
      if (this.modal) {
        this.modal.style.display = 'flex';
      } else {
        console.error('Failed to create modal element');
      }
    }
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

    // Ensure media array exists
    if (!this.currentItem.media) {
      this.currentItem.media = [];
    }

    if (this.currentItem.media && this.currentItem.media.length > 0) {
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
          <div class="audio-icon">▶️</div>
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
      
      // Upload media files if any
      const uploadedMedia = [];
      if (this.mediaFiles.length > 0) {
        progressText.textContent = 'Uploading media files...';
        
        for (let i = 0; i < this.mediaFiles.length; i++) {
          const file = this.mediaFiles[i];
          progressFill.style.width = `${(i / this.mediaFiles.length) * 50}%`;
          progressText.textContent = `Uploading ${file.name} (${i + 1}/${this.mediaFiles.length})...`;
          
          try {
            const mediaData = await window.githubAPI.uploadMedia(file, this.currentItem.hash);
            uploadedMedia.push(mediaData);
            console.log(`Successfully uploaded: ${file.name}`);
          } catch (uploadError) {
            console.error(`Failed to upload ${file.name}:`, uploadError);
            throw new Error(`Failed to upload ${file.name}: ${uploadError.message}`);
          }
        }
      }

      progressFill.style.width = '75%';
      progressText.textContent = 'Updating project data...';

      // Only send the fields that actually changed to prevent data corruption
      const updates = {
        title: title.trim(),
        description: description.trim()
      };
      
      // Always update media field to reflect removals and additions
      updates.media = [...(this.currentItem.media || []), ...uploadedMedia];
      
      console.log('Updating item with hash:', this.currentItem.hash);
      console.log('Original title:', this.currentItem.title);
      console.log('New title:', updates.title);
      console.log('Original description:', this.currentItem.description);
      console.log('New description:', updates.description);
      console.log('Media count:', uploadedMedia.length);
      
      // Use the new single-item update method that handles SHA conflicts better
      await window.githubAPI.updateSingleProject(this.currentItem.hash, updates);
      
      progressFill.style.width = '90%';
      progressText.textContent = 'Verifying save...';
      
      // Wait a moment for GitHub to process
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Verify the save by fetching the updated file
      try {
        const verifyResponse = await fetch(`https://api.github.com/repos/Grossculptor/leschnitz-micro-actions/contents/docs/data/projects.json?ref=main&_=${Date.now()}`, {
          headers: {
            'Authorization': `token ${await window.githubAPI.getToken()}`,
            'Accept': 'application/vnd.github.v3+json'
          }
        });
        
        if (verifyResponse.ok) {
          const verifyData = await verifyResponse.json();
          const verifyContent = JSON.parse(atob(verifyData.content));
          const verifiedItem = verifyContent.find(item => item.hash === this.currentItem.hash);
          
          if (verifiedItem) {
            const titleMatches = verifiedItem.title === title.trim();
            const descMatches = verifiedItem.description === description.trim();
            
            console.log('Verification:', {
              titleMatches,
              descMatches,
              savedTitle: verifiedItem.title,
              expectedTitle: title.trim(),
              savedDesc: verifiedItem.description?.substring(0, 50),
              expectedDesc: description.trim().substring(0, 50)
            });
            
            if (titleMatches && descMatches) {
              console.log('✓ Changes verified on GitHub');
              progressFill.style.width = '100%';
              progressText.textContent = 'Success! Changes saved to GitHub.';
              
              // Show cache warning
              alert('Changes saved successfully!\n\nNote: GitHub Pages may take 1-5 minutes to show your updates.\n\nTry:\n1. Hard refresh (Ctrl+F5 or Cmd+Shift+R)\n2. Clear browser cache\n3. Wait a few minutes for GitHub Pages CDN to update');
              
              // Force reload with cache bust
              setTimeout(() => {
                window.location.href = window.location.pathname + '?t=' + Date.now();
              }, 2000);
            } else {
              console.warn('Verification mismatch - data may have been saved but verification failed');
              progressFill.style.width = '100%';
              progressText.textContent = 'Saved (verification pending)';
              
              // Still reload as the save likely succeeded
              setTimeout(() => {
                window.location.href = window.location.pathname + '?t=' + Date.now();
              }, 2000);
            }
          } else {
            console.error('Item not found in verification');
            progressText.textContent = 'Save may have failed - item not found';
          }
        }
      } catch (verifyError) {
        console.error('Could not verify save:', verifyError);
        progressFill.style.width = '100%';
        progressText.textContent = 'Saved (verification pending)';
        
        setTimeout(() => {
          window.location.href = window.location.pathname + '?t=' + Date.now();
        }, 2000);
      }
      
    } catch (error) {
      console.error('Save error:', error);
      progressText.textContent = 'Error: ' + error.message;
      progressFill.style.backgroundColor = '#ff4444';
      
      // More detailed error message
      let errorMessage = 'Failed to save changes:\n\n';
      if (error.message.includes('401')) {
        errorMessage += 'Authentication failed. Please check your GitHub token has the correct permissions.';
      } else if (error.message.includes('404')) {
        errorMessage += 'File or repository not found. Please check the repository settings.';
      } else if (error.message.includes('422')) {
        errorMessage += 'Invalid request. The file may be too large or in an unsupported format.';
      } else {
        errorMessage += error.message;
      }
      
      alert(errorMessage);
      
      // Reset progress bar after 3 seconds
      setTimeout(() => {
        progressDiv.style.display = 'none';
        progressFill.style.width = '0%';
        progressFill.style.backgroundColor = '#4a7c4a';
        progressText.textContent = 'Uploading...';
      }, 3000);
    }
  }

  close() {
    this.modal.style.display = 'none';
    this.currentItem = null;
    this.mediaFiles = [];
    document.getElementById('mediaPreview').innerHTML = '';
  }
}

// Wait for DOM to be ready before creating modal
// Enhanced initialization with multiple fallbacks
function initializeEditModal() {
  try {
    if (!window.editModal) {
      window.editModal = new EditModal();
      console.log('EditModal instance created successfully');
    }
  } catch (error) {
    console.error('Failed to create EditModal instance:', error);
    // Retry after a delay
    setTimeout(initializeEditModal, 100);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeEditModal);
} else if (document.body) {
  // DOM and body are ready
  initializeEditModal();
} else {
  // Fallback: wait for body to be available
  const bodyWaitInterval = setInterval(() => {
    if (document.body) {
      clearInterval(bodyWaitInterval);
      initializeEditModal();
    }
  }, 10);
  
  // Clear interval after 5 seconds to prevent memory leak
  setTimeout(() => clearInterval(bodyWaitInterval), 5000);
}