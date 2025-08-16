class GitHubAPI {
  constructor() {
    this.owner = 'Grossculptor';
    this.repo = 'leschnitz-micro-actions';
    this.branch = 'main';
    this.token = null;
    this.password = null;
  }

  async authenticate(password) {
    try {
      // Store the password as the GitHub Personal Access Token
      this.token = password;
      
      // Test multiple authentication methods
      console.log('Testing GitHub authentication...');
      
      // Method 1: Direct test with minimal headers
      let userResponse;
      try {
        userResponse = await fetch('https://api.github.com/user', {
          method: 'GET',
          headers: {
            'Authorization': `token ${password}`,
            'Accept': 'application/vnd.github.v3+json'
          },
          mode: 'cors',
          credentials: 'same-origin'
        });
      } catch (fetchError) {
        console.error('Network error:', fetchError);
        // Try with Bearer format as absolute fallback
        try {
          userResponse = await fetch('https://api.github.com/user', {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${password}`,
              'Accept': 'application/vnd.github.v3+json'
            },
            mode: 'cors',
            credentials: 'same-origin'
          });
        } catch (secondError) {
          console.error('Both auth methods failed:', secondError);
          throw new Error('Network error - please check your connection and try again');
        }
      }
      
      if (!userResponse || !userResponse.ok) {
        const status = userResponse ? userResponse.status : 'unknown';
        console.error('Invalid token, status:', status);
        if (status === 401) {
          throw new Error('Invalid token - please check your Personal Access Token');
        } else if (status === 403) {
          throw new Error('Token lacks required permissions - needs "repo" scope');
        }
        return false;
      }
      
      const userData = await userResponse.json();
      console.log('Authenticated as:', userData.login);
      
      // Test if the token can access the repo - with better error handling
      let repoResponse;
      try {
        repoResponse = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}`, {
          method: 'GET',
          headers: {
            'Authorization': `token ${password}`,
            'Accept': 'application/vnd.github.v3+json'
          },
          mode: 'cors',
          credentials: 'same-origin'
        });
      } catch (repoError) {
        console.error('Failed to check repo access:', repoError);
        // Still allow authentication if user check passed
        console.warn('Could not verify repo access, but user auth succeeded');
        repoResponse = { ok: true };
      }
      
      if (!repoResponse.ok) {
        console.error('Cannot access repository');
        return false;
      }
      
      // Store authentication
      this.password = password;
      sessionStorage.setItem('edit_auth', btoa(password));
      sessionStorage.setItem('auth_time', Date.now());
      sessionStorage.setItem('github_user', userData.login);
      
      console.log('Authentication successful');
      return true;
    } catch (error) {
      console.error('Auth error:', error);
      return false;
    }
  }

  isAuthenticated() {
    const auth = sessionStorage.getItem('edit_auth');
    const authTime = sessionStorage.getItem('auth_time');
    if (!auth || !authTime) return false;
    
    const elapsed = Date.now() - parseInt(authTime);
    if (elapsed > 15 * 60 * 1000) {
      this.logout();
      return false;
    }
    return true;
  }

  logout() {
    sessionStorage.removeItem('edit_auth');
    sessionStorage.removeItem('auth_time');
    sessionStorage.removeItem('github_user');
    this.password = null;
    this.token = null;
  }

  async getToken() {
    if (!this.token) {
      // Try to restore from session storage
      const auth = sessionStorage.getItem('edit_auth');
      if (auth) {
        this.token = atob(auth);
      } else {
        throw new Error('Not authenticated. Please enter your GitHub Personal Access Token.');
      }
    }
    return this.token;
  }

  async uploadFile(filePath, content, message) {
    try {
      const token = await this.getToken();
      
      // Check if file already exists
      let sha = null;
      try {
        const existing = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/contents/${filePath}?ref=${this.branch}`, {
          method: 'GET',
          headers: {
            'Authorization': `token ${token}`, // Use token format
            'Accept': 'application/vnd.github.v3+json'
          },
          mode: 'cors',
          credentials: 'same-origin'
        });
        
        if (existing.ok) {
          const data = await existing.json();
          sha = data.sha;
          console.log('File exists, will update:', filePath);
        }
      } catch (e) {
        console.log('File does not exist, creating new:', filePath);
      }

      const body = {
        message: message || `Upload ${filePath}`,
        content: content,
        branch: this.branch
      };
      
      if (sha) {
        body.sha = sha;
      }

      const response = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/contents/${filePath}`, {
        method: 'PUT',
        headers: {
          'Authorization': `token ${token}`, // Use token format
          'Accept': 'application/vnd.github.v3+json',
          'Content-Type': 'application/json'
        },
        mode: 'cors',
        credentials: 'same-origin',
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('GitHub API error:', errorData);
        
        // Provide more specific error messages
        if (response.status === 403) {
          if (errorData.message?.includes('Resource not accessible')) {
            throw new Error('Token lacks required permissions. Please use a token with "repo" scope.');
          }
          throw new Error('Permission denied. Check token permissions.');
        } else if (response.status === 404) {
          throw new Error('Repository or file path not found.');
        } else if (response.status === 422) {
          throw new Error('Invalid request. File may be too large or path invalid.');
        }
        
        throw new Error(`Failed to upload file: ${response.status} - ${errorData.message || response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  }

  async updateSingleProject(itemHash, updates, retryCount = 0) {
    const maxRetries = 3;
    
    try {
      const token = await this.getToken();
      
      if (!token) {
        throw new Error('No authentication token available. Please login again.');
      }
      
      console.log('Fetching current projects.json from GitHub...');
      
      // Get current file to retrieve SHA and latest data
      let response;
      const maxAttempts = 3;
      let lastError = null;
      
      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
          console.log(`Attempt ${attempt}/${maxAttempts} to fetch projects.json...`);
          
          response = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/contents/docs/data/projects.json?ref=${this.branch}&_=${Date.now()}`, {
            method: 'GET',
            headers: {
              'Authorization': `token ${token}`,
              'Accept': 'application/vnd.github.v3+json'
            },
            mode: 'cors',
            credentials: 'same-origin',
            cache: 'no-cache'
          });
          
          if (response.ok) {
            break; // Success, exit loop
          }
          
          lastError = `HTTP ${response.status}: ${response.statusText}`;
          console.error(`Attempt ${attempt} failed:`, lastError);
          
          if (attempt < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
          }
        } catch (fetchError) {
          lastError = fetchError.message;
          console.error(`Network error on attempt ${attempt}:`, fetchError);
          
          if (attempt < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
          }
        }
      }
      
      if (!response || !response.ok) {
        throw new Error(`Failed to connect to GitHub after ${maxAttempts} attempts. ${lastError || 'Unknown error'}`);
      }

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Failed to get projects.json:', errorData);
        
        if (response.status === 403) {
          throw new Error('Token lacks permissions. Please use a token with "repo" scope for full access.');
        }
        
        throw new Error(`Failed to get current projects.json: ${errorData.message || response.statusText}`);
      }

      const fileData = await response.json();
      const currentSha = fileData.sha;
      console.log(`Attempt ${retryCount + 1}/${maxRetries + 1} - Current SHA:`, currentSha);
      
      // Decode and parse current content
      // Properly decode base64 with UTF-8 support
      const binaryString = atob(fileData.content);
      const bytes = Uint8Array.from(binaryString, char => char.charCodeAt(0));
      const jsonString = new TextDecoder().decode(bytes);
      const currentContent = JSON.parse(jsonString);
      
      // Find and update only the specific item
      const itemIndex = currentContent.findIndex(item => item.hash === itemHash);
      if (itemIndex === -1) {
        console.error('Item not found. Looking for hash:', itemHash);
        console.error('Available hashes:', currentContent.map(i => i.hash));
        throw new Error(`Item with hash ${itemHash} not found in current data`);
      }
      
      console.log('Found item at index:', itemIndex);
      console.log('Current item before update:', JSON.stringify(currentContent[itemIndex]));
      console.log('Updates to apply:', JSON.stringify(updates));
      
      // Validate that we're updating the right item
      const originalItem = currentContent[itemIndex];
      if (originalItem.hash !== itemHash) {
        throw new Error(`Hash mismatch! Expected ${itemHash} but found ${originalItem.hash}`);
      }
      
      // Only update specified fields, preserve everything else
      const updatedItem = { ...originalItem };
      
      // Only update fields that are explicitly provided in updates
      if (updates.hasOwnProperty('title')) {
        updatedItem.title = updates.title;
      }
      if (updates.hasOwnProperty('description')) {
        updatedItem.description = updates.description;
      }
      if (updates.hasOwnProperty('media')) {
        updatedItem.media = updates.media;
      }
      
      // Add metadata
      updatedItem.lastEdited = new Date().toISOString();
      
      // Replace the item in the array
      currentContent[itemIndex] = updatedItem;
      
      console.log('Updated item after update:', JSON.stringify(currentContent[itemIndex]));
      
      // Data integrity check - ensure no items were corrupted
      const itemCount = currentContent.length;
      const uniqueHashes = new Set(currentContent.map(i => i.hash));
      if (uniqueHashes.size !== itemCount) {
        throw new Error('Data integrity check failed: Duplicate hashes detected');
      }
      
      // Verify the updated item has the expected changes
      if (updates.hasOwnProperty('title') && currentContent[itemIndex].title !== updates.title) {
        throw new Error('Data integrity check failed: Title was not updated correctly');
      }
      if (updates.hasOwnProperty('description') && currentContent[itemIndex].description !== updates.description) {
        throw new Error('Data integrity check failed: Description was not updated correctly');
      }
      
      // Encode updated content with proper UTF-8 support
      const jsonString = JSON.stringify(currentContent, null, 2);
      
      // Convert to base64 with UTF-8 encoding (matches our decoding approach)
      const utf8Bytes = new TextEncoder().encode(jsonString);
      const binaryString = Array.from(utf8Bytes, byte => String.fromCharCode(byte)).join('');
      const content = btoa(binaryString);

      // Update with retry logic
      let updateResponse;
      const updateMaxAttempts = 3;
      let updateLastError = null;
      
      for (let attempt = 1; attempt <= updateMaxAttempts; attempt++) {
        try {
          console.log(`Update attempt ${attempt}/${updateMaxAttempts}...`);
          
          updateResponse = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/contents/docs/data/projects.json`, {
            method: 'PUT',
            headers: {
              'Authorization': `token ${token}`,
              'Accept': 'application/vnd.github.v3+json',
              'Content-Type': 'application/json'
            },
            mode: 'cors',
            credentials: 'same-origin',
            body: JSON.stringify({
              message: `Update micro action ${itemHash.substring(0, 8)} via web editor`,
              content: content,
              sha: currentSha,
              branch: this.branch
            })
          });
          
          if (updateResponse.ok) {
            break; // Success
          }
          
          const errorData = await updateResponse.json();
          updateLastError = errorData.message || updateResponse.statusText;
          
          // Check for SHA mismatch
          if (updateResponse.status === 409 || 
              (updateResponse.status === 422 && errorData.message?.includes('does not match'))) {
            console.log('SHA mismatch, refetching...');
            // Return to retry the whole operation
            if (retryCount < maxRetries) {
              await new Promise(resolve => setTimeout(resolve, 500 * Math.pow(2, retryCount)));
              return this.updateSingleProject(itemHash, updates, retryCount + 1);
            }
          }
          
          if (attempt < updateMaxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
          }
        } catch (fetchError) {
          updateLastError = fetchError.message;
          console.error(`Update network error on attempt ${attempt}:`, fetchError);
          
          if (attempt < updateMaxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
          }
        }
      }
      
      if (!updateResponse) {
        throw new Error(`Network error after ${updateMaxAttempts} attempts: ${updateLastError}`);
      }

      if (!updateResponse.ok) {
        const errorData = await updateResponse.json();
        console.error('Failed to update projects.json:', errorData);
        
        // Handle SHA mismatch
        if (updateResponse.status === 409 || 
            updateResponse.status === 422 && 
            (errorData.message?.includes('does not match') || 
             errorData.message?.includes('is at') && errorData.message?.includes('but expected'))) {
          
          console.log('SHA mismatch detected, retrying...');
          
          if (retryCount < maxRetries) {
            const waitTime = Math.min(500 * Math.pow(2, retryCount), 3000);
            console.log(`Retrying in ${waitTime}ms...`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
            return this.updateSingleProject(itemHash, updates, retryCount + 1);
          } else {
            throw new Error('Unable to save due to concurrent updates. Please refresh and try again.');
          }
        }
        
        if (updateResponse.status === 403) {
          if (errorData.message?.includes('Resource not accessible')) {
            throw new Error('Your token needs "repo" scope to modify files.');
          }
          throw new Error('Permission denied. Check token permissions.');
        }
        
        throw new Error(`Failed to update: ${errorData.message || updateResponse.statusText}`);
      }

      console.log('Successfully updated item:', itemHash.substring(0, 8));
      return await updateResponse.json();
    } catch (error) {
      console.error('Update error:', error);
      throw error;
    }
  }

  async updateProjects(projectsData, retryCount = 0) {
    const maxRetries = 3;
    
    try {
      const token = await this.getToken();
      
      // Get current file to retrieve SHA
      const response = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/contents/docs/data/projects.json?ref=${this.branch}&_=${Date.now()}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github.v3+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'Cache-Control': 'no-cache'
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Failed to get projects.json:', errorData);
        
        if (response.status === 403) {
          throw new Error('Token lacks permissions. Please use a token with "repo" scope for full access.');
        }
        
        throw new Error(`Failed to get current projects.json: ${errorData.message || response.statusText}`);
      }

      const fileData = await response.json();
      console.log(`Attempt ${retryCount + 1}/${maxRetries + 1} - Current SHA:`, fileData.sha);
      
      // Encode content properly for GitHub API
      const jsonString = JSON.stringify(projectsData, null, 2);
      const content = btoa(unescape(encodeURIComponent(jsonString)));

      const updateResponse = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/contents/docs/data/projects.json`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github.v3+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: `Update project data via web editor`,
          content: content,
          sha: fileData.sha,
          branch: this.branch
        })
      });

      if (!updateResponse.ok) {
        const errorData = await updateResponse.json();
        console.error('Failed to update projects.json:', errorData);
        
        // Handle SHA mismatch specifically
        if (updateResponse.status === 409 || 
            updateResponse.status === 422 && 
            (errorData.message?.includes('does not match') || 
             errorData.message?.includes('is at') && errorData.message?.includes('but expected'))) {
          
          console.log('SHA mismatch detected, file was updated by another process');
          
          // Retry with exponential backoff
          if (retryCount < maxRetries) {
            const waitTime = Math.min(1000 * Math.pow(2, retryCount), 5000);
            console.log(`Retrying in ${waitTime}ms...`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
            return this.updateProjects(projectsData, retryCount + 1);
          } else {
            throw new Error('File is being continuously updated by another process. Please try again in a few moments.');
          }
        }
        
        if (updateResponse.status === 403) {
          if (errorData.message?.includes('Resource not accessible')) {
            throw new Error('Your token needs "repo" scope to modify files. Create a new token at https://github.com/settings/tokens/new?scopes=repo');
          }
          throw new Error('Permission denied. Check that your token has "repo" scope.');
        }
        
        throw new Error(`Failed to update projects.json: ${errorData.message || updateResponse.statusText}`);
      }

      console.log('Successfully updated projects.json');
      return await updateResponse.json();
    } catch (error) {
      console.error('Update projects error:', error);
      throw error;
    }
  }

  async uploadMedia(file, itemHash) {
    try {
      const reader = new FileReader();
      const fileContent = await new Promise((resolve, reject) => {
        reader.onload = e => resolve(e.target.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const base64Content = fileContent.split(',')[1];
      
      // Sanitize filename - remove special characters and spaces
      const sanitizedName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
      const fileName = `${Date.now()}_${sanitizedName}`;
      const filePath = `docs/media/${itemHash}/${fileName}`;

      console.log('Uploading file:', filePath);
      await this.uploadFile(filePath, base64Content, `Upload media: ${fileName}`);

      let thumbPath = null;
      if (file.type.startsWith('image/') || file.type.startsWith('video/')) {
        const thumbnail = await this.generateThumbnail(file);
        if (thumbnail) {
          const thumbBase64 = thumbnail.split(',')[1];
          const thumbFileName = fileName.replace(/\.[^.]+$/, '') + '_thumb.jpg';
          thumbPath = `docs/media/${itemHash}/${thumbFileName}`;
          console.log('Uploading thumbnail:', thumbPath);
          await this.uploadFile(thumbPath, thumbBase64, `Upload thumbnail: ${thumbFileName}`);
        }
      }

      return {
        type: file.type.startsWith('image/') ? 'image' : 
              file.type.startsWith('video/') ? 'video' : 
              file.type.startsWith('audio/') ? 'audio' : 'file',
        url: filePath.replace('docs/', ''),
        thumb: thumbPath ? thumbPath.replace('docs/', '') : null,
        name: file.name,
        size: file.size
      };
    } catch (error) {
      console.error('Media upload error:', error);
      throw error;
    }
  }

  async testConnection() {
    try {
      console.log('Testing GitHub API connection...');
      
      // Test 1: Basic API connectivity
      const apiTest = await fetch('https://api.github.com', {
        method: 'GET',
        headers: {
          'Accept': 'application/vnd.github.v3+json'
        }
      });
      
      if (!apiTest.ok) {
        throw new Error('Cannot reach GitHub API');
      }
      
      console.log('✓ GitHub API is reachable');
      
      // Test 2: Token validity if available
      if (this.token) {
        const authTest = await fetch('https://api.github.com/user', {
          method: 'GET',
          headers: {
            'Authorization': `token ${this.token}`,
            'Accept': 'application/vnd.github.v3+json'
          }
        });
        
        if (authTest.ok) {
          const user = await authTest.json();
          console.log(`✓ Authenticated as: ${user.login}`);
          
          // Test 3: Repository access
          const repoTest = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}`, {
            method: 'GET',
            headers: {
              'Authorization': `token ${this.token}`,
              'Accept': 'application/vnd.github.v3+json'
            }
          });
          
          if (repoTest.ok) {
            const repo = await repoTest.json();
            console.log(`✓ Can access repository: ${repo.full_name}`);
            console.log(`  Permissions: ${repo.permissions ? JSON.stringify(repo.permissions) : 'unknown'}`);
          } else {
            console.log('✗ Cannot access repository');
          }
        } else {
          console.log('✗ Token is invalid or expired');
        }
      }
      
      return true;
    } catch (error) {
      console.error('Connection test failed:', error);
      return false;
    }
  }

  async generateThumbnail(file) {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = 120;
      canvas.height = 120;

      // Apply grayscale filter
      ctx.filter = 'grayscale(100%)';

      if (file.type.startsWith('image/')) {
        const img = new Image();
        img.onload = () => {
          // Use cover mode: scale to fill entire canvas (crop if needed)
          const scale = Math.max(canvas.width / img.width, canvas.height / img.height);
          const x = (canvas.width / 2) - (img.width / 2) * scale;
          const y = (canvas.height / 2) - (img.height / 2) * scale;
          ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
          resolve(canvas.toDataURL('image/jpeg', 0.7));
        };
        img.onerror = () => resolve(null);
        img.src = URL.createObjectURL(file);
      } else if (file.type.startsWith('video/')) {
        const video = document.createElement('video');
        video.onloadedmetadata = () => {
          video.currentTime = 1;
        };
        video.onseeked = () => {
          // Use cover mode: scale to fill entire canvas (crop if needed)
          const scale = Math.max(canvas.width / video.videoWidth, canvas.height / video.videoHeight);
          const x = (canvas.width / 2) - (video.videoWidth / 2) * scale;
          const y = (canvas.height / 2) - (video.videoHeight / 2) * scale;
          ctx.drawImage(video, x, y, video.videoWidth * scale, video.videoHeight * scale);
          resolve(canvas.toDataURL('image/jpeg', 0.7));
          URL.revokeObjectURL(video.src);
        };
        video.onerror = () => resolve(null);
        video.src = URL.createObjectURL(file);
      } else {
        resolve(null);
      }
    });
  }
}

window.githubAPI = new GitHubAPI();