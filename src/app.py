"""
Flask application entry point for Korail KTX Telegram Bot.

This is the refactored version using the new service-oriented architecture.
"""
import sys
from flask import Flask
from flask_restful import Api
from flask_cors import CORS

# Add src to path for imports
sys.path.insert(0, '/Users/gray/dev/geunsam2/korail_KTX_macro_telegrambot/src')

from config.settings import settings
from storage.redis import RedisStorage
from services import (
    TelegramService,
    KorailService,
    ReservationService,
    PaymentReminderService
)
from api import TelegramWebhook, PaymentCheckAPI
from utils.logger import get_logger, LoggerFactory

# Configure logging
logger = get_logger(__name__)

# Validate settings
try:
    settings.validate()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)

# Set recursion limit
sys.setrecursionlimit(settings.RECURSION_LIMIT)

# Create Flask application
application = Flask(__name__)
CORS(application)
api = Api(application)

# Initialize storage (Redis)
try:
    storage = RedisStorage()
    logger.info("✅ Redis storage initialized successfully")
    # Restore debug mode from Redis
    if storage.is_debug_mode():
        LoggerFactory.set_log_level("DEBUG")
        logger.info("Debug mode restored from Redis - log level set to DEBUG")
except Exception as e:
    logger.error(f"❌ Failed to initialize Redis storage: {e}")
    logger.error("Please ensure Redis is running and accessible")
    sys.exit(1)

# Initialize services
telegram_service = TelegramService(settings.TELEGRAM_BOT_TOKEN)
reservation_service = ReservationService(storage, telegram_service)
payment_reminder_service = PaymentReminderService(storage, telegram_service)

# Configure API resources with dependency injection
api.add_resource(
    TelegramWebhook,
    '/telebot',
    resource_class_kwargs={
        'storage': storage,
        'telegram_service': telegram_service,
        'reservation_service': reservation_service,
        'payment_reminder_service': payment_reminder_service
    }
)

api.add_resource(
    PaymentCheckAPI,
    '/check_payment',
    resource_class_kwargs={
        'storage': storage
    }
)

logger.info("="*60)
logger.info("Korail KTX Telegram Bot - Redis Version")
logger.info("="*60)
logger.info(f"Flask host: {settings.FLASK_HOST}")
logger.info(f"Flask port: {settings.FLASK_PORT}")
logger.info(f"Debug mode: {settings.FLASK_DEBUG}")
logger.info(f"Log level: {settings.LOG_LEVEL}")
logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
logger.info(f"Search interval: {settings.KORAIL_SEARCH_INTERVAL}s")
logger.info(f"Payment timeout: {settings.PAYMENT_TIMEOUT_MINUTES}min")
logger.info(f"Reminder interval: {settings.PAYMENT_REMINDER_INTERVAL_SECONDS}s")
logger.info("="*60)

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    application.run(
        debug=settings.FLASK_DEBUG,
        host=settings.FLASK_HOST,
        port=settings.FLASK_PORT,
        threaded=True
    )
