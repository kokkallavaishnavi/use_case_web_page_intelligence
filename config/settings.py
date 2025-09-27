"""
Configuration Settings for Web Page Intelligence Bot Testing
==========================================================

This module contains all configuration settings and environment variables
for the Web Page Intelligence application.

Author: AI Assistant
Date: 2025
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any
import logging

# Load environment variables
load_dotenv()

class AppConfig:
    """Application configuration class"""
    
    def __init__(self):
        """Initialize configuration settings"""
        
        # API Keys and Model Configuration
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
        
        # Model Settings
        self.LLM_MODEL = "llama-3.3-70b-versatile"
        self.EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
        self.EMBEDDING_DEVICE = "cpu"  # Change to "cuda" if GPU available
        
        # LangChain and RAG Settings
        self.CHUNK_SIZE = 2000
        self.CHUNK_OVERLAP = 100
        self.TOP_K_DOCUMENTS = 5
        self.VECTOR_DB_PERSIST_DIR = "data/vectordb"
        
        # Web Scraping Settings
        self.MAX_HYPERLINKS_PER_PAGE = 10
        self.REQUEST_TIMEOUT = 30000  # milliseconds
        self.MAX_CONTENT_LENGTH = 50000  # characters
        self.SCROLL_PAUSE_TIME = 2  # seconds
        
        # Playwright Settings
        self.PLAYWRIGHT_BROWSER = "chromium"  # chromium, firefox, webkit
        self.HEADLESS_MODE = True
        self.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        # Excel Export Settings
        self.EXPORT_DIR = "data/exported_questions"
        self.EXCEL_SHEET_NAME = "Bot_Testing_Questions"
        self.MAX_CELL_LENGTH = 32767  # Excel cell limit
        
        # Session Management
        self.SESSION_DATA_DIR = "data/sessions"
        self.MAX_CHAT_HISTORY = 100
        self.SESSION_TIMEOUT_HOURS = 24
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = "data/logs/app.log"
        self.LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Question Extraction Settings
        self.MIN_QUESTION_LENGTH = 10
        self.MAX_QUESTIONS_PER_PAGE = 50
        self.QUESTION_CONFIDENCE_THRESHOLD = 0.7
        
        # Performance Settings
        self.MAX_CONCURRENT_URLS = 3
        self.CACHE_SIZE = 100
        self.MEMORY_LIMIT_MB = 1024
        
        # Create necessary directories
        self._create_directories()
        
        # Setup logging
        self._setup_logging()
        
        # Validate configuration
        self._validate_config()
    
    def _create_directories(self):
        """Create necessary directories for the application"""
        directories = [
            self.EXPORT_DIR,
            self.SESSION_DATA_DIR,
            self.VECTOR_DB_PERSIST_DIR,
            os.path.dirname(self.LOG_FILE),
            "data/temp"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format=self.LOG_FORMAT,
            handlers=[
                logging.FileHandler(self.LOG_FILE),
                logging.StreamHandler()
            ]
        )
    
    def _validate_config(self):
        """Validate critical configuration settings"""
        if not self.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is required. Please set it in your .env file or environment variables."
            )
        
        if self.CHUNK_SIZE <= 0:
            raise ValueError("CHUNK_SIZE must be a positive integer")
        
        if self.MAX_HYPERLINKS_PER_PAGE <= 0:
            raise ValueError("MAX_HYPERLINKS_PER_PAGE must be a positive integer")
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration dictionary"""
        return {
            "llm_model": self.LLM_MODEL,
            "embedding_model": self.EMBEDDING_MODEL,
            "embedding_device": self.EMBEDDING_DEVICE,
            "groq_api_key": self.GROQ_API_KEY
        }
    
    def get_scraping_config(self) -> Dict[str, Any]:
        """Get web scraping configuration dictionary"""
        return {
            "max_hyperlinks": self.MAX_HYPERLINKS_PER_PAGE,
            "timeout": self.REQUEST_TIMEOUT,
            "max_content_length": self.MAX_CONTENT_LENGTH,
            "scroll_pause": self.SCROLL_PAUSE_TIME,
            "browser": self.PLAYWRIGHT_BROWSER,
            "headless": self.HEADLESS_MODE,
            "user_agent": self.USER_AGENT
        }
    
    def get_rag_config(self) -> Dict[str, Any]:
        """Get RAG configuration dictionary"""
        return {
            "chunk_size": self.CHUNK_SIZE,
            "chunk_overlap": self.CHUNK_OVERLAP,
            "top_k": self.TOP_K_DOCUMENTS,
            "persist_dir": self.VECTOR_DB_PERSIST_DIR
        }
    
    def get_export_config(self) -> Dict[str, Any]:
        """Get export configuration dictionary"""
        return {
            "export_dir": self.EXPORT_DIR,
            "sheet_name": self.EXCEL_SHEET_NAME,
            "max_cell_length": self.MAX_CELL_LENGTH
        }
    
    def is_development_mode(self) -> bool:
        """Check if running in development mode"""
        return os.getenv("ENVIRONMENT", "production").lower() == "development"

# Global configuration instance
config = AppConfig()