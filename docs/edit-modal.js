class EditModal {
  constructor() {
    this.modal = null;
    this.currentItem = null;
    this.mediaFiles = [];
    this.maxFiles = 4;
    this.initRetries = 0;
    this.maxRetries = 50; // Maximum 2.5 seconds of retrying
    this.pendingBackgroundIndex = null;
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
                <button id="deleteButton" class="btn-delete">Delete</button>
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
    const deleteBtn = document.getElementById('deleteButton');
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
    deleteBtn.addEventListener('click', () => this.delete());

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
    const passwordInput = document.getElementById('editPassword');
    const errorDiv = document.getElementById('authError');
    
    // Safety check - ensure elements exist
    if (!passwordInput || !errorDiv) {
      console.error('Authentication elements not found in DOM');
      alert('Authentication interface not ready. Please try again.');
      return;
    }
    
    const password = passwordInput.value;
    
    if (!password) {
      errorDiv.textContent = 'Please enter your GitHub Personal Access Token';
      return;
    }

    try {
      // GitHub API should already be loaded due to event-based initialization
      if (!window.githubAPI || typeof window.githubAPI.authenticate !== 'function') {
        console.error('GitHub API not available during authentication');
        errorDiv.innerHTML = `
          <div style="color: #ff6b6b;">GitHub API not available</div>
          <div style="margin-top: 0.5rem; font-size: 0.85rem;">
            This shouldn't happen. Please:
            <ul style="text-align: left; margin: 0.5rem 0;">
              <li>Check browser console for errors</li>
              <li>Refresh the page (Ctrl+F5 or Cmd+Shift+R)</li>
              <li>Disable ad blockers if any</li>
            </ul>
          </div>
        `;
        return;
      }
      
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
    console.log('Opening edit modal for item:', item?.hash);
    
    // Step 1: Ensure modal structure exists FIRST
    if (!this.modal || !document.getElementById('editModal')) {
      console.log('Modal not initialized, creating now...');
      this.init();
      
      // If still no modal after init, abort with user feedback
      if (!this.modal || !document.getElementById('editModal')) {
        console.error('Failed to create modal after initialization');
        alert('Unable to open editor. Please refresh the page and try again.');
        return;
      }
    }
    
    // Step 2: Verify all required child elements exist
    const authSection = document.getElementById('authSection');
    const editSection = document.getElementById('editSection');
    const passwordInput = document.getElementById('editPassword');
    const errorDiv = document.getElementById('authError');
    
    if (!authSection || !editSection || !passwordInput || !errorDiv) {
      console.error('Modal child elements missing, reinitializing...');
      // Clear and reinitialize
      if (this.modal) {
        this.modal.remove();
      }
      this.modal = null;
      this.init();
      
      // Try to get elements again
      const authSectionRetry = document.getElementById('authSection');
      const editSectionRetry = document.getElementById('editSection');
      
      if (!authSectionRetry || !editSectionRetry) {
        console.error('Critical: Modal structure corrupt even after reinitialization');
        alert('Editor initialization failed. Please refresh the page.');
        return;
      }
    }
    
    // Step 3: NOW safely proceed with item setup
    // Deep clone the item to prevent reference issues
    this.currentItem = JSON.parse(JSON.stringify(item));
    this.mediaFiles = [];
    
    // Step 4: Safely manipulate DOM elements (they're guaranteed to exist now)
    const auth = document.getElementById('authSection');
    const edit = document.getElementById('editSection');
    const pwd = document.getElementById('editPassword');
    const err = document.getElementById('authError');
    
    // Check if githubAPI is loaded and authenticated
    if (window.githubAPI && typeof window.githubAPI.isAuthenticated === 'function' && window.githubAPI.isAuthenticated()) {
      const user = sessionStorage.getItem('github_user');
      auth.style.display = 'none';
      edit.style.display = 'block';
      console.log(`Currently authenticated as: ${user}`);
      this.loadItemData();
    } else {
      auth.style.display = 'block';
      edit.style.display = 'none';
      pwd.value = '';
      err.innerHTML = '';
    }
    
    // Step 5: Display the modal
    this.modal.style.display = 'flex';
    console.log('Modal opened successfully');
  }

  loadItemData() {
    if (!this.currentItem) return;
    
    const titleInput = document.getElementById('editTitle');
    const descInput = document.getElementById('editDescription');
    
    if (!titleInput || !descInput) {
      console.error('Edit form elements not found');
      return;
    }
    
    titleInput.value = this.currentItem.title || '';
    descInput.value = this.currentItem.description || '';
    
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
        const isBackground = this.currentItem.backgroundImage === media.url;
        item.innerHTML = `
          <img src="${media.thumb || media.url}" alt="Media">
          <button class="remove-media" data-index="${index}" data-existing="true">&times;</button>
          <span class="media-type">${media.type}</span>
          ${media.type === 'image' ? `
            <label class="background-check" title="Use as background">
              <input type="checkbox" class="set-background" data-url="${media.url}" ${isBackground ? 'checked' : ''}>
              <span class="bg-icon">🖼</span>
            </label>
          ` : ''}
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
          <label class="background-check" title="Use as background">
            <input type="checkbox" class="set-background" data-new-index="${index}">
            <span class="bg-icon">🖼</span>
          </label>
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

    // Add event listeners for background checkboxes
    preview.querySelectorAll('.set-background').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        // Uncheck all other checkboxes first
        preview.querySelectorAll('.set-background').forEach(cb => {
          if (cb !== checkbox) cb.checked = false;
        });
        
        if (checkbox.checked) {
          // Set the background image URL
          if (checkbox.dataset.url) {
            // Existing image
            this.currentItem.backgroundImage = checkbox.dataset.url;
          } else if (checkbox.dataset.newIndex !== undefined) {
            // New image - mark it for later processing
            this.pendingBackgroundIndex = parseInt(checkbox.dataset.newIndex);
          }
        } else {
          // Clear background image
          this.currentItem.backgroundImage = null;
          this.pendingBackgroundIndex = null;
        }
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
      let newBackgroundImageUrl = null;
      
      if (this.mediaFiles.length > 0) {
        progressText.textContent = 'Uploading media files...';
        
        for (let i = 0; i < this.mediaFiles.length; i++) {
          const file = this.mediaFiles[i];
          progressFill.style.width = `${(i / this.mediaFiles.length) * 50}%`;
          progressText.textContent = `Uploading ${file.name} (${i + 1}/${this.mediaFiles.length})...`;
          
          try {
            const mediaData = await window.githubAPI.uploadMedia(file, this.currentItem.hash);
            uploadedMedia.push(mediaData);
            
            // Check if this is the selected background image
            if (this.pendingBackgroundIndex === i) {
              newBackgroundImageUrl = mediaData.url;
            }
            
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
      
      // Handle background image
      if (newBackgroundImageUrl) {
        updates.backgroundImage = newBackgroundImageUrl;
      } else if (this.currentItem.backgroundImage !== undefined) {
        updates.backgroundImage = this.currentItem.backgroundImage;
      }
      
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
          let verifyData;
          try {
            verifyData = await verifyResponse.json();
          } catch (parseError) {
            console.warn('Could not parse verify response:', parseError);
            verifyData = null;
          }
          if (!verifyData) {
            console.log('Verification skipped - could not parse response');
            return;
          }
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

  async delete() {
    if (!this.currentItem || !this.currentItem.hash) {
      alert('Cannot delete: item not properly loaded');
      return;
    }

    // Confirm deletion
    if (!confirm('Are you sure you want to delete this micro action? This cannot be undone.')) {
      return;
    }

    const progressDiv = document.getElementById('uploadProgress');
    const progressFill = progressDiv.querySelector('.progress-fill');
    const progressText = progressDiv.querySelector('.progress-text');
    const saveBtn = document.getElementById('saveButton');
    const deleteBtn = document.getElementById('deleteButton');
    const cancelBtn = document.getElementById('cancelButton');

    try {
      // Disable all buttons during deletion
      saveBtn.disabled = true;
      deleteBtn.disabled = true;
      cancelBtn.disabled = true;

      progressDiv.style.display = 'block';
      progressFill.style.width = '25%';
      progressText.textContent = 'Deleting micro action...';

      // Call the delete API
      await window.githubAPI.deleteSingleProject(this.currentItem.hash);

      progressFill.style.width = '75%';
      progressText.textContent = 'Verifying deletion...';

      // Wait a moment for GitHub to process
      await new Promise(resolve => setTimeout(resolve, 2000));

      progressFill.style.width = '100%';
      progressText.textContent = 'Success! Micro action deleted.';

      // Show success message
      alert('Micro action deleted successfully!\n\nNote: GitHub Pages may take 1-5 minutes to reflect the changes.');

      // Force reload with cache bust
      setTimeout(() => {
        window.location.href = window.location.pathname + '?t=' + Date.now();
      }, 1500);

    } catch (error) {
      console.error('Delete error:', error);
      progressText.textContent = 'Error: ' + error.message;
      progressFill.style.backgroundColor = '#ff4444';

      // More detailed error message
      let errorMessage = 'Failed to delete micro action:\n\n';
      if (error.message.includes('401')) {
        errorMessage += 'Authentication failed. Please check your GitHub token.';
      } else if (error.message.includes('404')) {
        errorMessage += 'Item not found in the repository.';
      } else if (error.message.includes('403')) {
        errorMessage += 'Permission denied. Check token permissions.';
      } else {
        errorMessage += error.message;
      }

      alert(errorMessage);

      // Re-enable buttons on failure
      saveBtn.disabled = false;
      deleteBtn.disabled = false;
      cancelBtn.disabled = false;

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

// Wait for both DOM and GitHub API to be ready before creating modal
// Enhanced initialization with event-based coordination
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

let domReady = false;
let githubAPIReady = false;

function checkAndInitialize() {
  console.log('edit-modal.js: Checking initialization conditions', {
    domReady,
    githubAPIReady,
    githubAPIExists: !!window.githubAPI
  });
  
  if (domReady && githubAPIReady) {
    console.log('edit-modal.js: Both DOM and GitHub API ready, initializing modal');
    initializeEditModal();
  }
}

// Wait for GitHub API ready event
window.addEventListener('githubAPIReady', (event) => {
  console.log('edit-modal.js: Received githubAPIReady event', event.detail);
  githubAPIReady = true;
  checkAndInitialize();
});

// Also check if GitHub API was already loaded (in case event was dispatched before this script)
if (window.githubAPILoaded) {
  console.log('edit-modal.js: GitHub API already loaded (flag set)');
  githubAPIReady = true;
}

// Wait for DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('edit-modal.js: DOM content loaded');
    domReady = true;
    checkAndInitialize();
  });
} else {
  console.log('edit-modal.js: DOM already ready');
  domReady = true;
  // Check after a micro-task to allow githubAPIReady event to be processed
  setTimeout(checkAndInitialize, 0);
}

// Fallback: If GitHub API hasn't loaded after 10 seconds, show error
setTimeout(() => {
  if (!githubAPIReady) {
    console.error('edit-modal.js: GitHub API failed to load after 10 seconds');
    // Create a minimal edit modal that shows error
    window.editModal = {
      open: () => {
        alert('GitHub API failed to load. The editor cannot function.\n\n' +
              'Possible causes:\n' +
              '• Ad blocker blocking github-api.js\n' +
              '• Network error loading the script\n' +
              '• JavaScript error in github-api.js\n\n' +
              'Please check browser console and refresh the page.');
      }
    };
  }
}, 10000);