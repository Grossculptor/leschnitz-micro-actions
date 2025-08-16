# Editing Guide for Leschnitz Micro Actions

## Overview
This website now supports direct editing of micro actions with multimedia uploads through a web interface.

## Requirements
- GitHub Personal Access Token with `repo` scope
- Write access to the repository

## Getting Write Access

You have two options:

### Option 1: Fork the Repository (Recommended)
1. Go to https://github.com/Grossculptor/leschnitz-micro-actions
2. Click the "Fork" button in the top-right corner
3. This creates your own copy of the repository
4. Your fork will be at: `https://github.com/YOUR_USERNAME/leschnitz-micro-actions`
5. The website will be available at: `https://YOUR_USERNAME.github.io/leschnitz-micro-actions`
6. You'll have full write access to your fork

### Option 2: Request Access to Original Repository
1. Contact the repository owner (Grossculptor)
2. Request collaborator access
3. Once granted, you can edit the original repository

## Creating a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens/new
2. Give your token a descriptive name (e.g., "Leschnitz Editor")
3. Select expiration (recommended: 90 days)
4. Check the `repo` scope (full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** - you won't be able to see it again!

## How to Edit

1. **Click the pencil icon** (✎) on any micro action card
2. **Enter your GitHub token** when prompted
3. **Edit the content**:
   - Modify the title
   - Update the description
   - Upload media files (images, videos, audio)
4. **Click Save** to commit changes

## Media Upload

- **Supported formats**: JPG, PNG (images), MP4 (video), MP3 (audio)
- **Maximum files**: 4 per micro action
- **File size limit**: 50MB per file
- Files are stored in `/docs/media/[hash]/` directories
- Thumbnails are automatically generated for images and videos

## Troubleshooting

### "403 - Resource not accessible by personal access token"
- **Cause**: Your token doesn't have write access to the repository
- **Solution**: Either fork the repository or use a token from the repository owner

### "401 - Bad credentials"
- **Cause**: Invalid or expired token
- **Solution**: Create a new token with the correct permissions

### "422 - Invalid request"
- **Cause**: File too large or unsupported format
- **Solution**: Check file size (<50MB) and format

## Security Notes

- Tokens are stored in browser session storage (expires in 15 minutes)
- Never share your personal access token
- Tokens are not stored on the server
- All edits are tracked in Git history

## For Developers

If you fork this repository, the system automatically detects your fork when hosted on GitHub Pages. The configuration in `docs/config.js` will adapt to use your repository.