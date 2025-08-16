class GitHubAPI {
  constructor() {
    // Use configuration from config.js, fallback to defaults
    const config = window.REPO_CONFIG || {};
    this.owner = config.owner || 'Grossculptor';
    this.repo = config.repo || 'leschnitz-micro-actions';
    this.branch = config.branch || 'main';
    this.token = null;
    this.password = null;
    
    console.log(`GitHub API configured for: ${this.owner}/${this.repo}`);
  }

  async authenticate(password) {
    try {
      // Store the password as the GitHub Personal Access Token
      this.token = password;
      
      // First, check who owns the token
      const userResponse = await fetch('https://api.github.com/user', {
        headers: {
          'Authorization': `token ${password}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });
      
      if (!userResponse.ok) {
        console.error('Invalid token');
        return { success: false, error: 'Invalid token. Please check your GitHub Personal Access Token.' };
      }
      
      const userData = await userResponse.json();
      console.log('Authenticated as:', userData.login);
      
      // Test if the token works by trying to read the repo
      const response = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}`, {
        headers: {
          'Authorization': `token ${password}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });
      
      if (!response.ok) {
        return { success: false, error: 'Cannot access repository. Token may lack "repo" scope.' };
      }
      
      const repoData = await response.json();
      
      // Check if user owns the repo or has write permissions
      const isOwner = repoData.owner.login.toLowerCase() === userData.login.toLowerCase();
      const hasWritePermission = repoData.permissions && repoData.permissions.push;
      
      if (!isOwner && !hasWritePermission) {
        console.warn('User does not have write permissions to this repository');
        return { 
          success: false, 
          error: `You (${userData.login}) don't have write access to ${this.owner}/${this.repo}.\n\nOptions:\n1. Fork the repository to your account\n2. Ask ${this.owner} for write access\n3. Use a token from the ${this.owner} account`
        };
      }
      
      this.password = password;
      sessionStorage.setItem('edit_auth', btoa(password));
      sessionStorage.setItem('auth_time', Date.now());
      sessionStorage.setItem('github_user', userData.login);
      return { success: true, user: userData.login };
    } catch (error) {
      console.error('Auth error:', error);
      return { success: false, error: 'Authentication failed: ' + error.message };
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
    this.password = null;
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
            'Authorization': `token ${token}`,
            'Accept': 'application/vnd.github.v3+json'
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
          'Authorization': `token ${token}`,
          'Accept': 'application/vnd.github.v3+json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('GitHub API error:', errorData);
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
          'Authorization': `token ${token}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Failed to get projects.json:', errorData);
        throw new Error(`Failed to get current projects.json: ${errorData.message || response.statusText}`);
      }

      const fileData = await response.json();
      
      // Encode content properly for GitHub API
      const jsonString = JSON.stringify(projectsData, null, 2);
      const content = btoa(unescape(encodeURIComponent(jsonString)));

      const updateResponse = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/contents/docs/data/projects.json`, {
        method: 'PUT',
        headers: {
          'Authorization': `token ${token}`,
          'Accept': 'application/vnd.github.v3+json',
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