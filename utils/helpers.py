"""
Utility Helpers Module
======================

This module contains general helper functions and utilities
for the Web Page Intelligence application.

Author: AI Assistant
Date: 2025
"""

import re
import logging
import hashlib
import unicodedata
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    
    try:
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remove multiple consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Clean up common HTML entities that might have been missed
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' ',
            '&mdash;': '—',
            '&ndash;': '–',
            '&hellip;': '...',
            '&rsquo;': "'",
            '&lsquo;': "'",
            '&rdquo;': '"',
            '&ldquo;': '"'
        }
        
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)
        
        return text.strip()
        
    except Exception as e:
        logger.warning(f"Error cleaning text: {str(e)}")
        return text.strip() if text else ""

def extract_main_content(text: str) -> str:
    """Extract main content from text, removing navigation and boilerplate"""
    if not text:
        return ""
    
    try:
        # Remove common navigation and boilerplate patterns
        patterns_to_remove = [
            r'skip to (?:main )?content',
            r'back to top',
            r'terms (?:of service|and conditions)',
            r'privacy policy',
            r'cookie (?:policy|notice)',
            r'all rights reserved',
            r'copyright \d{4}',
            r'follow us on',
            r'share this',
            r'print this page',
            r'email this',
            r'subscribe to',
            r'newsletter signup',
            r'breadcrumb',
            r'navigation menu',
            r'sidebar',
            r'footer',
            r'header'
        ]
        
        cleaned_text = text
        for pattern in patterns_to_remove:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace again
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
        
    except Exception as e:
        logger.warning(f"Error extracting main content: {str(e)}")
        return text

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    if not text:
        return []
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to end at a sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 200 characters
            search_start = max(end - 200, start)
            sentence_ends = []
            
            for match in re.finditer(r'[.!?]\s+', text[search_start:end]):
                sentence_ends.append(search_start + match.end())
            
            if sentence_ends:
                end = sentence_ends[-1]
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def format_response(response: str) -> str:
    """Format response text for better readability"""
    if not response:
        return ""
    
    try:
        # Clean the response
        formatted = clean_text(response)
        
        # Add proper spacing after periods if missing
        formatted = re.sub(r'\.(?=[A-Z])', '. ', formatted)
        
        # Ensure proper paragraph breaks
        formatted = re.sub(r'\n\s*\n', '\n\n', formatted)
        
        # Clean up bullet points
        formatted = re.sub(r'^[-*•]\s*', '• ', formatted, flags=re.MULTILINE)
        
        return formatted.strip()
        
    except Exception as e:
        logger.warning(f"Error formatting response: {str(e)}")
        return response

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    if not filename:
        return "untitled"
    
    try:
        # Remove or replace unsafe characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
        
        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "untitled"
        
        return sanitized
        
    except Exception as e:
        logger.warning(f"Error sanitizing filename: {str(e)}")
        return "untitled"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].strip() + suffix

def remove_duplicates(items: List[Dict[str, Any]], 
                     key_func: Callable[[Dict], str] = None,
                     similarity_threshold: float = 0.9) -> List[Dict[str, Any]]:
    """Remove duplicate items from list based on similarity"""
    if not items:
        return items
    
    if not key_func:
        key_func = lambda x: str(x)
    
    unique_items = []
    seen_keys = set()
    
    for item in items:
        try:
            item_key = key_func(item).lower().strip()
            
            # Check for exact matches
            if item_key in seen_keys:
                continue
            
            # Check for similar items (simple similarity check)
            is_duplicate = False
            for existing_key in seen_keys:
                similarity = calculate_text_similarity(item_key, existing_key)
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_items.append(item)
                seen_keys.add(item_key)
                
        except Exception as e:
            logger.warning(f"Error checking duplicate: {str(e)}")
            # Include item if we can't check for duplicates
            unique_items.append(item)
    
    return unique_items

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity (Jaccard similarity)"""
    if not text1 or not text2:
        return 0.0
    
    try:
        # Tokenize texts into words
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 and not words2:
            return 1.0
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
        
    except Exception:
        return 0.0

def create_hash(text: str) -> str:
    """Create MD5 hash of text"""
    try:
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    except Exception:
        return ""

def log_error(context: str, error: Exception):
    """Log error with context"""
    logger.error(f"{context}: {str(error)}", exc_info=True)

def safe_json_load(json_string: str) -> Dict[str, Any]:
    """Safely load JSON string with error handling"""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Error parsing JSON: {str(e)}")
        return {}

def safe_json_dump(data: Dict[str, Any], indent: int = None) -> str:
    """Safely dump data to JSON string"""
    try:
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning(f"Error dumping JSON: {str(e)}")
        return "{}"

def ensure_directory_exists(directory_path: str) -> bool:
    """Ensure directory exists, create if not"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {str(e)}")
        return False

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return 0.0

def format_timestamp(timestamp: Optional[str] = None) -> str:
    """Format timestamp for display"""
    try:
        if timestamp:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.now()
        
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text (simple approach)"""
    if not text:
        return []
    
    try:
        # Remove common stop words
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'to', 'are', 'as',
            'an', 'or', 'for', 'with', 'has', 'this', 'that', 'of', 'in',
            'it', 'you', 'have', 'be', 'was', 'were', 'been', 'their', 'said',
            'each', 'which', 'do', 'how', 'if', 'will', 'up', 'other', 'about',
            'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would',
            'make', 'like', 'into', 'him', 'time', 'two', 'more', 'go', 'no',
            'way', 'could', 'my', 'than', 'first', 'been', 'call', 'who', 'oil',
            'its', 'now', 'find', 'long', 'down', 'day', 'did', 'get', 'come',
            'made', 'may', 'part'
        }
        
        # Extract words and filter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:max_keywords] if freq > 1]
        
        return keywords
        
    except Exception as e:
        logger.warning(f"Error extracting keywords: {str(e)}")
        return []

def validate_config_value(value: Any, value_type: type, default: Any = None) -> Any:
    """Validate configuration value with type checking"""
    try:
        if value is None:
            return default
        
        if isinstance(value, value_type):
            return value
        
        # Try to convert
        if value_type == bool:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        elif value_type == int:
            return int(value)
        elif value_type == float:
            return float(value)
        elif value_type == str:
            return str(value)
        else:
            return default
            
    except (ValueError, TypeError):
        return default

def measure_execution_time(func: Callable) -> Callable:
    """Decorator to measure execution time"""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.debug(f"{func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    
    return wrapper

def batch_process(items: List[Any], batch_size: int = 10) -> List[List[Any]]:
    """Split items into batches"""
    if not items:
        return []
    
    batches = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batches.append(batch)
    
    return batches