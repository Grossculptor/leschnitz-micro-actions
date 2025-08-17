#!/usr/bin/env python3
"""Generate XML sitemap for Leschnitz Micro Actions website."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

def generate_sitemap():
    """Generate sitemap.xml from projects.json data."""
    
    # Load projects data
    projects_file = Path(__file__).parent.parent / "docs" / "data" / "projects.json"
    with open(projects_file, 'r', encoding='utf-8') as f:
        projects = json.load(f)
    
    # Create XML structure
    urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    # Add main page with highest priority
    main_url = ET.SubElement(urlset, 'url')
    ET.SubElement(main_url, 'loc').text = 'https://grossculptor.github.io/leschnitz-micro-actions/'
    ET.SubElement(main_url, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
    ET.SubElement(main_url, 'changefreq').text = 'hourly'
    ET.SubElement(main_url, 'priority').text = '1.0'
    
    # Add location-specific pages (high priority)
    location_pages = [
        ('leschnitz', 'Leschnitz - German historical perspective'),
        ('lesnica', 'Leśnica - Polish current affairs'),
        ('oberschlesien', 'Oberschlesien - Upper Silesia regional overview'),
        ('gross-strehlitz', 'Gross Strehlitz - Strzelce Opolskie'),
        ('oppeln', 'Oppeln - Opole region')
    ]
    
    for page, desc in location_pages:
        url = ET.SubElement(urlset, 'url')
        ET.SubElement(url, 'loc').text = f'https://grossculptor.github.io/leschnitz-micro-actions/{page}/'
        ET.SubElement(url, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
        ET.SubElement(url, 'changefreq').text = 'daily'
        ET.SubElement(url, 'priority').text = '0.9'
    
    # Add about page
    about_url = ET.SubElement(urlset, 'url')
    ET.SubElement(about_url, 'loc').text = 'https://grossculptor.github.io/leschnitz-micro-actions/about/'
    ET.SubElement(about_url, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
    ET.SubElement(about_url, 'changefreq').text = 'weekly'
    ET.SubElement(about_url, 'priority').text = '0.8'
    
    # Note: Individual action pages (/action/<hash>/) are not included 
    # because they don't exist as separate HTML pages yet.
    # The main page loads all actions dynamically via JavaScript.
    
    # Create pretty XML
    tree = ET.ElementTree(urlset)
    
    # Write sitemap with pretty formatting
    sitemap_path = Path(__file__).parent.parent / "docs" / "sitemap.xml"
    
    # Manual pretty print for compatibility
    xml_str = ET.tostring(urlset, encoding='unicode')
    
    # Add XML declaration and format
    pretty_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    pretty_xml += xml_str.replace('><', '>\n<')
    
    # Write to file
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"Sitemap generated with {len(location_pages) + 2} URLs")
    print(f"Saved to: {sitemap_path}")

if __name__ == "__main__":
    generate_sitemap()