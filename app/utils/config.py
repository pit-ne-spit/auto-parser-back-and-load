"""Configuration management module."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Path to config.yaml
CONFIG_FILE = Path(__file__).parent.parent.parent / "config.yaml"


class Config:
    """Application configuration."""
    
    def __init__(self):
        """Load configuration from YAML file."""
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Supports nested keys with dot notation, e.g., 'logging.level'
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get('logging', {})
    
    def get_batch_config(self) -> Dict[str, Any]:
        """Get batch processing configuration."""
        return self.get('batch', {})
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration."""
        return self.get('retry', {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration."""
        return self.get('api', {})
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration."""
        return self.get('rate_limit', {})
    
    def get_pagination_config(self) -> Dict[str, Any]:
        """Get pagination configuration."""
        return self.get('pagination', {})
    
    def get_che168_config(self) -> Dict[str, Any]:
        """Get CHE168 API configuration."""
        return self.get('che168', {})


# Environment variables
class EnvConfig:
    """Environment variables configuration."""
    
    @staticmethod
    def get_db_config() -> Dict[str, str]:
        """Get database configuration from environment."""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'che168_db'),
        }
    
    @staticmethod
    def get_che168_api_key() -> str:
        """Get CHE168 API key from environment."""
        return os.getenv('CHE168_API_KEY', '')
    
    @staticmethod
    def get_che168_access_name() -> str:
        """Get CHE168 access name from environment."""
        return os.getenv('CHE168_ACCESS_NAME', 'autobase')
    
    @staticmethod
    def get_secret_key() -> str:
        """Get secret key from environment."""
        return os.getenv('SECRET_KEY', '')
    
    @staticmethod
    def get_api_host() -> str:
        """Get API host from environment."""
        return os.getenv('API_HOST', '0.0.0.0')
    
    @staticmethod
    def get_api_port() -> int:
        """Get API port from environment."""
        return int(os.getenv('API_PORT', '8000'))


# Global config instance
config = Config()
env_config = EnvConfig()
