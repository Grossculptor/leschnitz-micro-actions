class MediaViewer {
  constructor() {
    this.viewer = null;
    this.currentIndex = 0;
    this.mediaItems = [];
    this.init();
  }

  init() {
    const viewerHTML = `
      <div id="mediaViewer" class="media-viewer">
        <div class="viewer-content">
          <button class="viewer-close">&times;</button>
          <button class="viewer-prev">‹</button>
          <button class="viewer-next">›</button>
          <div class="viewer-main">
            <div id="viewerMedia"></div>
          </div>
          <div class="viewer-info">
            <span id="viewerTitle"></span>
            <span id="viewerCounter"></span>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', viewerHTML);
    this.viewer = document.getElementById('mediaViewer');
    this.setupEventListeners();
  }

  setupEventListeners() {
    const closeBtn = this.viewer.querySelector('.viewer-close');
    const prevBtn = this.viewer.querySelector('.viewer-prev');
    const nextBtn = this.viewer.querySelector('.viewer-next');

    closeBtn.addEventListener('click', () => this.close());
    prevBtn.addEventListener('click', () => this.previous());
    nextBtn.addEventListener('click', () => this.next());

    this.viewer.addEventListener('click', (e) => {
      if (e.target === this.viewer) this.close();
    });

    document.addEventListener('keydown', (e) => {
      if (this.viewer.style.display !== 'flex') return;
      
      switch(e.key) {
        case 'Escape':
          this.close();
          break;
        case 'ArrowLeft':
          this.previous();
          break;
        case 'ArrowRight':
          this.next();
          break;
      }
    });
  }

  open(mediaItems, index = 0) {
    this.mediaItems = mediaItems;
    this.currentIndex = index;
    this.viewer.style.display = 'flex';
    this.showMedia();
    this.updateNavigation();
  }

  showMedia() {
    const media = this.mediaItems[this.currentIndex];
    const container = document.getElementById('viewerMedia');
    container.innerHTML = '';

    if (media.type === 'image') {
      const img = document.createElement('img');
      img.src = media.url;
      img.alt = media.name || 'Image';
      container.appendChild(img);
    } else if (media.type === 'video') {
      const video = document.createElement('video');
      video.src = media.url;
      video.controls = true;
      video.autoplay = true;
      container.appendChild(video);
    } else if (media.type === 'audio') {
      const audioContainer = document.createElement('div');
      audioContainer.className = 'audio-player';
      audioContainer.innerHTML = `
        <div class="audio-icon-large">🎵</div>
        <audio controls autoplay>
          <source src="${media.url}" type="audio/mpeg">
          Your browser does not support the audio element.
        </audio>
        <p>${media.name || 'Audio file'}</p>
      `;
      container.appendChild(audioContainer);
    }

    document.getElementById('viewerTitle').textContent = media.name || '';
    document.getElementById('viewerCounter').textContent = `${this.currentIndex + 1} / ${this.mediaItems.length}`;
  }

  updateNavigation() {
    const prevBtn = this.viewer.querySelector('.viewer-prev');
    const nextBtn = this.viewer.querySelector('.viewer-next');
    
    prevBtn.style.display = this.mediaItems.length > 1 ? 'block' : 'none';
    nextBtn.style.display = this.mediaItems.length > 1 ? 'block' : 'none';
    
    prevBtn.disabled = this.currentIndex === 0;
    nextBtn.disabled = this.currentIndex === this.mediaItems.length - 1;
  }

  previous() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.showMedia();
      this.updateNavigation();
    }
  }

  next() {
    if (this.currentIndex < this.mediaItems.length - 1) {
      this.currentIndex++;
      this.showMedia();
      this.updateNavigation();
    }
  }

  close() {
    this.viewer.style.display = 'none';
    const videos = this.viewer.querySelectorAll('video');
    const audios = this.viewer.querySelectorAll('audio');
    videos.forEach(v => v.pause());
    audios.forEach(a => a.pause());
  }
}

window.mediaViewer = new MediaViewer();