import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

"""
Web Page Scraper Module using Playwright (Synchronous)
======================================================

This module handles web page scraping using Playwright synchronously, including
scrolling through pages and following hyperlinks to extract comprehensive content.

Author: AI Assistant
Date: 2025
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
import time

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup

from config.settings import AppConfig
from utils.validators import URLValidator
from utils.helpers import clean_text, extract_main_content

logger = logging.getLogger(__name__)

class WebPageScraper:
    """Web page scraper using Playwright for comprehensive content extraction (sync version)"""
    
    def __init__(self):
        """Initialize the web scraper"""
        self.config = AppConfig()
        self.url_validator = URLValidator()
        self.scraped_urls: Set[str] = set()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
    
    def _setup_browser(self) -> None:
        """Setup Playwright browser instance (synchronous)"""
        try:
            self.playwright = sync_playwright().start()
            browser_type = getattr(self.playwright, self.config.PLAYWRIGHT_BROWSER)
            self.browser = browser_type.launch(
                headless=self.config.HEADLESS_MODE,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            self.context = self.browser.new_context(
                user_agent=self.config.USER_AGENT,
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            logger.info("Browser setup completed successfully")
        except Exception as e:
            logger.error(f"Failed to setup browser: {str(e)}")
            raise
    
    def _cleanup_browser(self) -> None:
        """Cleanup browser resources"""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during browser cleanup: {str(e)}")
    
    def _create_page(self) -> Page:
        """Create a new page with optimal settings"""
        if not self.context:
            self._setup_browser()
        page = self.context.new_page()
        page.set_default_timeout(self.config.REQUEST_TIMEOUT)
        return page
    
    def _scroll_page(self, page: Page) -> None:
        """Scroll through the entire page to load dynamic content"""
        try:
            page_height = page.evaluate("document.body.scrollHeight")
            current_height = 0
            while current_height < page_height:
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(self.config.SCROLL_PAUSE_TIME)
                current_height += page.evaluate("window.innerHeight")
                new_page_height = page.evaluate("document.body.scrollHeight")
                if new_page_height > page_height:
                    page_height = new_page_height
            logger.info("Page scrolling completed successfully")
        except Exception as e:
            logger.warning(f"Error during page scrolling: {str(e)}")
    
    def _extract_hyperlinks(self, html_content: str, base_url: str) -> List[str]:
        """Extract hyperlinks from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                if not href or href.startswith('#') or href.startswith('javascript:'):
                    continue
                absolute_url = urljoin(base_url, href)
                if (self.url_validator.is_valid_url(absolute_url) and
                    self._is_same_domain(base_url, absolute_url)):
                    links.append(absolute_url)
            unique_links = list(set(links))[:self.config.MAX_HYPERLINKS_PER_PAGE]
            logger.info(f"Extracted {len(unique_links)} hyperlinks from page")
            return unique_links
        except Exception as e:
            logger.error(f"Error extracting hyperlinks: {str(e)}")
            return []
    
    def _is_same_domain(self, base_url: str, link_url: str) -> bool:
        """Check if two URLs belong to the same domain"""
        try:
            base_domain = urlparse(base_url).netloc.lower().replace('www.', '')
            link_domain = urlparse(link_url).netloc.lower().replace('www.', '')
            return base_domain == link_domain
        except:
            return False
    
    def _scrape_single_page(self, url: str) -> Dict[str, Any]:
        """Scrape content from a single page synchronously"""
        result = {"success": False, "url": url, "title": "", "content": "", "error": None}
        page = None
        try:
            if url in self.scraped_urls:
                logger.info(f"URL already scraped, skipping: {url}")
                return result
            page = self._create_page()
            response = page.goto(url)
            if not response or response.status >= 400:
                raise Exception(f"Failed to load page, status: {response.status if response else 'Unknown'}")
            self._scroll_page(page)
            title = page.title()
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            text_content = extract_main_content(soup.get_text())
            if len(text_content) > self.config.MAX_CONTENT_LENGTH:
                text_content = text_content[:self.config.MAX_CONTENT_LENGTH] + "..."
            result.update({"success": True, "title": title, "content": text_content, "html": html_content})
            self.scraped_urls.add(url)
            logger.info(f"Successfully scraped page: {url} ({len(text_content)} characters)")
        except Exception as e:
            error_msg = f"Error scraping {url}: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
        finally:
            if page:
                page.close()
        return result
    
    def scrape_page_with_hyperlinks(self, main_url: str) -> Dict[str, Any]:
        """Scrape main page and its hyperlinks synchronously"""
        start_time = time.time()
        result = {"success": False, "main_url": main_url, "content": "", "hyperlinks": [],
                  "scraped_pages": [], "errors": [], "processing_time": 0}
        try:
            if not self.url_validator.is_valid_url(main_url):
                raise ValueError(f"Invalid URL provided: {main_url}")
            if not self.browser:
                self._setup_browser()
            logger.info(f"Starting comprehensive scraping for: {main_url}")
            main_page_result = self._scrape_single_page(main_url)
            if not main_page_result["success"]:
                raise Exception(f"Failed to scrape main page: {main_page_result.get('error', 'Unknown error')}")
            hyperlinks = self._extract_hyperlinks(main_page_result.get("html", ""), main_url)
            combined_content = f"=== MAIN PAGE: {main_page_result['title']} ===\n{main_page_result['content']}\n\n"
            result["scraped_pages"].append({
                "url": main_url, "title": main_page_result['title'], "type": "main_page", "success": True
            })
            for link in hyperlinks[:self.config.MAX_CONCURRENT_URLS]:
                link_result = self._scrape_single_page(link)
                if link_result["success"]:
                    combined_content += f"=== HYPERLINK: {link_result['title']} ({link}) ===\n{link_result['content']}\n\n"
                    result["scraped_pages"].append({"url": link, "title": link_result['title'], "type": "hyperlink", "success": True})
                else:
                    error_msg = link_result.get("error", f"Failed to scrape {link}")
                    result["errors"].append(error_msg)
                    result["scraped_pages"].append({"url": link, "title": "", "type": "hyperlink", "success": False, "error": error_msg})
            result.update({"success": True, "content": combined_content.strip(), "hyperlinks": hyperlinks,
                           "processing_time": time.time() - start_time})
            logger.info(f"Comprehensive scraping completed in {result['processing_time']:.2f}s")
        except Exception as e:
            error_msg = f"Error in comprehensive scraping: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            result["processing_time"] = time.time() - start_time
        return result
    
    def close(self) -> None:
        """Close the scraper and cleanup resources"""
        self._cleanup_browser()
        logger.info("WebPageScraper closed successfully")
    
    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        return {
            "total_scraped_urls": len(self.scraped_urls),
            "scraped_urls_list": list(self.scraped_urls),
            "browser_active": self.browser is not None
        }
