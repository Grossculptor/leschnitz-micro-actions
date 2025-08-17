class CardExpand {
  constructor() {
    this.modal = null;
    this.currentItem = null;
    this.init();
  }

  init() {
    const modalHTML = `
      <div id="cardExpandModal" class="card-expand-modal">
        <div class="expand-content">
          <button class="expand-close">&times;</button>
          <div class="expand-layout">
            <div class="expand-image-side">
              <img id="expandImage" alt="Background">
            </div>
            <div class="expand-text-side">
              <div class="expand-text-wrapper">
                <h2 id="expandTitle"></h2>
                <div id="expandMeta" class="expand-meta"></div>
                <p id="expandDescription"></p>
                <div id="expandThumbs" class="expand-thumbnails"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    this.modal = document.getElementById('cardExpandModal');
    this.setupEventListeners();
  }

  setupEventListeners() {
    const closeBtn = this.modal.querySelector('.expand-close');
    closeBtn.addEventListener('click', () => this.close());

    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) this.close();
    });

    document.addEventListener('keydown', (e) => {
      if (this.modal.style.display === 'flex' && e.key === 'Escape') {
        this.close();
      }
    });
  }

  open(item) {
    if (!item.backgroundImage) return;
    
    this.currentItem = item;
    
    // Set image
    const img = document.getElementById('expandImage');
    img.src = item.backgroundImage;
    
    // Set text content
    document.getElementById('expandTitle').textContent = item.title;
    document.getElementById('expandDescription').textContent = item.description;
    
    // Set metadata
    const metaHtml = `
      <span>${new Date(item.datetime || item.published || Date.now()).toLocaleString()}</span>
      <span>${(item.hash || '').slice(0, 8)}</span>
      <a href="${item.source || '#'}" target="_blank" rel="noopener">source</a>
    `;
    document.getElementById('expandMeta').innerHTML = metaHtml;
    
    // Set thumbnails if any media
    const thumbsContainer = document.getElementById('expandThumbs');
    thumbsContainer.innerHTML = '';
    
    if (item.media && item.media.length > 0) {
      item.media.forEach((m, i) => {
        const thumb = document.createElement('div');
        thumb.className = 'expand-thumb';
        thumb.dataset.index = i;
        
        if (m.type === 'image' || m.type === 'video') {
          thumb.innerHTML = `<img src="${m.thumb || m.url}" alt="Media">`;
        } else {
          thumb.innerHTML = `<div class="audio-thumb">▶️</div>`;
        }
        
        thumb.addEventListener('click', () => {
          if (window.mediaViewer) {
            window.mediaViewer.open(item.media, i);
          }
        });
        
        thumbsContainer.appendChild(thumb);
      });
    }
    
    this.modal.style.display = 'flex';
  }

  close() {
    this.modal.style.display = 'none';
    this.currentItem = null;
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.cardExpand = new CardExpand();
  });
} else {
  window.cardExpand = new CardExpand();
}