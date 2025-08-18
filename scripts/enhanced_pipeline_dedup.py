#!/usr/bin/env python3
"""
Enhanced deduplication functions to detect cross-domain duplicate articles.
These functions can be integrated into the pipeline.py to prevent duplicates.
"""

import re
from urllib.parse import urlparse
from difflib import SequenceMatcher

def extract_article_slug(url: str) -> str:
    """
    Extract a normalized article slug that can identify the same article
    across different domains (e.g., nto.pl and strzelceopolskie.naszemiasto.pl).
    """
    if not url:
        return ""
    
    url_lower = url.lower()
    
    # Parse the URL
    parsed = urlparse(url_lower)
    path = parsed.path
    
    # Remove common article ID patterns but keep the slug
    # Pattern: /slug/ar/c7-12345 -> slug
    match = re.search(r'/([a-z0-9-]+)/ar/c\d+-\d+', path)
    if match:
        return match.group(1)
    
    # Pattern: /slug,12345 -> slug
    match = re.search(r'/([a-z0-9-]+),\d+', path)
    if match:
        return match.group(1)
    
    # Pattern: /artykul/slug,12345 -> slug
    match = re.search(r'/artykul/([a-z0-9-]+)', path)
    if match:
        return match.group(1)
    
    # Extract longest slug-like pattern from the path
    slugs = re.findall(r'[a-z0-9-]{15,}', path)
    if slugs:
        # Return the longest slug found
        return max(slugs, key=len)
    
    # Fallback: use the path without common suffixes
    clean_path = re.sub(r'/ar/c\d+-\d+$', '', path)
    clean_path = re.sub(r',\d+$', '', clean_path)
    clean_path = re.sub(r'\.html?$', '', clean_path)
    clean_path = re.sub(r'/artykul/', '/', clean_path)
    clean_path = clean_path.strip('/')
    
    # Return the last segment if it looks like a slug
    if '/' in clean_path:
        segments = clean_path.split('/')
        last_segment = segments[-1]
        if len(last_segment) > 10 and re.match(r'^[a-z0-9-]+$', last_segment):
            return last_segment
    
    return clean_path

def is_duplicate_article(url1: str, url2: str, similarity_threshold: float = 0.85) -> bool:
    """
    Check if two URLs point to the same article on different domains.
    
    Args:
        url1: First URL
        url2: Second URL
        similarity_threshold: Minimum similarity ratio to consider as duplicate (0.85 = 85%)
    
    Returns:
        True if the URLs appear to be the same article on different domains
    """
    # Extract domains
    domain1 = urlparse(url1).netloc.lower()
    domain2 = urlparse(url2).netloc.lower()
    
    # If same domain, not a cross-domain duplicate
    if domain1 == domain2:
        return False
    
    # Known syndication patterns
    syndicated_domains = [
        {'nto.pl', 'strzelceopolskie.naszemiasto.pl', 'naszemiasto.pl'},
        {'strzelce360.pl', 'strzelce.pl'},
        {'radio.opole.pl', 'opole.pl'}
    ]
    
    # Check if domains are in a known syndication group
    domains_syndicated = False
    for group in syndicated_domains:
        if domain1 in group and domain2 in group:
            domains_syndicated = True
            break
    
    # Extract article slugs
    slug1 = extract_article_slug(url1)
    slug2 = extract_article_slug(url2)
    
    # If we couldn't extract meaningful slugs, can't determine
    if not slug1 or not slug2 or len(slug1) < 10 or len(slug2) < 10:
        return False
    
    # Check exact match first
    if slug1 == slug2:
        return True
    
    # For known syndicated domains, use lower threshold
    if domains_syndicated:
        similarity_threshold = 0.80
    
    # Calculate similarity
    similarity = SequenceMatcher(None, slug1, slug2).ratio()
    
    return similarity >= similarity_threshold

def find_cross_domain_duplicate(url: str, existing_urls: list) -> str:
    """
    Find if a URL has a duplicate article on another domain in the existing URLs.
    
    Args:
        url: URL to check
        existing_urls: List of existing URLs to check against
    
    Returns:
        The duplicate URL if found, None otherwise
    """
    for existing_url in existing_urls:
        if is_duplicate_article(url, existing_url):
            return existing_url
    return None

# Integration example for pipeline.py:
def should_skip_article(url: str, existing_items: list):
    """
    Check if an article should be skipped due to duplication.
    
    Args:
        url: URL of the article to check
        existing_items: List of existing items with 'source' field
    
    Returns:
        Tuple of (should_skip: bool, reason: str)
    """
    # Extract existing URLs
    existing_urls = [item.get('source', '') for item in existing_items if item.get('source')]
    
    # Check for cross-domain duplicate
    duplicate_url = find_cross_domain_duplicate(url, existing_urls)
    if duplicate_url:
        domain1 = urlparse(url).netloc
        domain2 = urlparse(duplicate_url).netloc
        return True, f"Cross-domain duplicate: {domain1} -> {domain2}"
    
    return False, ""

# Test the functions
if __name__ == "__main__":
    # Test cases from the user's example
    test_urls = [
        ("https://strzelceopolskie.naszemiasto.pl/oto-najstarsze-miasta-na-opolszczyznie-bedziecie-zaskoczeni/ar/c7-9161265",
         "https://nto.pl/oto-najstarsze-miasta-na-opolszczyznie-bedziecie-zaskoczeni-niektorymi-z-nich/ar/c7-17183813"),
        
        ("https://strzelceopolskie.naszemiasto.pl/na-opolszczyznie-mamy-mnostwo-stulatkow-w-ktorym-miescie/ar/c1-9852137",
         "https://nto.pl/na-opolszczyznie-mamy-mnostwo-stulatkow-w-ktorym-miescie-zyje-ich-najwiecej/ar/c1-19022810"),
    ]
    
    print("Testing cross-domain duplicate detection:\n")
    for url1, url2 in test_urls:
        slug1 = extract_article_slug(url1)
        slug2 = extract_article_slug(url2)
        is_dup = is_duplicate_article(url1, url2)
        
        print(f"URL 1: {url1}")
        print(f"  Slug: {slug1}")
        print(f"URL 2: {url2}")
        print(f"  Slug: {slug2}")
        print(f"  Is duplicate? {is_dup}")
        print()