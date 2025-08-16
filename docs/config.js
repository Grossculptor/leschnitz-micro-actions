// Configuration for the repository
// If you fork this repository, update these values to match your fork
const REPO_CONFIG = {
  owner: 'Grossculptor',  // Change this to your GitHub username if you fork
  repo: 'leschnitz-micro-actions',  // Change this if you rename the repository
  branch: 'main'
};

// Auto-detect if running from a fork based on the URL
if (window.location.hostname.includes('github.io')) {
  const parts = window.location.hostname.split('.');
  if (parts.length >= 2 && parts[1] === 'github') {
    const detectedOwner = parts[0];
    if (detectedOwner && detectedOwner !== 'grossculptor') {
      console.log(`Detected fork: Running from ${detectedOwner}'s repository`);
      REPO_CONFIG.owner = detectedOwner;
    }
  }
}

window.REPO_CONFIG = REPO_CONFIG;