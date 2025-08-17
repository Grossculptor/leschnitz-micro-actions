#!/usr/bin/env python3
"""Create placeholder images for SEO/social media."""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_og_image():
    """Create Open Graph image (1200x630) for social media previews."""
    # Create dark gray image
    img = Image.new('RGB', (1200, 630), color='#1a1a1a')
    draw = ImageDraw.Draw(img)
    
    # Add text
    try:
        # Try to use a nice font if available
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except:
        # Fallback to default font
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw title
    text1 = "LESCHNITZ"
    text2 = "MICRO ACTIONS"
    text3 = "Upper Silesia • Oberschlesien • Górny Śląsk"
    
    # Center text
    draw.text((600, 200), text1, fill='#e6e6e6', font=font_large, anchor='mm')
    draw.text((600, 300), text2, fill='#9a9a9a', font=font_large, anchor='mm')
    draw.text((600, 400), text3, fill='#666666', font=font_small, anchor='mm')
    
    # Add border
    draw.rectangle([10, 10, 1190, 620], outline='#333333', width=2)
    
    # Save
    output_path = Path(__file__).parent.parent / "docs" / "media" / "og-image.jpg"
    output_path.parent.mkdir(exist_ok=True)
    img.save(output_path, 'JPEG', quality=85)
    print(f"Created: {output_path}")

def create_logo():
    """Create logo image (512x512) for organization schema."""
    # Create dark square image
    img = Image.new('RGB', (512, 512), color='#141414')
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw minimalist logo
    draw.text((256, 200), "L", fill='#e6e6e6', font=font_large, anchor='mm')
    draw.text((256, 320), "LESCHNITZ", fill='#9a9a9a', font=font_small, anchor='mm')
    draw.text((256, 360), "MICRO ACTIONS", fill='#666666', font=font_small, anchor='mm')
    
    # Add geometric element
    draw.rectangle([100, 100, 412, 412], outline='#2a2a2a', width=2)
    draw.rectangle([120, 120, 392, 392], outline='#1a1a1a', width=1)
    
    # Save
    output_path = Path(__file__).parent.parent / "docs" / "media" / "logo.png"
    img.save(output_path, 'PNG')
    print(f"Created: {output_path}")

if __name__ == "__main__":
    try:
        create_og_image()
        create_logo()
        print("Successfully created placeholder images")
    except ImportError:
        print("Pillow not installed. Creating simple HTML placeholders instead...")
        
        # Create simple placeholder files if PIL not available
        media_dir = Path(__file__).parent.parent / "docs" / "media"
        media_dir.mkdir(exist_ok=True)
        
        # Create minimal SVG as fallback
        svg_og = '''<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
<rect width="1200" height="630" fill="#1a1a1a"/>
<text x="600" y="250" font-family="Arial" font-size="72" fill="#e6e6e6" text-anchor="middle">LESCHNITZ</text>
<text x="600" y="350" font-family="Arial" font-size="72" fill="#9a9a9a" text-anchor="middle">MICRO ACTIONS</text>
<text x="600" y="450" font-family="Arial" font-size="36" fill="#666666" text-anchor="middle">Upper Silesia • Oberschlesien</text>
</svg>'''
        
        svg_logo = '''<svg width="512" height="512" xmlns="http://www.w3.org/2000/svg">
<rect width="512" height="512" fill="#141414"/>
<text x="256" y="200" font-family="Arial" font-size="120" fill="#e6e6e6" text-anchor="middle">L</text>
<text x="256" y="320" font-family="Arial" font-size="24" fill="#9a9a9a" text-anchor="middle">LESCHNITZ</text>
<rect x="100" y="100" width="312" height="312" fill="none" stroke="#2a2a2a" stroke-width="2"/>
</svg>'''
        
        # Save as SVG files
        (media_dir / "og-image.svg").write_text(svg_og)
        (media_dir / "logo.svg").write_text(svg_logo)
        print("Created SVG placeholder files (install Pillow for proper images)")