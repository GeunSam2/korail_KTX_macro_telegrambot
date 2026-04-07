"""
Application configuration management.

This module centralizes all configuration variables from environment
and provides type-safe access to settings throughout the application.
"""
import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.environ.get('BOTTOKEN', '')
    TELEGRAM_API_BASE_URL: str = "https://api.telegram.org/bot{token}"

    # Korail Configuration
    KORAIL_ADMIN_USER_ID: Optional[str] = os.environ.get('USERID')
    KORAIL_ADMIN_PASSWORD: Optional[str] = os.environ.get('USERPW')
    KORAIL_SEARCH_INTERVAL: int = int(os.environ.get('SEARCH_INTERVAL', '1'))  # seconds
    KORAIL_STATION_LIST_URL: str = "http://www.letskorail.com/ebizprd/stationKtxList.do"
    KORAIL_PAYMENT_URL: str = "https://www.letskorail.com/ebizprd/EbizPrdTicketpr13500W_pr13510.do?"

    # User Access Control
    ALLOW_LIST: list[str] = os.environ.get('ALLOW_LIST', '').split(',') if os.environ.get('ALLOW_LIST') else []

    # Payment Reminder Configuration
    PAYMENT_TIMEOUT_MINUTES: int = int(os.environ.get('PAYMENT_TIMEOUT_MINUTES', '10'))
    PAYMENT_REMINDER_INTERVAL_SECONDS: int = int(os.environ.get('PAYMENT_REMINDER_INTERVAL', '10'))

    # Flask Configuration
    FLASK_HOST: str = os.environ.get('FLASK_HOST', '0.0.0.0')
    FLASK_PORT: int = int(os.environ.get('FLASK_PORT', '8080'))
    FLASK_DEBUG: bool = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')

    # Application Callback URLs (internal)
    CALLBACK_BASE_URL: str = f"http://127.0.0.1:{FLASK_PORT}"

    # Logging Configuration
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Magic Admin Login String
    ADMIN_MAGIC_STRING: str = "근삼이최고"

    # Admin Command Authentication
    # Uses USERPW environment variable (same as Korail admin password)
    ADMIN_PASSWORD: Optional[str] = os.environ.get('USERPW')

    # Process Management
    RECURSION_LIMIT: int = 10**7

    @classmethod
    def validate(cls) -> None:
        """Validate required settings."""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("BOTTOKEN environment variable is required")

    @classmethod
    def is_user_allowed(cls, phone_number: str) -> bool:
        """Check if user phone number is in allow list."""
        if not cls.ALLOW_LIST or cls.ALLOW_LIST == ['']:
            return True  # No restriction if ALLOW_LIST is empty
        return phone_number in cls.ALLOW_LIST


# Singleton instance
settings = Settings()
