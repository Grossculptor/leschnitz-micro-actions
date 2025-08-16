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
      
      // Test if the token works by trying to read the user
      const userResponse = await fetch('https://api.github.com/user', {
        headers: {
          'Authorization': `Bearer ${password}`, // Use Bearer for better compatibility
          'Accept': 'application/vnd.github.v3+json',
          'X-GitHub-Api-Version': '2022-11-28'
        }
      });
      
      if (!userResponse.ok) {
        console.error('Invalid token');
        return false;
      }
      
      const userData = await userResponse.json();
      console.log('Authenticated as:', userData.login);
      
      // Test if the token can access the repo
      const repoResponse = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}`, {
        headers: {
          'Authorization': `Bearer ${password}`,
          'Accept': 'application/vnd.github.v3+json',
          'X-GitHub-Api-Version': '2022-11-28'
        }
      });
      
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
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
          }
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
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github.v3+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'Content-Type': 'application/json'
        },
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

  async updateProjects(projectsData) {
    try {
      const token = await this.getToken();
      
      // Get current file to retrieve SHA
      const response = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/contents/docs/data/projects.json?ref=${this.branch}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github.v3+json',
          'X-GitHub-Api-Version': '2022-11-28'
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
        
        if (updateResponse.status === 403) {
          if (errorData.message?.includes('Resource not accessible')) {
            throw new Error('Your token needs "repo" scope to modify files. Create a new token at https://github.com/settings/tokens/new?scopes=repo');
          }
          throw new Error('Permission denied. Check that your token has "repo" scope.');
        }
        
        throw new Error(`Failed to update projects.json: ${errorData.message || updateResponse.statusText}`);
      }

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

  async generateThumbnail(file) {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = 120;
      canvas.height = 120;

      if (file.type.startsWith('image/')) {
        const img = new Image();
        img.onload = () => {
          const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
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
          const scale = Math.min(canvas.width / video.videoWidth, canvas.height / video.videoHeight);
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