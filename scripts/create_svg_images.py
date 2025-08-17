#!/usr/bin/env python3
"""Create SVG placeholder images for SEO/social media."""

from pathlib import Path

def create_images():
    """Create SVG placeholder images."""
    
    media_dir = Path(__file__).parent.parent / "docs" / "media"
    media_dir.mkdir(exist_ok=True)
    
    # Create OG image SVG
    svg_og = '''<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <rect width="1200" height="630" fill="#1a1a1a"/>
  <rect x="10" y="10" width="1180" height="610" fill="none" stroke="#333333" stroke-width="2"/>
  <text x="600" y="250" font-family="system-ui, -apple-system, sans-serif" font-size="72" fill="#e6e6e6" text-anchor="middle" font-weight="600">LESCHNITZ</text>
  <text x="600" y="350" font-family="system-ui, -apple-system, sans-serif" font-size="72" fill="#9a9a9a" text-anchor="middle">MICRO ACTIONS</text>
  <text x="600" y="450" font-family="system-ui, -apple-system, sans-serif" font-size="36" fill="#666666" text-anchor="middle">Upper Silesia • Oberschlesien • Górny Śląsk</text>
</svg>'''
    
    # Create logo SVG
    svg_logo = '''<svg width="512" height="512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#141414"/>
  <rect x="100" y="100" width="312" height="312" fill="none" stroke="#2a2a2a" stroke-width="2"/>
  <rect x="120" y="120" width="272" height="272" fill="none" stroke="#1a1a1a" stroke-width="1"/>
  <text x="256" y="200" font-family="system-ui, -apple-system, sans-serif" font-size="120" fill="#e6e6e6" text-anchor="middle" font-weight="bold">L</text>
  <text x="256" y="320" font-family="system-ui, -apple-system, sans-serif" font-size="24" fill="#9a9a9a" text-anchor="middle">LESCHNITZ</text>
  <text x="256" y="360" font-family="system-ui, -apple-system, sans-serif" font-size="20" fill="#666666" text-anchor="middle">MICRO ACTIONS</text>
</svg>'''
    
    # Save SVG files (browsers can use these)
    svg_og_path = media_dir / "og-image.svg"
    svg_logo_path = media_dir / "logo.svg"
    
    svg_og_path.write_text(svg_og)
    svg_logo_path.write_text(svg_logo)
    
    print(f"Created: {svg_og_path}")
    print(f"Created: {svg_logo_path}")
    
    # Note: GitHub Pages serves SVG files, and modern browsers/social platforms support SVG
    # But we'll also update the meta tags to use .svg extensions
    
    return True

if __name__ == "__main__":
    if create_images():
        print("Successfully created SVG placeholder images")
        print("Note: Update meta tags to reference .svg files instead of .jpg/.png")