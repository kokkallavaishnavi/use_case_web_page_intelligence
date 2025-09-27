"""
Utility Validators Module
========================

This module contains URL validation and other validation utilities
for the Web Page Intelligence application.

Author: AI Assistant
Date: 2025
"""

import re
import logging
from typing import List, Set, Optional
from urllib.parse import urlparse, urljoin
import validators

logger = logging.getLogger(__name__)

class URLValidator:
    """URL validation and extraction utilities"""
    
    def __init__(self):
        """Initialize the URL validator"""
        self.blocked_extensions = {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.exe', '.dmg', '.iso',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.css', '.js', '.xml', '.json', '.csv'
        }
        
        self.blocked_domains = {
            'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
            'youtube.com', 'tiktok.com', 'pinterest.com', 'reddit.com',
            'ads.', 'doubleclick.', 'googleads.', 'googlesyndication.'
        }
        
        # Common URL patterns
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and accessible"""
        try:
            if not url or not isinstance(url, str):
                return False
            
            # Basic validation
            if not validators.url(url):
                return False
            
            # Parse URL
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check if domain is blocked
            domain = parsed.netloc.lower()
            for blocked_domain in self.blocked_domains:
                if blocked_domain in domain:
                    return False
            
            # Check file extension
            path = parsed.path.lower()
            for ext in self.blocked_extensions:
                if path.endswith(ext):
                    return False
            
            # Check for suspicious patterns
            if any(pattern in url.lower() for pattern in ['javascript:', 'mailto:', 'tel:', 'ftp:']):
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error validating URL {url}: {str(e)}")
            return False
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """Extract all valid URLs from text"""
        if not text:
            return []
        
        try:
            # Find all URL patterns
            potential_urls = self.url_pattern.findall(text)
            
            # Validate each URL
            valid_urls = []
            for url in potential_urls:
                # Clean URL
                cleaned_url = self.clean_url(url)
                
                if self.is_valid_url(cleaned_url):
                    valid_urls.append(cleaned_url)
            
            # Remove duplicates while preserving order
            unique_urls = []
            seen = set()
            for url in valid_urls:
                if url not in seen:
                    unique_urls.append(url)
                    seen.add(url)
            
            return unique_urls
            
        except Exception as e:
            logger.error(f"Error extracting URLs from text: {str(e)}")
            return []
    
    def clean_url(self, url: str) -> str:
        """Clean and normalize URL"""
        if not url:
            return url
        
        try:
            # Remove common unwanted characters from end
            url = url.rstrip('.,;:!?)"\']}')
            
            # Remove fragments and some query parameters
            parsed = urlparse(url)
            
            # Rebuild URL without fragment
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Add back important query parameters (exclude tracking params)
            if parsed.query:
                clean_params = []
                for param in parsed.query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        # Skip common tracking parameters
                        if key.lower() not in ['utm_source', 'utm_medium', 'utm_campaign', 
                                             'utm_term', 'utm_content', 'fbclid', 'gclid', 
                                             'ref', 'source']:
                            clean_params.append(param)
                
                if clean_params:
                    clean_url += '?' + '&'.join(clean_params)
            
            return clean_url
            
        except Exception as e:
            logger.warning(f"Error cleaning URL {url}: {str(e)}")
            return url
    
    def contains_urls(self, text: str) -> bool:
        """Check if text contains any URLs"""
        if not text:
            return False
        
        return bool(self.url_pattern.search(text))
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]
                
            return domain
            
        except Exception:
            return url
    
    def is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs belong to the same domain"""
        try:
            domain1 = self.extract_domain(url1).lower()
            domain2 = self.extract_domain(url2).lower()
            return domain1 == domain2
        except Exception:
            return False
    
    def normalize_url(self, url: str, base_url: str = None) -> str:
        """Normalize URL (convert relative to absolute if base_url provided)"""
        try:
            if base_url and not url.startswith(('http://', 'https://')):
                return urljoin(base_url, url)
            return url
        except Exception:
            return url
    
    def is_internal_link(self, link_url: str, base_url: str) -> bool:
        """Check if link is internal to the base URL domain"""
        try:
            return self.is_same_domain(link_url, base_url)
        except Exception:
            return False
    
    def validate_url_list(self, urls: List[str]) -> List[str]:
        """Validate a list of URLs and return only valid ones"""
        valid_urls = []
        
        for url in urls:
            if self.is_valid_url(url):
                valid_urls.append(self.clean_url(url))
        
        return valid_urls
    
    def get_url_info(self, url: str) -> dict:
        """Get detailed information about a URL"""
        try:
            parsed = urlparse(url)
            
            return {
                "url": url,
                "domain": self.extract_domain(url),
                "scheme": parsed.scheme,
                "path": parsed.path,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "is_valid": self.is_valid_url(url),
                "is_secure": parsed.scheme == 'https'
            }
            
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "is_valid": False
            }


class ContentValidator:
    """Content validation utilities"""
    
    @staticmethod
    def is_meaningful_content(text: str, min_length: int = 50) -> bool:
        """Check if content is meaningful (not just navigation/boilerplate)"""
        if not text or len(text.strip()) < min_length:
            return False
        
        # Check for common boilerplate patterns
        boilerplate_indicators = [
            'cookie', 'privacy policy', 'terms of service', 'subscribe',
            'newsletter', 'all rights reserved', 'copyright',
            'back to top', 'skip to content', 'navigation menu'
        ]
        
        text_lower = text.lower()
        boilerplate_count = sum(1 for indicator in boilerplate_indicators 
                              if indicator in text_lower)
        
        # If more than 30% of indicators are present, likely boilerplate
        return boilerplate_count < len(boilerplate_indicators) * 0.3
    
    @staticmethod
    def extract_sentences(text: str) -> List[str]:
        """Extract sentences from text"""
        if not text:
            return []
        
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        
        # Clean and filter sentences
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and not sentence.isupper():
                clean_sentences.append(sentence)
        
        return clean_sentences
    
    @staticmethod
    def has_question_indicators(text: str) -> bool:
        """Check if text contains question indicators"""
        question_words = [
            'what', 'how', 'why', 'when', 'where', 'who', 'which',
            'can', 'could', 'would', 'should', 'do', 'does', 'did',
            'is', 'are', 'was', 'were', 'will', 'have', 'has'
        ]
        
        text_lower = text.lower()
        return (
            '?' in text or
            any(text_lower.strip().startswith(word) for word in question_words)
        )


class DataValidator:
    """General data validation utilities"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address"""
        return validators.email(email) if email else False
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = None) -> str:
        """Sanitize text for safe processing"""
        if not text:
            return ""
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Truncate if needed
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip() + "..."
        
        return sanitized
    
    @staticmethod
    def is_valid_confidence_score(score: float) -> bool:
        """Validate confidence score"""
        return isinstance(score, (int, float)) and 0.0 <= score <= 1.0