import asyncio
import logging
import json
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import aiohttp
import os
import random
import shutil
import qrcode
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode, ChatMemberStatus
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import time
import base64
import glob
import gc

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Create necessary directories
os.makedirs("temp", exist_ok=True)
os.makedirs("user_banners", exist_ok=True)
os.makedirs("languages", exist_ok=True)
os.makedirs("banner", exist_ok=True)

# Create comprehensive language files
DEFAULT_LANGUAGES = {
    'en': {
        'language_name': 'English',
        'templates': {
            'prediction': """🎯 <b>AI PREDICTION SYSTEM</b> ━ 24/7

<blockquote>📅 <b>Period:</b> <code>{period}</code>
🎲 <b>Investment:</b> <b>{choice}</b>
🚀 <b>Multiplier:</b> <b>{multiplier}x</b>
💰 <b>Purchase Price:</b> ₹{price}</blockquote>

<a href="{register_link}"><b>🎯 REGISTER NOW & GET BONUS 🎯</b></a>""",
            'win': """🎉 <b>VICTORY ACHIEVED!</b> 🏆

<blockquote>✅ <b>Prediction Successful</b>

📅 <b>Period:</b> <code>{period}</code>
🎯 <b>Result:</b> <b>{result}</b></blockquote>

💰 <b>Excellent investment! Continue your winning streak!</b>""",
            'lose': """💫 <b>NEXT TIME WINNER!</b>

<blockquote>📅 <b>Period:</b> <code>{period}</code>
🎯 <b>Result:</b> <b>{result}</b></blockquote>

⚡ <b>Stay determined! Another opportunity arrives shortly!</b>"""
        }
    },
    'hi': {
        'language_name': 'हिन्दी',
        'templates': {
            'prediction': """🎯 <b>एआई प्रीडिक्शन सिस्टम</b> ━ 24/7

<blockquote>📅 <b>अवधि:</b> <code>{period}</code>
🎲 <b>निवेश:</b> <b>{choice}</b>
🚀 <b>मल्टीप्लायर:</b> <b>{multiplier}x</b>
💰 <b>क्रय मूल्य:</b> ₹{price}</blockquote>

<a href="{register_link}"><b>🎯 अभी पंजीकरण करें और बोनस पाएं 🎯</b></a>""",
            'win': """🎉 <b>जीत हासिल की!</b> 🏆

<blockquote>✅ <b>भविष्यवाणी सफल</b>

📅 <b>अवधि:</b> <code>{period}</code>
🎯 <b>परिणाम:</b> <b>{result}</b></blockquote>

💰 <b>उत्कृष्ट निवेश! अपनी जीत की स्ट्रीक जारी रखें!</b>""",
            'lose': """💫 <b>अगली बार विजेता!</b>

<blockquote>📅 <b>अवधि:</b> <code>{period}</code>
🎯 <b>परिणाम:</b> <b>{result}</b></blockquote>

⚡ <b>दृढ़ रहें! एक और अवसर जल्द ही आता है!</b>"""
        }
    },
    'ur': {
        'language_name': 'اردو',
        'templates': {
            'prediction': """🎯 <b>AI پیشن گوئی کا نظام</b> ━ 24/7

<blockquote>📅 <b>مدت:</b> <code>{period}</code>
🎲 <b>سرمایہ کاری:</b> <b>{choice}</b>
🚀 <b>ضارب:</b> <b>{multiplier}x</b>
💰 <b>قیمت خرید:</b> ₹{price}</blockquote>

<a href="{register_link}"><b>🎯 ابھی رجسٹر کریں اور بونس حاصل کریں 🎯</b></a>""",
            'win': """🎉 <b>کامیابی حاصل ہوئی!</b> 🏆

<blockquote>✅ <b>پیشن گوئی کامیاب</b>

📅 <b>مدت:</b> <code>{period}</code>
🎯 <b>نتیجہ:</b> <b>{result}</b></blockquote>

💰 <b>بہترین سرمایہ کاری! اپنی جیتنے کے سلسلے کو جاری رکھیں!</b>""",
            'lose': """💫 <b>اگلی بار فاتح!</b>

<blockquote>📅 <b>مدت:</b> <code>{period}</code>
🎯 <b>نتیجہ:</b> <b>{result}</b></blockquote>

⚡ <b>ثابت قدم رہیں! ایک اور موقع جلد آتا ہے!</b>"""
        }
    }
}

# Save language files
for lang_code, lang_data in DEFAULT_LANGUAGES.items():
    with open(f'languages/{lang_code}.json', 'w', encoding='utf-8') as f:
        json.dump(lang_data, f, indent=2, ensure_ascii=False)

# Load language files
MONGO_URI = "mongodb+srv://avinash:avinash12@cluster0.wnwd1fv.mongodb.net/?appName=Cluster0"
MONGO_DB_NAME = "bot_24_7"
LANGUAGES = {}
for lang_file in os.listdir('languages'):
    if lang_file.endswith('.json'):
        with open(f'languages/{lang_file}', 'r', encoding='utf-8') as f:
            LANGUAGES[lang_file.replace('.json', '')] = json.load(f)

class SubscriptionManager:
    """Manage user subscriptions with 3 tiers"""
    def __init__(self):
        self.subscriptions_file = 'subscriptions.json'
        self.subscriptions = {}
        self.mongo = None
        self._init_mongo()
        self.load_subscriptions()

    def _init_mongo(self):
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            self.mongo = client[MONGO_DB_NAME]
            logging.info('✅ MongoDB connected')
        except Exception as e:
            logging.error(f'❌ MongoDB connect failed: {e}')
            self.mongo = None
    
    def load_subscriptions(self):
        """Load all subscriptions"""
        if self.mongo is not None:
            try:
                self.subscriptions = {}
                for doc in self.mongo.subscriptions.find({}):
                    uid = str(doc['_id'])
                    self.subscriptions[uid] = {k:v for k,v in doc.items() if k != '_id'}
                logging.info(f"✅ Loaded {len(self.subscriptions)} subscriptions from MongoDB")
                return
            except Exception as e:
                logging.error(f"❌ Error loading subscriptions from MongoDB: {e}")
        if os.path.exists(self.subscriptions_file):
            try:
                with open(self.subscriptions_file, 'r') as f:
                    self.subscriptions = json.load(f)
                logging.info(f"✅ Loaded {len(self.subscriptions)} subscriptions")
            except Exception as e:
                logging.error(f"❌ Error loading subscriptions: {e}")
    
    def save_subscriptions(self):
        """Save all subscriptions"""
        try:
            with open(self.subscriptions_file, 'w') as f:
                json.dump(self.subscriptions, f, indent=2)
        except Exception as e:
            logging.error(f"❌ Error saving subscriptions: {e}")
        if self.mongo is not None:
            try:
                for uid, sub in self.subscriptions.items():
                    self.mongo.subscriptions.update_one({'_id': uid}, {'$set': sub}, upsert=True)
            except Exception as e:
                logging.error(f"❌ Error saving subscriptions to MongoDB: {e}")
    
    def add_subscription(self, user_id, days=30, tier='basic'):
        """Add or extend subscription with tier"""
        user_id_str = str(user_id)
        now = datetime.now()
        
        if user_id_str in self.subscriptions:
            current_expiry = datetime.fromisoformat(self.subscriptions[user_id_str]['expiry'])
            if current_expiry > now:
                new_expiry = current_expiry + timedelta(days=days)
            else:
                new_expiry = now + timedelta(days=days)
        else:
            new_expiry = now + timedelta(days=days)
        
        self.subscriptions[user_id_str] = {
            'expiry': new_expiry.isoformat(),
            'activated_on': now.isoformat(),
            'status': 'active',
            'is_trial': False,
            'tier': tier,
            'days': days
        }
        self.save_subscriptions()
        logging.info(f"✅ {tier.upper()} Subscription added for user {user_id} until {new_expiry}")
        return new_expiry
    
    def add_trial(self, user_id, days=1):
        """Add free trial"""
        user_id_str = str(user_id)
        if user_id_str in self.subscriptions:
            return None
        
        now = datetime.now()
        new_expiry = now + timedelta(days=days)
        
        self.subscriptions[user_id_str] = {
            'expiry': new_expiry.isoformat(),
            'activated_on': now.isoformat(),
            'status': 'active',
            'is_trial': True,
            'tier': 'basic',
            'days': days
        }
        self.save_subscriptions()
        logging.info(f"🎁 Trial added for user {user_id} until {new_expiry}")
        return new_expiry
    
    def is_subscribed(self, user_id):
        """Check if user has active subscription"""
        user_id_str = str(user_id)
        if user_id_str not in self.subscriptions:
            return False
        
        expiry = datetime.fromisoformat(self.subscriptions[user_id_str]['expiry'])
        return datetime.now() < expiry
    
    def get_tier(self, user_id):
        """Get user subscription tier"""
        user_id_str = str(user_id)
        if user_id_str not in self.subscriptions:
            return None
        return self.subscriptions[user_id_str].get('tier', 'basic')
    
    def can_access_feature(self, user_id, feature):
        """Check if user can access specific feature based on tier"""
        tier = self.get_tier(user_id)
        if not tier:
            return False
        
        feature_access = {
            'basic': ['big_small_predictions', 'single_channel', 'basic_templates'],
            'premium': ['big_small_predictions', 'color_predictions', 'multiple_channels', 'custom_templates', 'multiple_media', 'language_support', 'custom_session'],
            'vip': ['big_small_predictions', 'color_predictions', 'multiple_channels', 'custom_templates', 'multiple_media', 'language_support', 'advanced_analytics', 'custom_branding', 'custom_session']
        }
        
        return feature in feature_access.get(tier, [])
    
    def get_expiry(self, user_id):
        """Get subscription expiry date"""
        user_id_str = str(user_id)
        if user_id_str not in self.subscriptions:
            return None
        return datetime.fromisoformat(self.subscriptions[user_id_str]['expiry'])
    
    def days_remaining(self, user_id):
        """Get days remaining in subscription"""
        user_id_str = str(user_id)
        if user_id_str not in self.subscriptions:
            return 0
        
        expiry = datetime.fromisoformat(self.subscriptions[user_id_str]['expiry'])
        delta = expiry - datetime.now()
        return max(0, delta.days)
    
    def is_trial(self, user_id):
        """Check if user is on trial"""
        user_id_str = str(user_id)
        if user_id_str not in self.subscriptions:
            return False
        return self.subscriptions[user_id_str].get('is_trial', False)

    def merge_to_mongo(self, users=None, settings=None, admins=None):
        if self.mongo is None:
            return
        try:
            for uid, sub in self.subscriptions.items():
                self.mongo.subscriptions.update_one({'_id': uid}, {'$set': sub}, upsert=True)
            if users:
                for uid, u in users.items():
                    self.mongo.users.update_one({'_id': str(uid)}, {'$set': u.to_dict()}, upsert=True)
            if settings is not None:
                self.mongo.meta.update_one({'_id': 'settings'}, {'$set': settings}, upsert=True)
            if admins is not None:
                self.mongo.meta.update_one({'_id': 'admins'}, {'$set': {'admin_ids': admins}}, upsert=True)
        except Exception as e:
            logging.error(f'❌ Mongo merge failed: {e}')
    
    def remove_subscription(self, user_id):
        """Remove user subscription"""
        user_id_str = str(user_id)
        if user_id_str in self.subscriptions:
            del self.subscriptions[user_id_str]
            self.save_subscriptions()
            logging.info(f"❌ Subscription removed for user {user_id}")

class UserConfig:
    """Individual user configuration and state with advanced features"""
    def __init__(self, user_id, user_name=""):
        self.user_id = user_id
        self.user_name = user_name
        self.channels = []
        self.api_url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
        self.base_price = 10
        self.register_link = "https://your-registration-link.com"

        # Enhanced Media Support - Separate media for each type
        self.win_media_ids = []
        self.lose_media_ids = []

        # Separate media for BIG/SMALL predictions
        self.big_media_ids = []
        self.small_media_ids = []

        # Separate media for Color predictions
        self.red_media_ids = []
        self.green_media_ids = []

        # Prediction Type Settings
        self.prediction_type = {}
        self.use_table_format = True
        self.max_table_rows = 10
        self.banner_image = f"user_banners/banner_{user_id}.jpg"

        # Language Settings
        self.language = 'en'

        # Templates
        self.prediction_template = LANGUAGES['en']['templates']['prediction']
        self.win_template = LANGUAGES['en']['templates']['win']
        self.lose_template = LANGUAGES['en']['templates']['lose']

        # Prediction state
        self.is_active = False
        self.last_processed_period = None
        self.current_multiplier = 1
        self.current_price = self.base_price
        self.multipliers = {}
        self.prices = {}
        self.predictions = {}
        self.prediction_tables = {}
        self.table_counter = 0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.prediction_history = []
        self.last_10_results = []
        self.pattern_memory = []

        # Performance optimization
        self.last_api_call = None
        self.cached_data = None
        self.data_cache_time = 1

        # Custom Session Features (Premium only)
        self.custom_session_enabled = False  # 24/7 or custom session
        self.custom_session_duration = 60  # Duration in minutes
        self.custom_session_active = False
        self.custom_session_start_time = None
        self.custom_session_channel = None  # Channel for custom session

        # Custom Session Messages and Media
        self.custom_session_start_message = "🎯 <b>CUSTOM SESSION STARTED</b>\n\nSession Duration: {duration} minutes\nChannel: {channel}\n\nGood luck! 🍀"
        self.custom_session_end_message = "⏰ <b>CUSTOM SESSION ENDED</b>\n\nSession completed after {duration} minutes.\n\nResults summary will be shown."
        self.custom_session_start_media = []  # Multiple media for session start
        self.custom_session_end_media = []   # Multiple media for session end

        # Extra Messages for Custom Sessions
        self.extra_messages = []  # List of extra messages with timing and media

        # Template disable options
        self.disable_win_template = False
        self.disable_lose_template = False

        # Custom session tracking
        self.custom_session_last_win = None  # Track last win for session ending
        
        # Preload fonts
        self.fonts = {}
        try:
            self.fonts['header'] = ImageFont.truetype("arialbd.ttf", 12)
            self.fonts['cell'] = ImageFont.truetype("arialbd.ttf", 10)
            self.fonts['result'] = ImageFont.truetype("arialbd.ttf", 8)
        except:
            try:
                self.fonts['header'] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                self.fonts['cell'] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                self.fonts['result'] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8)
            except:
                self.fonts['header'] = ImageFont.load_default()
                self.fonts['cell'] = ImageFont.load_default()
                self.fonts['result'] = ImageFont.load_default()

    def to_dict(self):
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'channels': self.channels,
            'api_url': self.api_url,
            'base_price': self.base_price,
            'register_link': self.register_link,
            'win_media_ids': self.win_media_ids,
            'lose_media_ids': self.lose_media_ids,
            'big_media_ids': self.big_media_ids,
            'small_media_ids': self.small_media_ids,
            'red_media_ids': self.red_media_ids,
            'green_media_ids': self.green_media_ids,
            'prediction_type': self.prediction_type,
            'use_table_format': self.use_table_format,
            'max_table_rows': self.max_table_rows,
            'banner_image': self.banner_image,
            'language': 'en',
            'prediction_template': self.prediction_template,
            'win_template': self.win_template,
            'lose_template': self.lose_template,
            'is_active': self.is_active,
            'prediction_tables': self.prediction_tables,
            'multipliers': self.multipliers,
            'prices': self.prices,
            # Custom Session Features
            'custom_session_enabled': self.custom_session_enabled,
            'custom_session_duration': self.custom_session_duration,
            'custom_session_active': self.custom_session_active,
            'custom_session_start_time': self.custom_session_start_time.isoformat() if self.custom_session_start_time else None,
            'custom_session_channel': self.custom_session_channel,
            'custom_session_start_message': self.custom_session_start_message,
            'custom_session_end_message': self.custom_session_end_message,
            'custom_session_start_media': self.custom_session_start_media,
            'custom_session_end_media': self.custom_session_end_media,
            'extra_messages': self.extra_messages,
            'disable_win_template': self.disable_win_template,
            'disable_lose_template': self.disable_lose_template
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        config = cls(data['user_id'], data.get('user_name', ''))
        config.channels = data.get('channels', [])
        config.base_price = data.get('base_price', 10)
        config.register_link = data.get('register_link', 'https://your-registration-link.com')
        config.win_media_ids = data.get('win_media_ids', [])
        config.lose_media_ids = data.get('lose_media_ids', [])
        config.big_media_ids = data.get('big_media_ids', [])
        config.small_media_ids = data.get('small_media_ids', [])
        config.red_media_ids = data.get('red_media_ids', [])
        config.green_media_ids = data.get('green_media_ids', [])
        config.prediction_type = data.get('prediction_type', {})
        config.use_table_format = data.get('use_table_format', True)
        config.max_table_rows = data.get('max_table_rows', 10)
        config.banner_image = data.get('banner_image', f"user_banners/banner_{data['user_id']}.jpg")
        config.language = data.get('language', 'en')
        config.is_active = data.get('is_active', False)
        config.prediction_template = data.get('prediction_template', LANGUAGES['en']['templates']['prediction'])
        config.win_template = data.get('win_template', LANGUAGES['en']['templates']['win'])
        config.lose_template = data.get('lose_template', LANGUAGES['en']['templates']['lose'])
        config.current_price = config.base_price
        config.prediction_tables = data.get('prediction_tables', {})

        # Load custom session features
        config.custom_session_enabled = data.get('custom_session_enabled', False)
        config.custom_session_duration = data.get('custom_session_duration', 60)
        config.custom_session_active = data.get('custom_session_active', False)
        if data.get('custom_session_start_time'):
            config.custom_session_start_time = datetime.fromisoformat(data['custom_session_start_time'])
        config.custom_session_channel = data.get('custom_session_channel', None)
        config.custom_session_start_message = data.get('custom_session_start_message', "🎯 <b>CUSTOM SESSION STARTED</b>\n\nSession Duration: {duration} minutes\nChannel: {channel}\n\nGood luck! 🍀")
        config.custom_session_end_message = data.get('custom_session_end_message', "⏰ <b>CUSTOM SESSION ENDED</b>\n\nSession completed after {duration} minutes.\n\nResults summary will be shown.")
        config.custom_session_start_media = data.get('custom_session_start_media', [])
        config.custom_session_end_media = data.get('custom_session_end_media', [])
        config.extra_messages = data.get('extra_messages', [])
        config.disable_win_template = data.get('disable_win_template', False)
        config.disable_lose_template = data.get('disable_lose_template', False)

        return config
    
    def reset_state(self):
        """Reset prediction state to fresh start"""
        self.last_processed_period = None
        self.current_multiplier = 1
        self.current_price = self.base_price
        self.multipliers = {}
        self.prices = {}
        self.predictions = {}
        self.prediction_tables = {}
        self.table_counter = 0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.prediction_history = []
        self.last_10_results = []
        self.pattern_memory = []
        logging.info(f"🔄 Reset state for user {self.user_id}")
    
    def clear_user_data(self):
        """Clear all user data completely"""
        self.reset_state()
        self.channels = []
        self.base_price = 10
        self.register_link = "https://your-registration-link.com"
        self.win_media_ids = []
        self.lose_media_ids = []
        self.big_media_ids = []
        self.small_media_ids = []
        self.red_media_ids = []
        self.green_media_ids = []
        self.use_table_format = True
        self.max_table_rows = 10
        self.language = 'en'

        # Clear custom session data
        self.custom_session_enabled = False
        self.custom_session_duration = 60
        self.custom_session_active = False
        self.custom_session_start_time = None
        self.custom_session_channel = None
        self.custom_session_start_message = "🎯 <b>CUSTOM SESSION STARTED</b>\n\nSession Duration: {duration} minutes\nChannel: {channel}\n\nGood luck! 🍀"
        self.custom_session_end_message = "⏰ <b>CUSTOM SESSION ENDED</b>\n\nSession completed after {duration} minutes.\n\nResults summary will be shown."
        self.custom_session_start_media = []
        self.custom_session_end_media = []
        self.extra_messages = []
        self.disable_win_template = False
        self.disable_lose_template = False

        # Remove banner file if exists
        if os.path.exists(self.banner_image):
            try:
                os.remove(self.banner_image)
            except:
                pass

        logging.info(f"🗑️ Cleared all data for user {self.user_id}")

class WinGoBotMultiUser:
    def __init__(self, token):
        self.token = token
        self.users_file = 'users_config.json'
        self.admin_file = 'admin_config.json'
        self.settings_file = 'bot_settings.json'
        self.log_channel = '@testing4571'
        self.default_banner_folder = 'banner'
        self.default_banner = 'banner/banner.jpg'
        self.users = {}
        self.user_state = {}
        self.admin_ids = []
        self.subscription_manager = SubscriptionManager()
        self.reminder_task_started = False
        
        # Performance optimization
        self.global_data_cache = None
        self.global_cache_time = None
        self.cache_duration = 1
        
        # Rate limiting
        self.rate_limit_delay = 0.1
        self.max_retries = 2
        self.retry_delay = 0.5
        
        # Bot settings
        self.settings = {
            'mandatory_channel': '@YourChannel',
            'subscription_enabled': True,
            'basic_price': 299,
            'premium_price': 599,
            'vip_price': 999,
            'subscription_days': 30,
            'trial_days': 1,
            'payment_upi': 'yourname@paytm',
            'log_channel': '@YourLogChannel',
            'default_register_link': 'https://your-registration-link.com'
        }
        
        self.load_data()
        self.initialize_default_banner()
        
    def initialize_default_banner(self):
        """Initialize default banner in banner folder"""
        try:
            if os.path.exists(self.default_banner_folder):
                banner_files = [f for f in os.listdir(self.default_banner_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                
                if banner_files:
                    self.default_banner = os.path.join(self.default_banner_folder, banner_files[0])
                    logging.info(f"✅ Found default banner: {self.default_banner}")
                else:
                    self.default_banner = os.path.join(self.default_banner_folder, "banner.jpg")
                    self.create_default_banner(self.default_banner)
                    logging.info(f"✅ Created default banner: {self.default_banner}")
            else:
                os.makedirs(self.default_banner_folder, exist_ok=True)
                self.default_banner = os.path.join(self.default_banner_folder, "banner.jpg")
                self.create_default_banner(self.default_banner)
                logging.info(f"✅ Created banner folder and default banner: {self.default_banner}")
                
        except Exception as e:
            logging.error(f"❌ Error initializing default banner: {e}")
            self.default_banner = "user_banners/default_banner.jpg"
            self.create_default_banner(self.default_banner)
    
    def load_data(self):
        """Load all configurations"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    self.settings.update(json.load(f))
            except Exception as e:
                logging.error(f"❌ Error loading settings: {e}")
        else:
            self.save_settings()
        
        if os.path.exists(self.admin_file):
            try:
                with open(self.admin_file, 'r') as f:
                    data = json.load(f)
                    self.admin_ids = data.get('admin_ids', [8089603563, 8015937475])
            except Exception as e:
                logging.error(f"❌ Error loading admin config: {e}")
                self.admin_ids = [8089603563, 8015937475]
        else:
            self.admin_ids = [8089603563, 8015937475]
            self.save_admin_config()
        
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    for user_id_str, user_data in data.items():
                        user_id = int(user_id_str)
                        self.users[user_id] = UserConfig.from_dict(user_data)
                logging.info(f"✅ Loaded {len(self.users)} user configurations")
            except Exception as e:
                logging.error(f"❌ Error loading users: {e}")
    
    def save_settings(self):
        """Save bot settings"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logging.error(f"❌ Error saving settings: {e}")
    
    def save_user_config(self, user_id):
        """Save specific user configuration"""
        try:
            all_data = {}
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    all_data = json.load(f)
            
            all_data[str(user_id)] = self.users[user_id].to_dict()
            
            with open(self.users_file, 'w') as f:
                json.dump(all_data, f, indent=2)
            logging.info(f"💾 Saved config for user {user_id}")
        except Exception as e:
            logging.error(f"❌ Error saving user config: {e}")
    
    def save_admin_config(self):
        """Save admin configuration"""
        try:
            with open(self.admin_file, 'w') as f:
                json.dump({'admin_ids': self.admin_ids}, f, indent=2)
        except Exception as e:
            logging.error(f"❌ Error saving admin config: {e}")
    
    async def send_log(self, context: ContextTypes.DEFAULT_TYPE, message: str):
        """Send log to log channel"""
        try:
            await context.bot.send_message(
                chat_id=self.settings.get('log_channel', self.log_channel),
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"❌ Failed to send log: {e}")
    
    def get_or_create_user(self, user_id, user_name=""):
        """Get existing user config or create new one"""
        if user_id not in self.users:
            self.users[user_id] = UserConfig(user_id, user_name)
            user_banner_path = f"user_banners/banner_{user_id}.jpg"
            
            os.makedirs("user_banners", exist_ok=True)
            
            if not os.path.exists(user_banner_path):
                try:
                    if os.path.exists(self.default_banner):
                        shutil.copy(self.default_banner, user_banner_path)
                        logging.info(f"✅ Copied default banner to user banner: {user_banner_path}")
                    else:
                        self.create_default_banner(user_banner_path)
                        logging.info(f"✅ Created new user banner: {user_banner_path}")
                    
                    self.users[user_id].banner_image = user_banner_path
                    
                except Exception as e:
                    logging.error(f"❌ Error creating user banner: {e}")
                    self.create_default_banner(user_banner_path)
                    self.users[user_id].banner_image = user_banner_path
                    logging.info(f"✅ Created fallback user banner: {user_banner_path}")
                
            self.save_user_config(user_id)
        elif user_name and (not self.users[user_id].user_name or self.users[user_id].user_name != user_name):
            self.users[user_id].user_name = user_name
            self.save_user_config(user_id)
        return self.users[user_id]
    
    def create_default_banner(self, banner_path):
        """Create a default banner if it doesn't exist"""
        try:
            width, height = 470, 240
            image = Image.new('RGB', (width, height), color='#1a237e')
            draw = ImageDraw.Draw(image)
            
            # Create gradient background
            for i in range(height):
                ratio = i / height
                r = int(26 + (33 * ratio))
                g = int(35 + (150 * ratio))
                b = int(126 + (200 * ratio))
                draw.line([(0, i), (width, i)], fill=(r, g, b))
            
            # Add text
            try:
                font_large = ImageFont.truetype("arialbd.ttf", 24)
                font_small = ImageFont.truetype("arial.ttf", 14)
            except:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            draw.text((width//2, height//2 - 20), "AI PREDICTION SYSTEM", 
                     fill='white', font=font_large, anchor="mm")
            draw.text((width//2, height//2 + 20), "24/7 Live Predictions", 
                     fill='#bbdefb', font=font_small, anchor="mm")
            
            image.save(banner_path, format='JPEG', quality=85)
            logging.info(f"✅ Created default banner: {banner_path}")
        except Exception as e:
            logging.error(f"❌ Error creating default banner: {e}")
    
    async def check_channel_membership(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, channel_id: str) -> bool:
        """Check if user is member of channel with retry logic"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                if channel_id.startswith('@'):
                    chat_id = channel_id
                elif channel_id.startswith('-100'):
                    chat_id = int(channel_id)
                else:
                    chat_id = channel_id
                
                member = await context.bot.get_chat_member(
                    chat_id=chat_id,
                    user_id=user_id
                )
                return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.2)
                    logging.warning(f"⚠️ Membership check attempt {attempt + 1} failed for {channel_id}: {e}")
                else:
                    logging.error(f"❌ Error checking membership for {channel_id}: {e}")
                    return False
        return False
    
    def generate_upi_qr(self, amount):
        """Generate UPI QR code"""
        upi_id = self.settings.get('payment_upi', 'yourname@paytm')
        upi_string = f"upi://pay?pa={upi_id}&am={amount}&cu=INR&tn=Subscription Payment"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        os.makedirs("temp", exist_ok=True)
        qr_path = f"temp/upi_qr_{int(time.time())}.png"
        img.save(qr_path)
        return qr_path
    
    def get_big_small(self, num):
        """Determine if number is BIG or SMALL"""
        return 'SMALL' if num <= 4 else 'BIG'
    
    def get_color(self, num):
        """Determine color of number"""
        if num in [0, 2, 4, 6, 8]:
            return 'RED'
        else:
            return 'GREEN'
    
    async def fetch_live_data(self):
        """Optimized live data fetching with better error handling"""
        current_time = datetime.now()
        
        if (self.global_data_cache and self.global_cache_time and 
            (current_time - self.global_cache_time).total_seconds() < self.cache_duration):
            return self.global_data_cache
        
        url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://draw.ar-lottery01.com',
            'Referer': 'https://draw.ar-lottery01.com/',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            logging.warning(f"⚠️ API returned status {response.status}, attempt {attempt + 1}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(0.5)
                                continue
                            return None
                        
                        text_content = await response.text()
                        try:
                            data = json.loads(text_content)
                        except json.JSONDecodeError as e:
                            logging.warning(f"⚠️ JSON decode error, attempt {attempt + 1}: {e}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(0.5)
                                continue
                            return None
                        
                        if data.get('data') and data['data'].get('list'):
                            data_list = data['data']['list']
                            formatted_data = []
                            for item in data_list:
                                try:
                                    number_str = str(item.get('number', '0'))
                                    number_clean = ''.join(filter(str.isdigit, number_str))
                                    number = int(number_clean[0]) if number_clean else 0
                                    
                                    formatted_item = {
                                        'issueNumber': item.get('issueNumber'),
                                        'number': number,
                                        'color': self.get_color(number),
                                        'big_small': self.get_big_small(number),
                                        'premium': item.get('premium', ''),
                                        'sum': item.get('sum', '')
                                    }
                                    formatted_data.append(formatted_item)
                                except Exception as e:
                                    continue
                            
                            # Update cache
                            self.global_data_cache = formatted_data
                            self.global_cache_time = current_time
                            
                            logging.info(f"✅ API data fetched successfully: {len(formatted_data)} records")
                            return formatted_data if formatted_data else None
                        
                        return None
                    
            except asyncio.TimeoutError:
                logging.warning(f"⏰ API timeout, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
                return None
            except Exception as e:
                logging.warning(f"⚠️ API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
                return None
        
        return None
    
    def generate_random_prediction(self, user_config, prediction_type='big_small', channel_id=None):
        """Generate prediction based on type"""
        current_time = int(time.time() * 1000)
        unique_seed = current_time + user_config.user_id + (hash(channel_id) if channel_id else 0)
        
        local_random = random.Random(unique_seed)
        
        if prediction_type == 'color':
            choice = local_random.choice(['RED', 'GREEN'])
        else:
            choice = 'BIG' if local_random.random() > 0.5 else 'SMALL'
        
        logging.info(f"[User {user_config.user_id}] 🎲 Channel {channel_id} {prediction_type.upper()} prediction: {choice}")
        return choice
    
    def generate_adaptive_prediction(self, user_config, data, prediction_type='big_small', channel_id=None):
        """Generate adaptive prediction based on recent patterns"""
        return self.generate_random_prediction(user_config, prediction_type, channel_id)
    
    def get_next_period(self, current_period):
        """Get next period number"""
        try:
            return str(int(current_period) + 1)
        except:
            import re
            numbers = re.findall(r'\d+', current_period)
            return str(int(numbers[-1]) + 1) if numbers else "000001"
    
    def format_message(self, template, data):
        """Format message with data"""
        message = template
        for key, value in data.items():
            message = message.replace(f'{{{key}}}', str(value))
        return message
    
    def cleanup_memory(self):
        """Clean up memory and temporary files"""
        try:
            temp_files = glob.glob("temp/*.png")
            if len(temp_files) > 30:
                temp_files.sort(key=os.path.getctime)
                for old_file in temp_files[:-30]:
                    try:
                        os.remove(old_file)
                    except:
                        pass
            
            gc.collect()
            
        except Exception as e:
            logging.error(f"❌ Memory cleanup error: {e}")
    
    def generate_prediction_table_image(self, user_config, channel):
        """Enhanced prediction table image generation with colors and language support"""
        table = user_config.prediction_tables.get(channel, [])
        if not table:
            return None

        try:
            width = 470
            banner_height = 240
            header_height = 24
            row_height = 28
            table_rows = min(len(table), 10)
            table_height = header_height + (table_rows * row_height)
            total_height = banner_height + table_height

            image = Image.new('RGB', (width, total_height), color='#ffffff')
            draw = ImageDraw.Draw(image)

            header_font = user_config.fonts['header']
            cell_font = user_config.fonts['cell']
            result_font = user_config.fonts['result']

            # Load banner
            banner_path = user_config.banner_image
            
            banner_loaded = False
            if os.path.exists(banner_path):
                try:
                    banner = Image.open(banner_path)
                    banner = banner.resize((width, banner_height), Image.Resampling.LANCZOS)
                    image.paste(banner, (0, 0))
                    banner_loaded = True
                except Exception as e:
                    logging.error(f"❌ Error loading user banner {banner_path}: {e}")
                    banner_loaded = False
            
            if not banner_loaded and os.path.exists(self.default_banner):
                try:
                    banner = Image.open(self.default_banner)
                    banner = banner.resize((width, banner_height), Image.Resampling.LANCZOS)
                    image.paste(banner, (0, 0))
                    banner_loaded = True
                except Exception as e:
                    logging.error(f"❌ Error loading default banner {self.default_banner}: {e}")
                    banner_loaded = False
            
            if not banner_loaded:
                for i in range(banner_height):
                    ratio = i / banner_height
                    r = int(5 + (20 * ratio))
                    g = int(20 + (50 * ratio))
                    b = int(40 + (80 * ratio))
                    draw.line([(0, i), (width, i)], fill=(r, g, b))

            table_y = banner_height

            # Draw header
            draw.rectangle([(0, table_y), (width, table_y + header_height)], fill='#001f5c')
            
            # Header texts
            headers = ["PERIOD", "INVESTMENT", "AMOUNT", "RESULT"]
                
            header_x_positions = [80, 220, 322, 425]

            for header, x_pos in zip(headers, header_x_positions):
                text_bbox = draw.textbbox((0, 0), header, font=header_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_x = x_pos - (text_width // 2)
                draw.text((text_x, table_y + (header_height // 2) - 5), header,
                         fill='white', font=header_font)

            separator_positions = [161, 282, 363]

            # Draw rows with color coding
            recent_table = table[-10:] if len(table) > 10 else table
            
            for row_idx, row in enumerate(recent_table):
                y = table_y + header_height + (row_idx * row_height)

                bg_color = '#f8f9fa' if row_idx % 2 == 0 else '#ffffff'
                draw.rectangle([(0, y), (width, y + row_height)], fill=bg_color)
                draw.line([(0, y), (width, y)], fill='#141414', width=1)

                for sep_x in separator_positions:
                    draw.line([(sep_x, y), (sep_x, y + row_height)], fill='#141414', width=1)

                cell_y = y + (row_height // 2) - 4

                # Period
                text = str(row['period'])
                text_bbox = draw.textbbox((0, 0), text, font=cell_font)
                text_width = text_bbox[2] - text_bbox[0]
                draw.text((80 - (text_width // 2), cell_y), text, fill='#000000', font=cell_font)

                # Investment with color coding
                investment = row['investment']
                text = str(investment)
                text_bbox = draw.textbbox((0, 0), text, font=cell_font)
                text_width = text_bbox[2] - text_bbox[0]
                
                # Color code the investment
                prediction_type = user_config.prediction_type.get(channel, 'big_small')
                
                if prediction_type == 'color':
                    if investment == 'RED':
                        text_color = '#dc3545'
                    elif investment == 'GREEN':
                        text_color = '#28a745'
                    else:
                        text_color = '#000000'
                else:
                    if investment == 'BIG':
                        text_color = '#007bff'
                    elif investment == 'SMALL':
                        text_color = '#6c757d'
                    else:
                        text_color = '#000000'
                
                draw.text((220 - (text_width // 2), cell_y), text, fill=text_color, font=cell_font)

                # Amount
                text = f"₹{row['amount']}"
                text_bbox = draw.textbbox((0, 0), text, font=cell_font)
                text_width = text_bbox[2] - text_bbox[0]
                draw.text((322 - (text_width // 2), cell_y), text, fill='#000000', font=cell_font)

                # Result with filled boxes
                result = row['result']
                if result == 'WIN':
                    pill_width = 40
                    pill_height = 16
                    pill_x = 425 - (pill_width // 2)
                    pill_y = y + (row_height // 2) - (pill_height // 2)
                    draw.rounded_rectangle(
                        [(pill_x, pill_y), (pill_x + pill_width, pill_y + pill_height)],
                        radius=8, fill='#28a745'
                    )
                    text_bbox = draw.textbbox((0, 0), result, font=result_font)
                    text_width = text_bbox[2] - text_bbox[0]
                    draw.text((425 - (text_width // 2), pill_y + 4), result, fill='white', font=result_font)

                elif result == 'LOSE':
                    pill_width = 40
                    pill_height = 16
                    pill_x = 425 - (pill_width // 2)
                    pill_y = y + (row_height // 2) - (pill_height // 2)
                    draw.rounded_rectangle(
                        [(pill_x, pill_y), (pill_x + pill_width, pill_y + pill_height)],
                        radius=8, fill='#dc3545'
                    )
                    text_bbox = draw.textbbox((0, 0), result, font=result_font)
                    text_width = text_bbox[2] - text_bbox[0]
                    draw.text((425 - (text_width // 2), pill_y + 4), result, fill='white', font=result_font)

            img_bytes = BytesIO()
            image.save(img_bytes, format='PNG', quality=95, optimize=True)
            img_bytes.seek(0)

            return img_bytes

        except Exception as e:
            logging.error(f"❌ Error generating table image: {e}")
            return None
    
    def add_prediction_to_table(self, user_config, period, choice, amount, channel, result):
        """Add prediction to history table"""
        table = user_config.prediction_tables.setdefault(channel, [])
        
        if len(table) >= user_config.max_table_rows:
            user_config.prediction_tables[channel] = table[-user_config.max_table_rows + 1:]
        
        table.append({
            'period': period,
            'investment': choice,
            'amount': amount,
            'result': result
        })
    
    def update_prediction_result(self, user_config, period, is_win, channel):
        """Update prediction result in table"""
        table = user_config.prediction_tables.get(channel, [])
        prediction_updated = False
        for prediction in table:
            if prediction['period'] == period and prediction['result'] == 'PENDING':
                prediction['result'] = 'WIN' if is_win else 'LOSE'
                user_config.table_counter += 1
                prediction_updated = True
                
                if is_win:
                    user_config.consecutive_wins += 1
                    user_config.consecutive_losses = 0
                else:
                    user_config.consecutive_losses += 1
                    user_config.consecutive_wins = 0
                break
        
        if prediction_updated:
            logging.info(f"[User {user_config.user_id}] Updated period {period}: {'WIN' if is_win else 'LOSE'}")
    
    async def send_message_with_retry(self, context, chat_id, text=None, photo_data=None, animation=None, parse_mode=None, max_retries=2):
        """Send message with retry logic"""
        message_obj = None
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(self.rate_limit_delay)

                if photo_data:
                    if isinstance(photo_data, BytesIO):
                        photo_data.seek(0)
                        message_obj = await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo_data,
                            caption=text,
                            parse_mode=parse_mode
                        )
                    elif isinstance(photo_data, str) and os.path.exists(photo_data):
                        with open(photo_data, 'rb') as photo:
                            message_obj = await context.bot.send_photo(
                                chat_id=chat_id,
                                photo=photo,
                                caption=text,
                                parse_mode=parse_mode
                            )
                elif animation:
                    message_obj = await context.bot.send_animation(
                        chat_id=chat_id,
                        animation=animation,
                        caption=text,
                        parse_mode=parse_mode
                    )
                else:
                    message_obj = await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode,
                        disable_web_page_preview=True
                    )
                
                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logging.warning(f"⚠️ Send attempt {attempt + 1} failed for {chat_id}, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logging.error(f"❌ Failed to send to {chat_id} after {max_retries} attempts: {e}")
                    return False
        return False
    
    async def send_media_sequence(self, context, chat_id, media_ids, text=None, parse_mode=None):
        """Send multiple media in sequence"""
        if not media_ids:
            return
        
        for media_id in media_ids:
            try:
                await self.send_message_with_retry(
                    context, chat_id, animation=media_id
                )
                await asyncio.sleep(0.2)
            except Exception as e:
                logging.error(f"❌ Failed to send media: {e}")
        
        if text:
            await self.send_message_with_retry(
                context, chat_id, text=text, parse_mode=parse_mode
            )
    
    async def send_prediction(self, context: ContextTypes.DEFAULT_TYPE, user_config, period, choice, channel):
        """Send prediction with appropriate media based on prediction type"""
        logging.info(f"[User {user_config.user_id}] 📤 Sending prediction for period {period} to {channel}: {choice}")

        multiplier = user_config.multipliers.get(channel, 1)
        price = user_config.prices.get(channel, user_config.base_price)
        prediction_type = user_config.prediction_type.get(channel, 'big_small')

        # Generate prediction content
        if user_config.use_table_format and user_config.prediction_tables.get(channel):
            image_data = self.generate_prediction_table_image(user_config, channel)
            caption = self.format_message(user_config.prediction_template, {
                'period': period,
                'choice': choice,
                'multiplier': multiplier,
                'price': price,
                'register_link': user_config.register_link
            })
        else:
            image_data = None
            caption = self.format_message(user_config.prediction_template, {
                'period': period,
                'choice': choice,
                'multiplier': multiplier,
                'price': price,
                'register_link': user_config.register_link
            })

        # Send main prediction message FIRST
        if image_data:
            success = await self.send_message_with_retry(
                context, channel, text=caption,
                photo_data=image_data, parse_mode=ParseMode.HTML
            )
            if image_data and hasattr(image_data, 'close'):
                image_data.close()
        else:
            success = await self.send_message_with_retry(
                context, channel, text=caption,
                parse_mode=ParseMode.HTML
            )

        # Send appropriate media based on prediction type and choice AFTER prediction
        if success:
            if prediction_type == 'big_small':
                if choice == 'BIG' and user_config.big_media_ids:
                    await self.send_media_sequence(context, channel, user_config.big_media_ids)
                elif choice == 'SMALL' and user_config.small_media_ids:
                    await self.send_media_sequence(context, channel, user_config.small_media_ids)
            elif prediction_type == 'color':
                if choice == 'RED' and user_config.red_media_ids:
                    await self.send_media_sequence(context, channel, user_config.red_media_ids)
                elif choice == 'GREEN' and user_config.green_media_ids:
                    await self.send_media_sequence(context, channel, user_config.green_media_ids)

        if success:
            if channel not in user_config.predictions:
                user_config.predictions[channel] = {}
            user_config.predictions[channel][period] = {
                'choice': choice,
                'amount': price,
                'sent_time': datetime.now(),
                'type': prediction_type
            }
            logging.info(f"[User {user_config.user_id}] ✅ Prediction sent to {channel}")
            return True
        else:
            logging.error(f"[User {user_config.user_id}] ❌ Failed to send to {channel}")
            return False
    
    async def send_result(self, context: ContextTypes.DEFAULT_TYPE, user_config, is_win, period, result, channel):
        """Send result with media sequences and language support"""
        # Check if templates should be disabled
        if (is_win and user_config.disable_win_template) or (not is_win and user_config.disable_lose_template):
            text = None  # Don't send template message
        else:
            template = user_config.win_template if is_win else user_config.lose_template
            text = self.format_message(template, {'period': period, 'result': result})

        completed_predictions = sum(1 for p in user_config.prediction_tables.get(channel, []) if p['result'] != 'PENDING')

        # Generate table image if needed
        image_data = None
        if completed_predictions >= user_config.max_table_rows:
            image_data = self.generate_prediction_table_image(user_config, channel)

        # Send win/loss media sequence
        if is_win and user_config.win_media_ids:
            await self.send_media_sequence(context, channel, user_config.win_media_ids)
        elif not is_win and user_config.lose_media_ids:
            await self.send_media_sequence(context, channel, user_config.lose_media_ids)

        # Send result message only if not disabled
        if text:
            if image_data:
                await self.send_message_with_retry(
                    context, channel, text=text,
                    photo_data=image_data, parse_mode=ParseMode.HTML
                )
                if image_data and hasattr(image_data, 'close'):
                    image_data.close()
            else:
                await self.send_message_with_retry(
                    context, channel, text=text,
                    parse_mode=ParseMode.HTML
                )

        # Clear table after completion
        if completed_predictions >= user_config.max_table_rows:
            logging.info(f"[User {user_config.user_id}] 🎯 Sent completed table with {completed_predictions} predictions to {channel}")
            user_config.prediction_tables[channel] = []
            self.save_user_config(user_config.user_id)
    
    async def process_pending_predictions(self, context: ContextTypes.DEFAULT_TYPE, user_config, data):
        """Process pending predictions and check results"""
        if not data:
            return
        
        latest = data[0]
        latest_period = latest.get('issueNumber')
        
        if not latest_period:
            return
        
        for channel in list(user_config.predictions.keys()):
            if channel in user_config.predictions and latest_period in user_config.predictions[channel]:
                prediction = user_config.predictions[channel][latest_period]
                result_number = latest['number']
                
                # Determine result based on prediction type
                if prediction.get('type') == 'color':
                    result = self.get_color(result_number)
                else:
                    result = self.get_big_small(result_number)
                
                is_win = prediction['choice'] == result
                
                # Update the result
                self.update_prediction_result(user_config, latest_period, is_win, channel)
                await self.send_result(context, user_config, is_win, latest_period, result, channel)

                # Track win for custom session logic
                if is_win:
                    user_config.custom_session_last_win = 'WIN'
                else:
                    user_config.custom_session_last_win = 'LOSE'

                # Update channel-specific multiplier and price
                if is_win:
                    user_config.multipliers[channel] = 1
                    user_config.prices[channel] = user_config.base_price
                    logging.info(f"[User {user_config.user_id}] ✅ WIN - Reset to base for {channel}")
                else:
                    current_multiplier = user_config.multipliers.get(channel, 1)
                    if current_multiplier >= 8:
                        user_config.multipliers[channel] = 1
                        user_config.prices[channel] = user_config.base_price
                        logging.info(f"[User {user_config.user_id}] ⚠️ LOSS - Capped at 8x, RESET for {channel}")
                    else:
                        user_config.multipliers[channel] = current_multiplier * 2
                        user_config.prices[channel] = user_config.prices.get(channel, user_config.base_price) * 2
                        logging.info(f"[User {user_config.user_id}] ❌ LOSS - Increase to {user_config.multipliers[channel]}x for {channel}")

                # Remove from pending predictions
                del user_config.predictions[channel][latest_period]
                logging.info(f"[User {user_config.user_id}] Processed result for {latest_period} on {channel}: {'WIN' if is_win else 'LOSE'}")
    
    async def user_prediction_loop(self, context: ContextTypes.DEFAULT_TYPE, user_id):
        """Main user prediction loop"""
        user_config = self.users[user_id]
        logging.info(f"[User {user_id}] 🚀 Prediction loop started")
        
        last_data_fetch = None
        cached_data = None
        consecutive_failures = 0
        max_consecutive_failures = 5
        cleanup_counter = 0
        
        while user_config.is_active:
            try:
                # Check subscription
                if (self.settings.get('subscription_enabled') and 
                    user_id not in self.admin_ids and 
                    not self.subscription_manager.is_subscribed(user_id)):
                    
                    user_config.is_active = False
                    self.save_user_config(user_id)
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="❌ <b>Subscription Expired</b>\n\nYour subscription period has concluded. Please renew to continue receiving predictions.",
                        parse_mode=ParseMode.HTML
                    )
                    await self.send_log(context, f"❌ <b>Subscription Expired</b>\nUser: {user_config.user_name} (ID: {user_id})")
                    break
                
                # Fetch data with caching
                current_time = datetime.now()
                if (not last_data_fetch or 
                    (current_time - last_data_fetch).total_seconds() > self.cache_duration or
                    not cached_data):
                    
                    data = await self.fetch_live_data()
                    last_data_fetch = current_time
                    cached_data = data
                    
                    if data:
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            logging.error(f"[User {user_id}] Too many API failures, pausing for 3 seconds")
                            await asyncio.sleep(3)
                            consecutive_failures = 0
                        continue
                else:
                    data = cached_data
                
                if not data:
                    await asyncio.sleep(0.5)
                    continue
                
                # Process pending predictions first
                await self.process_pending_predictions(context, user_config, data)
                
                # Check custom session logic
                current_time = datetime.now()

                # Handle custom session ending conditions
                if user_config.custom_session_enabled and user_config.custom_session_active:
                    if user_config.custom_session_start_time:
                        session_duration = timedelta(minutes=user_config.custom_session_duration)
                        session_end_time = user_config.custom_session_start_time + session_duration

                        # Check if session should end due to time limit
                        if current_time >= session_end_time:
                            # Check if last prediction was win - if yes, continue until loss
                            if user_config.custom_session_last_win and user_config.custom_session_last_win == 'WIN':
                                logging.info(f"[User {user_id}] ⏰ Session time up but last prediction was WIN - continuing until loss")
                            else:
                                # End session
                                await self.end_custom_session(context, user_config, "time_limit")
                                continue
                        else:
                            # Session still active
                            logging.info(f"[User {user_id}] 🎯 Custom session active - {user_config.custom_session_duration} min session")

                # New prediction
                latest = data[0]
                latest_period = latest.get('issueNumber')

                if latest_period and latest_period != user_config.last_processed_period:
                    next_period = self.get_next_period(latest_period)

                    # Check if we should send predictions (normal mode or custom session mode)
                    should_send_predictions = True

                    if user_config.custom_session_enabled and user_config.custom_session_active:
                        # Only send to custom session channel
                        if user_config.custom_session_channel and user_config.custom_session_channel in user_config.channels:
                            channels_to_predict = [user_config.custom_session_channel]
                        else:
                            should_send_predictions = False
                    else:
                        # Normal mode - send to all channels
                        channels_to_predict = user_config.channels

                    if should_send_predictions and channels_to_predict:
                        prediction_tasks = []
                        for channel in channels_to_predict:
                            if (channel in user_config.predictions and
                                next_period in user_config.predictions[channel]):
                                continue

                            # Get prediction type for this channel
                            prediction_type = user_config.prediction_type.get(channel, 'big_small')

                            # Check if user has access to this prediction type
                            if prediction_type == 'color' and not self.subscription_manager.can_access_feature(user_id, 'color_predictions'):
                                prediction_type = 'big_small'

                            choice = self.generate_adaptive_prediction(user_config, data, prediction_type, channel)
                            price_for_channel = user_config.prices.get(channel, user_config.base_price)
                            self.add_prediction_to_table(user_config, next_period, choice, price_for_channel, channel, 'PENDING')

                            task = self.send_prediction(context, user_config, next_period, choice, channel)
                            prediction_tasks.append(task)

                        # Send predictions with controlled concurrency
                        if prediction_tasks:
                            batch_size = 2
                            for i in range(0, len(prediction_tasks), batch_size):
                                batch = prediction_tasks[i:i + batch_size]
                                await asyncio.gather(*batch, return_exceptions=True)
                                if i + batch_size < len(prediction_tasks):
                                    await asyncio.sleep(0.2)

                            logging.info(f"[User {user_id}] 🔄 Sent {len(prediction_tasks)} predictions for period {next_period}")

                    user_config.last_processed_period = latest_period
                    
                # Periodic memory cleanup
                cleanup_counter += 1
                if cleanup_counter >= 20:
                    self.cleanup_memory()
                    cleanup_counter = 0
                    
            except Exception as e:
                logging.error(f"[User {user_id}] Loop error: {e}")
                await asyncio.sleep(1)
            
            await asyncio.sleep(0.5)
        
        logging.info(f"[User {user_id}] Prediction loop stopped")
        await self.send_log(context, f"⏹️ <b>Predictions Stopped</b>\nUser: {user_config.user_name} (ID: {user_id})")
    
    async def subscription_reminder_loop(self, context: ContextTypes.DEFAULT_TYPE):
        """Send reminders for expiring subscriptions"""
        logging.info("🔔 Subscription reminder task started")
        
        while True:
            try:
                await asyncio.sleep(86400)
                
                for user_id_str, sub_data in self.subscription_manager.subscriptions.items():
                    user_id = int(user_id_str)
                    
                    if sub_data.get('is_trial', False):
                        continue
                    
                    expiry = datetime.fromisoformat(sub_data['expiry'])
                    days_left = (expiry - datetime.now()).days
                    
                    if 1 <= days_left <= 5:
                        try:
                            user_config = self.users.get(user_id)
                            if user_config:
                                await self.send_message_with_retry(
                                    context, user_id,
                                    text=f"⚠️ <b>Subscription Expiry Reminder</b>\n\n"
                                         f"Your {sub_data.get('tier', 'basic').upper()} subscription will expire in <b>{days_left} days</b>!\n\n"
                                         f"Renew now to continue uninterrupted access to predictions.\n\n"
                                         f"Use /start to renew your subscription.",
                                    parse_mode=ParseMode.HTML
                                )
                                logging.info(f"📧 Reminder sent to user {user_id} ({days_left} days left)")
                        except Exception as e:
                            logging.error(f"❌ Failed to send reminder to {user_id}: {e}")
                
            except Exception as e:
                logging.error(f"❌ Reminder loop error: {e}")
                await asyncio.sleep(3600)
    
    def get_keyboard(self, keyboard_type, is_admin=False, user_config=None, user_tier=None):
        """Get inline keyboard markup"""
        # Get dynamic prices from settings
        basic_price = self.settings.get('basic_price', 299)
        premium_price = self.settings.get('premium_price', 599)
        vip_price = self.settings.get('vip_price', 999)

        if is_admin:
            keyboards = {
                'admin_main': [
                    [InlineKeyboardButton("👤 My Settings", callback_data="user_settings")],
                    [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")],
                    [InlineKeyboardButton("▶️ Start Predictions", callback_data="start_predictions"),
                     InlineKeyboardButton("⏹️ Stop Predictions", callback_data="stop_predictions")]
                ],
                'admin_panel': [
                    [InlineKeyboardButton("📊 All Users Stats", callback_data="admin_all_stats")],
                    [InlineKeyboardButton("🎮 Control All Users", callback_data="admin_control_all")],
                    [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
                    [InlineKeyboardButton("💳 Subscription Control", callback_data="admin_subscription")],
                    [InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_bot_settings")],
                    [InlineKeyboardButton("👥 User Management", callback_data="admin_user_mgmt")],
                    [InlineKeyboardButton("📢 Channel Broadcast", callback_data="admin_channel_broadcast")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
                ],
                'admin_control_all': [
                    [InlineKeyboardButton("▶️ Start All Users", callback_data="admin_start_all")],
                    [InlineKeyboardButton("⏹️ Stop All Users", callback_data="admin_stop_all")],
                    [InlineKeyboardButton("🔄 Restart All Users", callback_data="admin_restart_all")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
                ],
                'admin_subscription': [
                    [InlineKeyboardButton("➕ Add Subscription", callback_data="admin_add_sub")],
                    [InlineKeyboardButton("➕ Add Sub (Custom)", callback_data="admin_add_sub_custom")],
                    [InlineKeyboardButton("📋 List Subscriptions", callback_data="admin_list_subs")],
                    [InlineKeyboardButton("🚫 Remove Subscription", callback_data="admin_remove_sub")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
                ],
                'admin_bot_settings': [
                    [InlineKeyboardButton("📢 Set Mandatory Channel", callback_data="admin_set_channel")],
                    [InlineKeyboardButton("💰 Set Basic Price", callback_data="admin_set_basic_price")],
                    [InlineKeyboardButton("🚀 Set Premium Price", callback_data="admin_set_premium_price")],
                    [InlineKeyboardButton("👑 Set VIP Price", callback_data="admin_set_vip_price")],
                    [InlineKeyboardButton("💳 Set UPI ID", callback_data="admin_set_upi")],
                    [InlineKeyboardButton("🔗 Set Register Link", callback_data="admin_set_register_link")],
                    [InlineKeyboardButton("🔄 Toggle Subscription", callback_data="admin_toggle_sub")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
                ],
                'admin_user_mgmt': [
                    [InlineKeyboardButton("📋 List All Users", callback_data="admin_list_users")],
                    [InlineKeyboardButton("🔍 View User Details", callback_data="admin_view_user")],
                    [InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_admin")],
                    [InlineKeyboardButton("📋 List Admins", callback_data="admin_list_admins")],
                    [InlineKeyboardButton("🗑️ Clear User Data", callback_data="admin_clear_user_data")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
                ],
                'admin_channel_broadcast': [
                    [InlineKeyboardButton("🎯 Broadcast to Specific Channel", callback_data="admin_broadcast_specific_channel")],
                    [InlineKeyboardButton("📢 Broadcast to All Channels", callback_data="admin_broadcast_all_channels")],
                    [InlineKeyboardButton("👤 Broadcast to User's Channels", callback_data="admin_broadcast_user_channels")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
                ]
            }
        else:
            keyboards = {}
        
        # Common keyboards with DYNAMIC PRICES
        keyboards.update({
            'main': [
                [InlineKeyboardButton("⚙️ Settings", callback_data="user_settings")],
                [InlineKeyboardButton("▶️ Start Predictions", callback_data="start_predictions"),
                 InlineKeyboardButton("⏹️ Stop Predictions", callback_data="stop_predictions")],
                [InlineKeyboardButton("📊 My Stats", callback_data="user_stats")],
                [InlineKeyboardButton("💳 My Subscription", callback_data="user_subscription")],
                [InlineKeyboardButton("🔄 Renew Subscription", callback_data="renew_subscription")]
            ],
            'channel_join': [
                [InlineKeyboardButton("📢 Join Our Channel", url=f"https://t.me/{self.settings.get('mandatory_channel', 'YourChannel').replace('@', '')}")],
                [InlineKeyboardButton("✅ I Have Joined", callback_data="check_membership")]
            ],
            'subscription_choice': [
                [InlineKeyboardButton(f"💰 Basic - ₹{basic_price}/month", callback_data="buy_basic")],
                [InlineKeyboardButton(f"🚀 Premium - ₹{premium_price}/month", callback_data="buy_premium")],
                [InlineKeyboardButton(f"👑 VIP - ₹{vip_price}/month", callback_data="buy_vip")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ],
            'subscription_payment': [
                [InlineKeyboardButton("💳 Pay via UPI", callback_data="pay_upi")],
                [InlineKeyboardButton("📞 Contact Admin", url=f"tg://user?id={self.admin_ids[0]}")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ],
            'user_settings': [
                [InlineKeyboardButton("📢 Manage Channels", callback_data="manage_channels")],
                [InlineKeyboardButton("🎲 Prediction Settings", callback_data="prediction_settings")],
                [InlineKeyboardButton("🖼️ Media Settings", callback_data="media_settings")],
                [InlineKeyboardButton("📝 Template Settings", callback_data="template_settings")],
                [InlineKeyboardButton("🎨 Banner Settings", callback_data="banner_settings")],
                [InlineKeyboardButton("🔗 Register Link", callback_data="register_link_settings")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ],
            'manage_channels': [
                [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel")],
                [InlineKeyboardButton("➖ Remove Channel", callback_data="remove_channel")],
                [InlineKeyboardButton("📋 List Channels", callback_data="list_channels")],
                [InlineKeyboardButton("🔙 Back", callback_data="user_settings")]
            ],
            'media_settings': [
                [InlineKeyboardButton("🎉 Win Media", callback_data="set_win_media")],
                [InlineKeyboardButton("💫 Loss Media", callback_data="set_loss_media")],
                [InlineKeyboardButton("🎲 Big Media", callback_data="set_big_media")],
                [InlineKeyboardButton("🎲 Small Media", callback_data="set_small_media")],
                [InlineKeyboardButton("🎨 Red Media", callback_data="set_red_media")],
                [InlineKeyboardButton("🎨 Green Media", callback_data="set_green_media")],
                [InlineKeyboardButton("📋 View Media", callback_data="view_media")],
                [InlineKeyboardButton("🗑️ Delete Media", callback_data="delete_media")],  # NEW: Delete media option
                [InlineKeyboardButton("🔙 Back", callback_data="user_settings")]
            ],
            'delete_media_menu': [  # NEW: Delete media menu
                [InlineKeyboardButton("🗑️ Delete Win Media", callback_data="delete_win_media")],
                [InlineKeyboardButton("🗑️ Delete Loss Media", callback_data="delete_loss_media")],
                [InlineKeyboardButton("🗑️ Delete Big Media", callback_data="delete_big_media")],
                [InlineKeyboardButton("🗑️ Delete Small Media", callback_data="delete_small_media")],
                [InlineKeyboardButton("🗑️ Delete Red Media", callback_data="delete_red_media")],
                [InlineKeyboardButton("🗑️ Delete Green Media", callback_data="delete_green_media")],
                [InlineKeyboardButton("🔙 Back", callback_data="media_settings")]
            ],
            'banner_settings': [
                [InlineKeyboardButton("🔄 Change Banner", callback_data="change_banner")],
                [InlineKeyboardButton("🔙 Back", callback_data="user_settings")]
            ],
            'template_settings': [
                [InlineKeyboardButton("📝 Edit Prediction Template", callback_data="edit_prediction_template")],
                [InlineKeyboardButton("🎉 Edit Win Template", callback_data="edit_win_template")],
                [InlineKeyboardButton("💫 Edit Lose Template", callback_data="edit_lose_template")],
                [InlineKeyboardButton("📊 Toggle Table Format", callback_data="toggle_table_format")],
                [InlineKeyboardButton("🎯 Custom Session Settings", callback_data="custom_session_settings")],
                [InlineKeyboardButton("📝 Template Disable Options", callback_data="template_disable_settings")],
                [InlineKeyboardButton("🔙 Back", callback_data="user_settings")]
            ],
            'prediction_settings': [
                [InlineKeyboardButton("📊 Set Prediction Type", callback_data="set_prediction_type")],
                [InlineKeyboardButton("📋 View Channel Types", callback_data="view_channel_types")],
                [InlineKeyboardButton("💰 Set Base Price", callback_data="set_base_price")],
                [InlineKeyboardButton("⚙️ Session Mode", callback_data="session_mode_settings")],
                [InlineKeyboardButton("🔙 Back", callback_data="user_settings")]
            ],
            'session_mode_settings': [
                [InlineKeyboardButton("⏰ 24/7 Mode", callback_data="set_mode_247")],
                [InlineKeyboardButton("🎯 Custom Session", callback_data="set_mode_custom")],
                [InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]
            ],
            'prediction_type_selection': [
                [InlineKeyboardButton("🎲 Big/Small Prediction", callback_data="pred_type_big_small")],
                [InlineKeyboardButton("🎨 Color Prediction", callback_data="pred_type_color")],
                [InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]
            ],
            'register_link_settings': [
                [InlineKeyboardButton("🔗 Set Register Link", callback_data="set_register_link")],
                [InlineKeyboardButton("👁️ View Register Link", callback_data="view_register_link")],
                [InlineKeyboardButton("🔙 Back", callback_data="user_settings")]
            ],
            'custom_session_settings': [
                [InlineKeyboardButton("⚙️ Session Mode", callback_data="session_mode_settings")],
                [InlineKeyboardButton("⏱️ Session Duration", callback_data="session_duration_settings")],
                [InlineKeyboardButton("📝 Session Messages", callback_data="session_messages_settings")],
                [InlineKeyboardButton("🖼️ Session Media", callback_data="session_media_settings")],
                [InlineKeyboardButton("📢 Extra Messages", callback_data="extra_messages_settings")],
                [InlineKeyboardButton("▶️ Start Custom Session", callback_data="start_custom_session")],
                [InlineKeyboardButton("⏹️ Stop Custom Session", callback_data="stop_custom_session")],
                [InlineKeyboardButton("🔙 Back", callback_data="template_settings")]
            ],
            'session_messages_settings': [
                [InlineKeyboardButton("🎯 Edit Start Message", callback_data="edit_session_start_message")],
                [InlineKeyboardButton("⏰ Edit End Message", callback_data="edit_session_end_message")],
                [InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]
            ],
            'session_media_settings': [
                [InlineKeyboardButton("🎯 Start Media", callback_data="set_session_start_media")],
                [InlineKeyboardButton("⏰ End Media", callback_data="set_session_end_media")],
                [InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]
            ],
            'extra_messages_settings': [
                [InlineKeyboardButton("➕ Add Extra Message", callback_data="add_extra_message")],
                [InlineKeyboardButton("📋 List Extra Messages", callback_data="list_extra_messages")],
                [InlineKeyboardButton("🗑️ Delete Extra Message", callback_data="delete_extra_message")],
                [InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]
            ],
            'template_disable_settings': [
                [InlineKeyboardButton("🎉 Toggle Win Template", callback_data="toggle_win_template")],
                [InlineKeyboardButton("💫 Toggle Lose Template", callback_data="toggle_lose_template")],
                [InlineKeyboardButton("🔙 Back", callback_data="template_settings")]
            ]
        })
        
        return InlineKeyboardMarkup(keyboards.get(keyboard_type, keyboards['main']))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        is_admin = user_id in self.admin_ids

        # Start reminder task once
        if not self.reminder_task_started:
            self.reminder_task_started = True
            asyncio.create_task(self.subscription_reminder_loop(context))
            logging.info("✅ Reminder task scheduled")

        # Get or create user
        user_config = self.get_or_create_user(user_id, user_name)

        # Check channel membership
        if not is_admin and self.settings.get('mandatory_channel'):
            is_member = await self.check_channel_membership(context, user_id, self.settings['mandatory_channel'])
            if not is_member:
                await update.message.reply_text(
                    f"👋 <b>Welcome {user_name}!</b>\n\n"
                    f"📢 <b>Channel Membership Required</b>\n\n"
                    f"To access our premium AI prediction system, please join our official channel:\n"
                    f"<code>{self.settings['mandatory_channel']}</code>\n\n"
                    f"Click the button below to join, then verify your membership.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=self.get_keyboard('channel_join', is_admin, user_config)
                )
                return

        # Check subscription
        if not is_admin and self.settings.get('subscription_enabled'):
            if not self.subscription_manager.is_subscribed(user_id):
                # Get DYNAMIC prices from settings
                basic_price = self.settings.get('basic_price', 299)
                premium_price = self.settings.get('premium_price', 599)
                vip_price = self.settings.get('vip_price', 999)
                trial_days = self.settings.get('trial_days', 1)

                user_id_str = str(user_id)
                had_trial = user_id_str in self.subscription_manager.subscriptions

                if had_trial:
                    await update.message.reply_text(
                        f"👋 <b>Welcome Back {user_name}!</b>\n\n"
                        f"💳 <b>Premium Subscription Required</b>\n\n"
                        f"Continue accessing our advanced AI prediction system:\n\n"
                        f"💰 <b>Basic:</b> ₹{basic_price}/month\n"
                        f"• Big/Small Predictions\n"
                        f"• 1 Channel\n"
                        f"• Standard Templates\n\n"
                        f"🚀 <b>Premium:</b> ₹{premium_price}/month\n"
                        f"• All Predictions (Big/Small + Colors)\n"
                        f"• Multiple Channels\n"
                        f"• Custom Templates\n"
                        f"• Multiple Media\n"
                        f"• Language Support\n\n"
                        f"👑 <b>VIP:</b> ₹{vip_price}/month\n"
                        f"• All Premium Features\n"
                        f"• Priority Support\n"
                        f"• Advanced Analytics\n"
                        f"• Custom Branding\n\n"
                        f"Select your preferred subscription plan:",
                        parse_mode=ParseMode.HTML,
                        reply_markup=self.get_keyboard('subscription_choice', is_admin, user_config)
                    )
                else:
                    await update.message.reply_text(
                        f"👋 <b>Welcome {user_name}!</b>\n\n"
                        f"💳 <b>Subscription Options</b>\n\n"
                        f"🎁 <b>Free Trial:</b> {trial_days} day (First time users only)\n\n"
                        f"💰 <b>Basic:</b> ₹{basic_price}/month\n"
                        f"• Big/Small Predictions\n"
                        f"• 1 Channel\n"
                        f"• Standard Templates\n\n"
                        f"🚀 <b>Premium:</b> ₹{premium_price}/month\n"
                        f"• All Predictions (Big/Small + Colors)\n"
                        f"• Multiple Channels\n"
                        f"• Custom Templates\n"
                        f"• Multiple Media\n"
                        f"• Language Support\n\n"
                        f"👑 <b>VIP:</b> ₹{vip_price}/month\n"
                        f"• All Premium Features\n"
                        f"• Priority Support\n"
                        f"• Advanced Analytics\n"
                        f"• Custom Branding\n\n"
                        f"Choose your preferred option below:",
                        parse_mode=ParseMode.HTML,
                        reply_markup=self.get_keyboard('subscription_choice', is_admin, user_config)
                    )
                return

        # Regular start
        welcome_text = f"🎯 <b>AI PREDICTION SYSTEM</b>\n\n"
        welcome_text += f"👋 <b>Welcome {user_name}!</b>\n\n"
        
        if is_admin:
            welcome_text += "👑 <b>Administrator Access Granted</b>\n\n"

        if self.subscription_manager.is_subscribed(user_id):
            tier = self.subscription_manager.get_tier(user_id)
            days_left = self.subscription_manager.days_remaining(user_id)
            is_trial = self.subscription_manager.is_trial(user_id)
            
            if is_trial:
                sub_type = "🎁 Trial"
            else:
                sub_type = f"💰 {tier.upper()}"
            
            welcome_text += f"✅ <b>{sub_type} Subscription Active</b> ({days_left} days remaining)\n\n"

        welcome_text += "Please select an option from the menu below:"

        keyboard_type = 'admin_main' if is_admin else 'main'
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_keyboard(keyboard_type, is_admin, user_config)
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_name = query.from_user.first_name
        chat_id = query.message.chat_id
        data = query.data
        is_admin = user_id in self.admin_ids
        
        user_config = self.get_or_create_user(user_id, user_name)
        user_tier = self.subscription_manager.get_tier(user_id)
        
        # Handle membership check
        if data == 'check_membership':
            is_member = await self.check_channel_membership(context, user_id, self.settings['mandatory_channel'])
            if is_member:
                if self.settings.get('subscription_enabled') and not self.subscription_manager.is_subscribed(user_id):
                    # Get DYNAMIC prices
                    basic_price = self.settings.get('basic_price', 299)
                    premium_price = self.settings.get('premium_price', 599)
                    vip_price = self.settings.get('vip_price', 999)
                    trial_days = self.settings.get('trial_days', 1)
                    
                    user_id_str = str(user_id)
                    had_trial = user_id_str in self.subscription_manager.subscriptions
                    
                    if had_trial:
                        await query.edit_message_text(
                            f"✅ <b>Channel Verification Successful!</b>\n\n"
                            f"💳 <b>Activate Premium Subscription</b>\n\n"
                            f"💰 <b>Basic:</b> ₹{basic_price}/month\n"
                            f"🚀 <b>Premium:</b> ₹{premium_price}/month\n"
                            f"👑 <b>VIP:</b> ₹{vip_price}/month\n\n"
                            f"Choose your preferred plan:",
                            parse_mode=ParseMode.HTML,
                            reply_markup=self.get_keyboard('subscription_choice', is_admin, user_config)
                        )
                    else:
                        await query.edit_message_text(
                            f"✅ <b>Channel Verification Successful!</b>\n\n"
                            f"💳 <b>Choose Your Plan</b>\n\n"
                            f"🎁 <b>Free Trial:</b> {trial_days} day\n"
                            f"💰 <b>Basic Subscription:</b> ₹{basic_price}/month\n"
                            f"🚀 <b>Premium Subscription:</b> ₹{premium_price}/month\n"
                            f"👑 <b>VIP Subscription:</b> ₹{vip_price}/month\n\n"
                            f"Select your preferred option:",
                            parse_mode=ParseMode.HTML,
                            reply_markup=self.get_keyboard('subscription_choice', is_admin, user_config)
                        )
                else:
                    keyboard_type = 'admin_main' if is_admin else 'main'
                    await query.edit_message_text(
                        "✅ <b>Verification Successful!</b> Welcome to our AI prediction system!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=self.get_keyboard(keyboard_type, is_admin, user_config)
                    )
            else:
                await query.answer("❌ Please join our channel first to use the bot!", show_alert=True)
        
        # Handle trial subscription
        elif data == 'start_trial':
            trial_days = self.settings.get('trial_days', 1)
            expiry = self.subscription_manager.add_trial(user_id, trial_days)
            
            if expiry:
                await query.edit_message_text(
                    f"🎉 <b>Free Trial Activated Successfully!</b>\n\n"
                    f"Your {trial_days}-day free trial has been activated.\n\n"
                    f"📅 <b>Expires on:</b> {expiry.strftime('%d %B %Y')}\n"
                    f"🎯 <b>Features:</b> Basic Predictions, 1 Channel\n\n"
                    f"Enjoy premium features! 🚀",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Start Using Bot", callback_data="main_menu")]])
                )
                await self.send_log(context, f"🎁 <b>Free Trial Activated</b>\nUser: {user_name} (ID: {user_id})")
            else:
                await query.edit_message_text(
                    "❌ You have already used your free trial! Please purchase a premium subscription.",
                    reply_markup=self.get_keyboard('subscription_choice', is_admin, user_config)
                )
        
        # Handle subscription purchases
        elif data in ['buy_basic', 'buy_premium', 'buy_vip']:
            # Get DYNAMIC prices
            basic_price = self.settings.get('basic_price', 299)
            premium_price = self.settings.get('premium_price', 599)
            vip_price = self.settings.get('vip_price', 999)
            
            tiers = {
                'buy_basic': {'name': 'Basic', 'price': basic_price, 'tier': 'basic'},
                'buy_premium': {'name': 'Premium', 'price': premium_price, 'tier': 'premium'},
                'buy_vip': {'name': 'VIP', 'price': vip_price, 'tier': 'vip'}
            }
            
            tier_info = tiers[data]
            
            await query.edit_message_text(
                f"💳 <b>{tier_info['name']} Subscription</b>\n\n"
                f"💰 <b>Price:</b> ₹{tier_info['price']}/month\n"
                f"⏱ <b>Duration:</b> 30 days\n"
                f"🎯 <b>Features:</b> {self.get_tier_features(tier_info['name'])}\n\n"
                f"Choose your payment method:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💳 Pay via UPI", callback_data=f"pay_upi_{tier_info['tier']}"),
                    InlineKeyboardButton("📞 Contact Admin", url=f"tg://user?id={self.admin_ids[0]}")
                ], [
                    InlineKeyboardButton("🔙 Back", callback_data="subscription_choice")
                ]])
            )
        
        # Handle UPI payments
        elif data.startswith('pay_upi_'):
            tier = data.replace('pay_upi_', '')
            price = self.settings.get(f'{tier}_price', 299)
            qr_path = self.generate_upi_qr(price)
            
            upi_text = f"""
💳 <b>{tier.upper()} Subscription - UPI Payment</b>

💰 <b>Amount:</b> ₹{price}
📱 <b>UPI ID:</b> <code>{self.settings.get('payment_upi')}</code>

📋 <b>Payment Steps:</b>
1. Scan the QR code below
2. The amount will be auto-filled
3. Complete the payment securely
4. Send payment screenshot to admin

👨‍💼 <b>Admin Contact: @aviii566</b> 
"""
            
            contact_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Contact Admin", url=f"tg://user?id={self.admin_ids[0]}")],
                [InlineKeyboardButton("🔙 Back", callback_data="subscription_choice")]
            ])
            
            with open(qr_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=upi_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=contact_keyboard
                )
            
            try:
                os.remove(qr_path)
            except:
                pass
        
        # Handle user subscription info
        elif data == 'user_subscription':
            if self.subscription_manager.is_subscribed(user_id):
                expiry = self.subscription_manager.get_expiry(user_id)
                days_left = self.subscription_manager.days_remaining(user_id)
                is_trial = self.subscription_manager.is_trial(user_id)
                tier = self.subscription_manager.get_tier(user_id)
                
                sub_type = f"💰 {tier.upper()}"
                expiry_text = expiry.strftime('%d %B %Y')
                days_text = f"{days_left} days remaining"
                
                sub_text = f"""
💳 <b>Your Subscription Details</b>

✅ <b>Status:</b> Active
🎯 <b>Type:</b> {sub_type}
📅 <b>Expires on:</b> {expiry_text}
⏱ <b>Days Remaining:</b> {days_text}

📢 You will receive automatic reminders 5 days before expiry.
"""
            else:
                sub_text = """
💳 <b>Your Subscription Status</b>

❌ <b>Status:</b> Expired / Not Active

💡 Use /start to activate your subscription and access premium features.
"""
            
            await query.edit_message_text(
                sub_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Renew", callback_data="renew_subscription"), InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
            )
        
        # Handle main menu navigation
        elif data == 'main_menu' or data == 'admin_main':
            keyboard_type = 'admin_main' if is_admin else 'main'
            await query.edit_message_text(
                "👋 <b>Main Menu - AI Prediction System</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard(keyboard_type, is_admin, user_config)
            )
        
        # Handle prediction start
        elif data == 'start_predictions':
            if not is_admin and self.settings.get('subscription_enabled'):
                if not self.subscription_manager.is_subscribed(user_id):
                    await query.edit_message_text("❌ <b>Subscription Expired</b>\n\nPlease renew to start predictions.", parse_mode=ParseMode.HTML)
                    return
            
            if user_config.is_active:
                await query.edit_message_text("⚠️ <b>Predictions Already Running</b>", parse_mode=ParseMode.HTML)
                return
            
            if not user_config.channels:
                await query.edit_message_text("❌ <b>No Channels Configured</b>\n\nPlease add at least one channel first in Settings!", parse_mode=ParseMode.HTML)
                return
            
            user_config.reset_state()
            user_config.is_active = True
            self.save_user_config(user_id)
            
            asyncio.create_task(self.user_prediction_loop(context, user_id))
            
            await query.edit_message_text(
                "🎉 <b>AI Predictions Started Successfully!</b>\n\n"
                f"• 🎯 <b>Multiplier:</b> 1x\n"
                f"• 💰 <b>Base Price:</b> ₹{user_config.base_price}\n"
                f"• 📢 <b>Channels:</b> {len(user_config.channels)}\n"
                f"• 🎲 <b>Prediction Types:</b> {', '.join(set(user_config.prediction_type.values()) or ['Big/Small'])}\n"
                f"• 🔗 <b>Register Link:</b> {user_config.register_link}\n\n"
                f"<i>AI system is now analyzing patterns and sending predictions...</i>",
                parse_mode=ParseMode.HTML
            )
            
            await self.send_log(context, f"▶️ <b>Predictions Started</b>\nUser: {user_name} (ID: {user_id})\nChannels: {len(user_config.channels)}")
        
        # Handle prediction stop
        elif data == 'stop_predictions':
            if not user_config.is_active:
                await query.edit_message_text("⚠️ <b>Predictions Not Currently Running</b>", parse_mode=ParseMode.HTML)
                return
            
            user_config.is_active = False
            self.save_user_config(user_id)
            await query.edit_message_text("⏹️ <b>Predictions Stopped Successfully!</b>", parse_mode=ParseMode.HTML)
            await self.send_log(context, f"⏹️ <b>Predictions Stopped</b>\nUser: {user_name} (ID: {user_id})")
        
        # Handle user stats
        elif data == 'user_stats':
            status = "🟢 Active" if user_config.is_active else "🔴 Inactive"
            banner_status = "✅ Custom" if os.path.exists(user_config.banner_image) else "📁 Default"
            
            if self.subscription_manager.is_subscribed(user_id):
                is_trial = self.subscription_manager.is_trial(user_id)
                tier = self.subscription_manager.get_tier(user_id)
                if is_trial:
                    sub_status = "🎁 Trial"
                else:
                    sub_status = f"✅ {tier.upper()}"
            else:
                sub_status = "❌ Expired"
            
            # Calculate total predictions across all channels
            total_predictions = sum(len(table) for table in user_config.prediction_tables.values())
            total_table_size = user_config.max_table_rows * len(user_config.channels) if user_config.channels else user_config.max_table_rows
            
            # Media counts
            media_counts = f"""
🖼️ <b>Media Counts:</b>
• 🎉 Win: {len(user_config.win_media_ids)}
• 💫 Loss: {len(user_config.lose_media_ids)}
• 🎲 Big: {len(user_config.big_media_ids)}
• 🎲 Small: {len(user_config.small_media_ids)}
• 🎨 Red: {len(user_config.red_media_ids)}
• 🎨 Green: {len(user_config.green_media_ids)}
"""
            
            stats_text = f"""
📊 <b>Your Statistics</b>

🎯 <b>Status:</b> {status}
💳 <b>Subscription:</b> {sub_status}
📢 <b>Channels:</b> {len(user_config.channels)}
💰 <b>Base Price:</b> ₹{user_config.base_price}
🚀 <b>Current Multiplier:</b> {user_config.current_multiplier}x
🎨 <b>Banner:</b> {banner_status}
🌐 <b>Language:</b> {user_config.language.upper()}
🔗 <b>Register Link:</b> {user_config.register_link[:30]}...
📈 <b>Total Predictions:</b> {user_config.table_counter}
✅ <b>Consecutive Wins:</b> {user_config.consecutive_wins}
❌ <b>Consecutive Losses:</b> {user_config.consecutive_losses}
📋 <b>Current Table Size:</b> {total_predictions}/{total_table_size}

{media_counts}
"""
            await query.edit_message_text(
                stats_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
            )
        
        # Handle settings menu
        elif data == 'user_settings':
            await query.edit_message_text(
                "⚙️ <b>Configuration Settings</b>\n\nCustomize your prediction system:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('user_settings', is_admin, user_config)
            )
        
        # Handle channel management
        elif data == 'manage_channels':
            channels_list = '\n'.join([f"• {ch}" for ch in user_config.channels]) if user_config.channels else "No channels added yet"
            await query.edit_message_text(
                f"📢 <b>Your Channels</b>\n\n{channels_list}\n\nManage your channels:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('manage_channels', is_admin, user_config)
            )
        
        # Handle add channel
        elif data == 'add_channel':
            self.user_state[chat_id] = 'awaiting_add_channel'
            await query.edit_message_text(
                "➕ <b>Add Channel</b>\n\nSend channel username or ID:\n\n• Example: @mychannel\n• Example: -1001234567890\n\nPlease ensure the bot is admin in your channel.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="manage_channels")]])
            )
        
        # Handle remove channel
        elif data == 'remove_channel':
            if not user_config.channels:
                await query.edit_message_text("❌ <b>No Channels to Remove</b>", parse_mode=ParseMode.HTML)
                return
            
            self.user_state[chat_id] = 'awaiting_remove_channel'
            channels_list = '\n'.join([f"{i+1}. {ch}" for i, ch in enumerate(user_config.channels)])
            await query.edit_message_text(
                f"➖ <b>Remove Channel</b>\n\nSend the number of channel to remove:\n\n{channels_list}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="manage_channels")]])
            )
        
        # Handle list channels
        elif data == 'list_channels':
            channels_list = '\n'.join([f"• {ch}" for ch in user_config.channels]) if user_config.channels else "No channels added yet"
            await query.edit_message_text(
                f"📋 <b>Your Active Channels</b>\n\n{channels_list}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="manage_channels")]])
            )
        
        # Handle media settings
        elif data == 'media_settings':
            await query.edit_message_text(
                "🖼️ <b>Media Settings</b>\n\nSet multiple media for different events:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('media_settings', is_admin, user_config)
            )
        
        # Handle win media setup
        elif data == 'set_win_media':
            self.user_state[chat_id] = 'awaiting_win_media'
            await query.edit_message_text(
                "🎉 <b>Set Win Animation</b>\n\nSend GIFs or Stickers for WIN results:\n\nSend multiple media files one by one. Click Done when finished.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="media_settings")]])
            )
        
        # Handle loss media setup
        elif data == 'set_loss_media':
            self.user_state[chat_id] = 'awaiting_loss_media'
            await query.edit_message_text(
                "💫 <b>Set Loss Animation</b>\n\nSend GIFs or Stickers for LOSS results:\n\nSend multiple media files one by one. Click Done when finished.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="media_settings")]])
            )
        
        # Handle big media setup
        elif data == 'set_big_media':
            self.user_state[chat_id] = 'awaiting_big_media'
            await query.edit_message_text(
                "🎲 <b>Set Big Prediction Media</b>\n\nSend GIFs or Stickers for BIG predictions:\n\nSend multiple media files one by one. Click Done when finished.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="media_settings")]])
            )
        
        # Handle small media setup
        elif data == 'set_small_media':
            self.user_state[chat_id] = 'awaiting_small_media'
            await query.edit_message_text(
                "🎲 <b>Set Small Prediction Media</b>\n\nSend GIFs or Stickers for SMALL predictions:\n\nSend multiple media files one by one. Click Done when finished.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="media_settings")]])
            )
        
        # Handle red media setup
        elif data == 'set_red_media':
            self.user_state[chat_id] = 'awaiting_red_media'
            await query.edit_message_text(
                "🎨 <b>Set Red Prediction Media</b>\n\nSend GIFs or Stickers for RED predictions:\n\nSend multiple media files one by one. Click Done when finished.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="media_settings")]])
            )
        
        # Handle green media setup
        elif data == 'set_green_media':
            self.user_state[chat_id] = 'awaiting_green_media'
            await query.edit_message_text(
                "🎨 <b>Set Green Prediction Media</b>\n\nSend GIFs or Stickers for GREEN predictions:\n\nSend multiple media files one by one. Click Done when finished.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="media_settings")]])
            )
        
        # NEW: Handle delete media menu
        elif data == 'delete_media':
            await query.edit_message_text(
                "🗑️ <b>Delete Media</b>\n\nSelect which media type you want to delete:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('delete_media_menu', is_admin, user_config)
            )
        
        # Handle delete win media
        elif data == 'delete_win_media':
            if user_config.win_media_ids:
                self.user_state[chat_id] = 'awaiting_delete_win_media'
                media_list = '\n'.join([f"{i+1}. Media ID: {media_id[:20]}..." for i, media_id in enumerate(user_config.win_media_ids)])
                await query.edit_message_text(
                    f"🗑️ <b>Delete Win Media</b>\n\nCurrent win media:\n{media_list}\n\nSend the number of media to delete:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="delete_media")]])
                )
            else:
                await query.edit_message_text("❌ <b>No win media to delete!</b>", parse_mode=ParseMode.HTML)
        
        # Handle delete loss media
        elif data == 'delete_loss_media':
            if user_config.lose_media_ids:
                self.user_state[chat_id] = 'awaiting_delete_loss_media'
                media_list = '\n'.join([f"{i+1}. Media ID: {media_id[:20]}..." for i, media_id in enumerate(user_config.lose_media_ids)])
                await query.edit_message_text(
                    f"🗑️ <b>Delete Loss Media</b>\n\nCurrent loss media:\n{media_list}\n\nSend the number of media to delete:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="delete_media")]])
                )
            else:
                await query.edit_message_text("❌ <b>No loss media to delete!</b>", parse_mode=ParseMode.HTML)
        
        # Handle delete big media
        elif data == 'delete_big_media':
            if user_config.big_media_ids:
                self.user_state[chat_id] = 'awaiting_delete_big_media'
                media_list = '\n'.join([f"{i+1}. Media ID: {media_id[:20]}..." for i, media_id in enumerate(user_config.big_media_ids)])
                await query.edit_message_text(
                    f"🗑️ <b>Delete Big Media</b>\n\nCurrent big media:\n{media_list}\n\nSend the number of media to delete:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="delete_media")]])
                )
            else:
                await query.edit_message_text("❌ <b>No big media to delete!</b>", parse_mode=ParseMode.HTML)
        
        # Handle delete small media
        elif data == 'delete_small_media':
            if user_config.small_media_ids:
                self.user_state[chat_id] = 'awaiting_delete_small_media'
                media_list = '\n'.join([f"{i+1}. Media ID: {media_id[:20]}..." for i, media_id in enumerate(user_config.small_media_ids)])
                await query.edit_message_text(
                    f"🗑️ <b>Delete Small Media</b>\n\nCurrent small media:\n{media_list}\n\nSend the number of media to delete:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="delete_media")]])
                )
            else:
                await query.edit_message_text("❌ <b>No small media to delete!</b>", parse_mode=ParseMode.HTML)
        
        # Handle delete red media
        elif data == 'delete_red_media':
            if user_config.red_media_ids:
                self.user_state[chat_id] = 'awaiting_delete_red_media'
                media_list = '\n'.join([f"{i+1}. Media ID: {media_id[:20]}..." for i, media_id in enumerate(user_config.red_media_ids)])
                await query.edit_message_text(
                    f"🗑️ <b>Delete Red Media</b>\n\nCurrent red media:\n{media_list}\n\nSend the number of media to delete:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="delete_media")]])
                )
            else:
                await query.edit_message_text("❌ <b>No red media to delete!</b>", parse_mode=ParseMode.HTML)
        
        # Handle delete green media
        elif data == 'delete_green_media':
            if user_config.green_media_ids:
                self.user_state[chat_id] = 'awaiting_delete_green_media'
                media_list = '\n'.join([f"{i+1}. Media ID: {media_id[:20]}..." for i, media_id in enumerate(user_config.green_media_ids)])
                await query.edit_message_text(
                    f"🗑️ <b>Delete Green Media</b>\n\nCurrent green media:\n{media_list}\n\nSend the number of media to delete:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="delete_media")]])
                )
            else:
                await query.edit_message_text("❌ <b>No green media to delete!</b>", parse_mode=ParseMode.HTML)
        
        # Handle view media
        elif data == 'view_media':
            media_info = f"""
🖼️ <b>Your Media Files</b>

🎉 <b>Win Media:</b> {len(user_config.win_media_ids)} files
💫 <b>Loss Media:</b> {len(user_config.lose_media_ids)} files
🎲 <b>Big Media:</b> {len(user_config.big_media_ids)} files
🎲 <b>Small Media:</b> {len(user_config.small_media_ids)} files
🎨 <b>Red Media:</b> {len(user_config.red_media_ids)} files
🎨 <b>Green Media:</b> {len(user_config.green_media_ids)} files

💡 Media will be sent based on prediction type and result.
"""
            await query.edit_message_text(
                media_info,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="media_settings")]])
            )
        
        # Handle language settings
        elif data == 'language_settings':
            keyboard = []
            for lang_code in LANGUAGES.keys():
                lang_name = LANGUAGES[lang_code].get('language_name', lang_code.upper())
                keyboard.append([InlineKeyboardButton(
                    f"{'✅ ' if user_config.language == lang_code else ''}{lang_name}",
                    callback_data=f"set_language_{lang_code}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="user_settings")])
            
            await query.edit_message_text(
                "🌐 <b>Language Settings</b>\n\nSelect your preferred language for PREDICTION MESSAGES ONLY:\n\n<i>Note: Bot interface will remain in English</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Handle language change
        elif data.startswith('set_language_'):
            lang_code = data.replace('set_language_', '')
            user_config.language = lang_code
            
            # Update templates to selected language
            lang_data = LANGUAGES.get(lang_code, LANGUAGES['en'])
            user_config.prediction_template = lang_data['templates']['prediction']
            user_config.win_template = lang_data['templates']['win']
            user_config.lose_template = lang_data['templates']['lose']
            
            self.save_user_config(user_id)
            
            lang_name = LANGUAGES[lang_code].get('language_name', lang_code.upper())
            await query.edit_message_text(
                f"✅ <b>Prediction language changed to {lang_name}</b>\n\nAll prediction messages and table headers will now be in {lang_name}.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="language_settings")]])
            )
        
        # Handle template settings
        elif data == 'template_settings':
            await query.edit_message_text(
                "📝 <b>Template Settings</b>\n\nCustomize your prediction messages:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('template_settings', is_admin, user_config)
            )
        
        # Handle prediction template editing
        elif data == 'edit_prediction_template':
            self.user_state[chat_id] = 'awaiting_prediction_template'
            await query.edit_message_text(
                f"📝 <b>Edit Prediction Template</b>\n\nCurrent template:\n\n{user_config.prediction_template}\n\nSend new prediction template:\n\nAvailable variables: {{period}}, {{choice}}, {{multiplier}}, {{price}}, {{register_link}}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="template_settings")]])
            )
        
        # Handle win template editing
        elif data == 'edit_win_template':
            self.user_state[chat_id] = 'awaiting_win_template'
            await query.edit_message_text(
                f"🎉 <b>Edit Win Template</b>\n\nCurrent template:\n\n{user_config.win_template}\n\nSend new win template:\n\nAvailable variables: {{period}}, {{result}}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="template_settings")]])
            )
        
        # Handle lose template editing
        elif data == 'edit_lose_template':
            self.user_state[chat_id] = 'awaiting_lose_template'
            await query.edit_message_text(
                f"💫 <b>Edit Lose Template</b>\n\nCurrent template:\n\n{user_config.lose_template}\n\nSend new lose template:\n\nAvailable variables: {{period}}, {{result}}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="template_settings")]])
            )
        
        # Handle table format toggle
        elif data == 'toggle_table_format':
            user_config.use_table_format = not user_config.use_table_format
            self.save_user_config(user_id)
            status = "Enabled" if user_config.use_table_format else "Disabled"
            await query.edit_message_text(
                f"✅ <b>Table format:</b> <b>{status}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="template_settings")]])
            )

        # Handle custom session settings
        elif data == 'custom_session_settings':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access custom sessions.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="template_settings")]])
                )
                return

            await query.edit_message_text(
                "🎯 <b>Custom Session Settings</b>\n\nConfigure your custom session features:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('custom_session_settings', is_admin, user_config)
            )

        # Handle session mode settings
        elif data == 'session_mode_settings':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session modes.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]])
                )
                return

            status = "Custom Session" if user_config.custom_session_enabled else "24/7 Mode"
            await query.edit_message_text(
                f"⚙️ <b>Session Mode</b>\n\nCurrent: <b>{status}</b>\n\nChoose session mode:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('session_mode_settings', is_admin, user_config)
            )

        # Handle session mode change
        elif data in ['set_mode_247', 'set_mode_custom']:
            # Check if user has access to custom session
            if data == 'set_mode_custom' and not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access custom sessions.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]])
                )
                return

            user_config.custom_session_enabled = (data == 'set_mode_custom')
            self.save_user_config(user_id)
            mode = "Custom Session" if user_config.custom_session_enabled else "24/7 Mode"
            await query.edit_message_text(
                f"✅ <b>Session mode set to {mode}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]])
            )

        # Handle session duration settings
        elif data == 'session_duration_settings':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            self.user_state[chat_id] = 'awaiting_session_duration'
            await query.edit_message_text(
                f"⏱️ <b>Set Session Duration</b>\n\nCurrent: {user_config.custom_session_duration} minutes\n\nSend new duration in minutes (1-1440):",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
            )

        # Handle session messages settings
        elif data == 'session_messages_settings':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            await query.edit_message_text(
                "📝 <b>Session Messages</b>\n\nCustomize session start and end messages:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('session_messages_settings', is_admin, user_config)
            )

        # Handle edit session start message
        elif data == 'edit_session_start_message':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="session_messages_settings")]])
                )
                return

            self.user_state[chat_id] = 'awaiting_session_start_message'
            await query.edit_message_text(
                f"🎯 <b>Edit Session Start Message</b>\n\nCurrent message:\n\n{user_config.custom_session_start_message}\n\nSend new start message:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="session_messages_settings")]])
            )

        # Handle edit session end message
        elif data == 'edit_session_end_message':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="session_messages_settings")]])
                )
                return

            self.user_state[chat_id] = 'awaiting_session_end_message'
            await query.edit_message_text(
                f"⏰ <b>Edit Session End Message</b>\n\nCurrent message:\n\n{user_config.custom_session_end_message}\n\nSend new end message:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="session_messages_settings")]])
            )

        # Handle session media settings
        elif data == 'session_media_settings':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            await query.edit_message_text(
                "🖼️ <b>Session Media</b>\n\nSet media for session start and end:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('session_media_settings', is_admin, user_config)
            )

        # Handle set session start media
        elif data == 'set_session_start_media':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="session_media_settings")]])
                )
                return

            self.user_state[chat_id] = 'awaiting_session_start_media'
            await query.edit_message_text(
                "🎯 <b>Set Session Start Media</b>\n\nSend GIFs, stickers, photos, or videos for session start:\n\nSend multiple media files one by one. Click Done when finished.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="session_media_settings")]])
            )

        # Handle set session end media
        elif data == 'set_session_end_media':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="session_media_settings")]])
                )
                return

            self.user_state[chat_id] = 'awaiting_session_end_media'
            await query.edit_message_text(
                "⏰ <b>Set Session End Media</b>\n\nSend GIFs, stickers, photos, or videos for session end:\n\nSend multiple media files one by one. Click Done when finished.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="session_media_settings")]])
            )

        # Handle extra messages settings
        elif data == 'extra_messages_settings':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            extra_count = len(user_config.extra_messages)
            await query.edit_message_text(
                f"📢 <b>Extra Messages</b>\n\nCurrent extra messages: {extra_count}\n\nManage additional messages during sessions:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('extra_messages_settings', is_admin, user_config)
            )

        # Handle add extra message
        elif data == 'add_extra_message':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="extra_messages_settings")]])
                )
                return

            self.user_state[chat_id] = 'awaiting_add_extra_message'
            await query.edit_message_text(
                "➕ <b>Add Extra Message</b>\n\nSend message in format:\n<code>timing:message</code> or <code>timing:message:media_url</code>\n\n• <b>timing:</b> start or end\n• <b>message:</b> your message text\n• <b>media_url:</b> optional media URL\n\nExample: <code>start:Welcome to session! or end:Session ended:photo123</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="extra_messages_settings")]])
            )

        # Handle list extra messages
        elif data == 'list_extra_messages':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="extra_messages_settings")]])
                )
                return

            if user_config.extra_messages:
                messages_list = "📋 <b>Extra Messages</b>\n\n"
                for i, msg in enumerate(user_config.extra_messages, 1):
                    timing = msg['timing'].upper()
                    message = msg['message'][:50] + "..." if len(msg['message']) > 50 else msg['message']
                    media = f" + Media" if msg['media'] else ""
                    messages_list += f"{i}. <b>{timing}:</b> {message}{media}\n"
                messages_list += f"\n<b>Total:</b> {len(user_config.extra_messages)} messages"
            else:
                messages_list = "📋 <b>Extra Messages</b>\n\nNo extra messages configured yet."

            await query.edit_message_text(
                messages_list,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="extra_messages_settings")]])
            )

        # Handle delete extra message
        elif data == 'delete_extra_message':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="extra_messages_settings")]])
                )
                return

            if user_config.extra_messages:
                self.user_state[chat_id] = 'awaiting_delete_extra_message'
                messages_list = "🗑️ <b>Delete Extra Message</b>\n\nSelect message to delete:\n\n"
                for i, msg in enumerate(user_config.extra_messages, 1):
                    timing = msg['timing'].upper()
                    message = msg['message'][:30] + "..." if len(msg['message']) > 30 else msg['message']
                    messages_list += f"{i}. <b>{timing}:</b> {message}\n"

                await query.edit_message_text(
                    messages_list + "\n\nSend the message number to delete:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="extra_messages_settings")]])
                )
            else:
                await query.edit_message_text(
                    "❌ <b>No extra messages to delete!</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="extra_messages_settings")]])
                )

        # Handle start custom session
        elif data == 'start_custom_session':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access custom sessions.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            if not user_config.custom_session_enabled:
                await query.edit_message_text(
                    "❌ <b>Custom session mode is not enabled!</b>\n\nEnable custom session mode first.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            if user_config.custom_session_active:
                await query.edit_message_text(
                    "⚠️ <b>Custom session is already active!</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            if not user_config.channels:
                await query.edit_message_text(
                    "❌ <b>No channels configured!</b>\n\nAdd channels first.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            # Start custom session
            user_config.custom_session_active = True
            user_config.custom_session_start_time = datetime.now()
            user_config.custom_session_channel = user_config.channels[0]  # Use first channel
            self.save_user_config(user_id)

            # Send session start message and media
            if user_config.custom_session_start_media:
                await self.send_media_sequence(context, user_config.custom_session_channel, user_config.custom_session_start_media)

            start_message = self.format_message(user_config.custom_session_start_message, {
                'duration': user_config.custom_session_duration,
                'channel': user_config.custom_session_channel
            })
            await self.send_message_with_retry(context, user_config.custom_session_channel, text=start_message, parse_mode=ParseMode.HTML)

            await query.edit_message_text(
                f"🎯 <b>Custom session started!</b>\n\nChannel: {user_config.custom_session_channel}\nDuration: {user_config.custom_session_duration} minutes",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
            )

        # Handle stop custom session
        elif data == 'stop_custom_session':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access custom sessions.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            if not user_config.custom_session_active:
                await query.edit_message_text(
                    "⚠️ <b>No active custom session to stop!</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
                )
                return

            await self.end_custom_session(context, user_config, "manual_stop")
            await query.edit_message_text(
                "⏰ <b>Custom session stopped manually!</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="custom_session_settings")]])
            )

        # Handle template disable settings
        elif data == 'template_disable_settings':
            win_status = "Disabled" if user_config.disable_win_template else "Enabled"
            lose_status = "Disabled" if user_config.disable_lose_template else "Enabled"

            await query.edit_message_text(
                f"📝 <b>Template Disable Options</b>\n\nControl win/loss message templates:\n\n🎉 <b>Win Template:</b> {win_status}\n💫 <b>Lose Template:</b> {lose_status}",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('template_disable_settings', is_admin, user_config)
            )

        # Handle template toggles
        elif data == 'toggle_win_template':
            user_config.disable_win_template = not user_config.disable_win_template
            self.save_user_config(user_id)
            status = "Disabled" if user_config.disable_win_template else "Enabled"
            await query.edit_message_text(
                f"✅ <b>Win template {status.lower()}!</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="template_disable_settings")]])
            )

        elif data == 'toggle_lose_template':
            user_config.disable_lose_template = not user_config.disable_lose_template
            self.save_user_config(user_id)
            status = "Disabled" if user_config.disable_lose_template else "Enabled"
            await query.edit_message_text(
                f"✅ <b>Lose template {status.lower()}!</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="template_disable_settings")]])
            )
        
        # Handle prediction settings
        elif data == 'prediction_settings':
            # Check if user has access to session mode
            has_session_access = self.subscription_manager.can_access_feature(user_id, 'custom_session')

            if has_session_access:
                await query.edit_message_text(
                    "🎲 <b>Prediction Settings</b>\n\nConfigure prediction types and session modes:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=self.get_keyboard('prediction_settings', is_admin, user_config)
                )
            else:
                # Show limited menu without session mode for basic users
                await query.edit_message_text(
                    "🎲 <b>Prediction Settings</b>\n\nConfigure prediction types:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 Set Prediction Type", callback_data="set_prediction_type")],
                        [InlineKeyboardButton("📋 View Channel Types", callback_data="view_channel_types")],
                        [InlineKeyboardButton("💰 Set Base Price", callback_data="set_base_price")],
                        [InlineKeyboardButton("🔙 Back", callback_data="user_settings")]
                    ])
                )

        # Handle session mode settings from prediction settings
        elif data == 'session_mode_settings':
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await query.edit_message_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session modes.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]])
                )
                return

            status = "Custom Session" if user_config.custom_session_enabled else "24/7 Mode"
            await query.edit_message_text(
                f"⚙️ <b>Session Mode</b>\n\nCurrent: <b>{status}</b>\n\nChoose session mode:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('session_mode_settings', is_admin, user_config)
            )
        
        # Handle prediction type selection with BUTTONS
        elif data == 'set_prediction_type':
            if not user_config.channels:
                await query.edit_message_text("❌ <b>No Channels Configured</b>\n\nPlease add channels first!", parse_mode=ParseMode.HTML)
                return
            
            self.user_state[chat_id] = 'awaiting_prediction_type_channel'
            
            # Create channel selection buttons
            keyboard = []
            for channel in user_config.channels:
                current_type = user_config.prediction_type.get(channel, 'big_small')
                keyboard.append([InlineKeyboardButton(
                    f"{channel} ({current_type.upper()})", 
                    callback_data=f"select_channel_{channel}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")])
            
            await query.edit_message_text(
                "📊 <b>Set Prediction Type</b>\n\nSelect a channel to change its prediction type:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Handle channel selection for prediction type
        elif data.startswith('select_channel_'):
            channel = data.replace('select_channel_', '')
            self.user_state[chat_id] = f'awaiting_prediction_type_for_{channel}'
            
            current_type = user_config.prediction_type.get(channel, 'big_small')
            
            await query.edit_message_text(
                f"🎲 <b>Set Prediction Type for {channel}</b>\n\nCurrent type: <b>{current_type.upper()}</b>\n\nSelect new prediction type:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('prediction_type_selection', is_admin, user_config)
            )
        
        # Handle prediction type selection
        elif data in ['pred_type_big_small', 'pred_type_color']:
            # Find which channel we're setting for
            channel = None
            for key, value in self.user_state.items():
                if key == chat_id and value.startswith('awaiting_prediction_type_for_'):
                    channel = value.replace('awaiting_prediction_type_for_', '')
                    break
            
            if channel and channel in user_config.channels:
                pred_type = 'big_small' if data == 'pred_type_big_small' else 'color'
                
                # Check if user has access to color predictions
                if pred_type == 'color' and not self.subscription_manager.can_access_feature(user_id, 'color_predictions'):
                    await query.edit_message_text(
                        "❌ <b>Color predictions require Premium or VIP subscription!</b>",
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="set_prediction_type")]])
                    )
                    return
                
                user_config.prediction_type[channel] = pred_type
                self.save_user_config(user_id)
                
                await query.edit_message_text(
                    f"✅ <b>Prediction type for {channel} set to {pred_type.upper()}</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]])
                )
                
                # Clear state
                if chat_id in self.user_state:
                    del self.user_state[chat_id]
            else:
                await query.edit_message_text(
                    "❌ <b>Channel not found or session expired!</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]])
                )
        
        # Handle view channel types
        elif data == 'view_channel_types':
            types_info = "📋 <b>Channel Prediction Types</b>\n\n"
            if user_config.channels:
                for channel in user_config.channels:
                    pred_type = user_config.prediction_type.get(channel, 'big_small')
                    types_info += f"• {channel}: {pred_type.upper()}\n"
            else:
                types_info += "No channels configured"
            
            await query.edit_message_text(
                types_info,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]])
            )
        
        # Handle base price setting
        elif data == 'set_base_price':
            self.user_state[chat_id] = 'awaiting_base_price'
            await query.edit_message_text(
                f"💰 <b>Set Base Price</b>\n\nCurrent: ₹{user_config.base_price}\n\nSend new base price:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="prediction_settings")]])
            )
        
        # Handle banner settings
        elif data == 'banner_settings':
            banner_status = "✅ Custom" if os.path.exists(user_config.banner_image) else "📁 Default"
            banner_path = user_config.banner_image
            
            # Show current banner
            if os.path.exists(banner_path):
                try:
                    with open(banner_path, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=f"🎨 <b>Current Banner</b>\n\nStatus: {banner_status}\n\nPath: {banner_path}",
                            parse_mode=ParseMode.HTML
                        )
                except Exception as e:
                    logging.error(f"❌ Error sending banner preview: {e}")
            
            await query.edit_message_text(
                f"🎨 <b>Banner Settings</b>\n\nCurrent banner status: {banner_status}\n\nCustomize your prediction table banner:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('banner_settings', is_admin, user_config)
            )
        
        # Handle banner change
        elif data == 'change_banner':
            self.user_state[chat_id] = 'awaiting_banner'
            
            guide = """
🎨 <b>Change Banner - Instructions</b>

📋 <b>Steps to Change Banner:</b>
1. Send your new banner image
2. Image will be saved to user_banners folder
3. New banner will be used in next prediction

⚙️ <b>Banner Requirements:</b>
• Size: 470x240 pixels (Recommended)
• Format: JPG or PNG
• Maximum Size: 5MB

💡 <i>Send your new banner image or use /cancel to abort</i>
"""
            await query.edit_message_text(
                guide,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="banner_settings")]])
            )
        
        # Handle register link settings
        elif data == 'register_link_settings':
            await query.edit_message_text(
                "🔗 <b>Register Link Settings</b>\n\nManage your registration link for predictions:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('register_link_settings', is_admin, user_config)
            )
        
        # Handle set register link
        elif data == 'set_register_link':
            self.user_state[chat_id] = 'awaiting_register_link'
            await query.edit_message_text(
                f"🔗 <b>Set Register Link</b>\n\nCurrent: {user_config.register_link}\n\nSend new register link:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="register_link_settings")]])
            )
        
        # Handle view register link
        elif data == 'view_register_link':
            await query.edit_message_text(
                f"🔗 <b>Your Register Link</b>\n\n{user_config.register_link}\n\nThis link will be included in all prediction messages.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✏️ Change", callback_data="set_register_link"), InlineKeyboardButton("🔙 Back", callback_data="register_link_settings")]])
            )
        
        # Handle admin channel broadcast menu
        elif data == 'admin_channel_broadcast' and is_admin:
            await query.edit_message_text(
                "📢 <b>Channel Broadcast System</b>\n\nSend messages to any user's channels:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('admin_channel_broadcast', is_admin, user_config)
            )
        
        # Handle broadcast to specific channel
        elif data == 'admin_broadcast_specific_channel' and is_admin:
            self.user_state[chat_id] = 'awaiting_broadcast_specific_channel'
            await query.edit_message_text(
                "🎯 <b>Broadcast to Specific Channel</b>\n\nSend channel username (e.g., @mychannel) to broadcast to:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_channel_broadcast")]])
            )
        
        # Handle broadcast to all channels
        elif data == 'admin_broadcast_all_channels' and is_admin:
            self.user_state[chat_id] = 'awaiting_broadcast_all_channels'
            await query.edit_message_text(
                "📢 <b>Broadcast to All Channels</b>\n\nThis will send your message to ALL channels of ALL users.\n\nSend the message you want to broadcast:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_channel_broadcast")]])
            )
        
        # Handle broadcast to user's channels
        elif data == 'admin_broadcast_user_channels' and is_admin:
            self.user_state[chat_id] = 'awaiting_broadcast_user_id'
            await query.edit_message_text(
                "👤 <b>Broadcast to User's Channels</b>\n\nSend User ID to broadcast to all their channels:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_channel_broadcast")]])
            )
        
        # Handle admin panel
        elif data == 'admin_panel' and is_admin:
            await query.edit_message_text(
                "👑 <b>Administrator Control Panel</b>\n\nManage system-wide settings and users:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('admin_panel', is_admin, user_config)
            )
        
        # Handle admin user stats
        elif data == 'admin_all_stats' and is_admin:
            total_users = len(self.users)
            active_users = sum(1 for u in self.users.values() if u.is_active)
            total_subs = len([uid for uid in self.users.keys() if self.subscription_manager.is_subscribed(uid)])
            trial_users = len([uid for uid in self.users.keys() if self.subscription_manager.is_trial(uid) and self.subscription_manager.is_subscribed(uid)])
            
            basic_users = len([uid for uid in self.users.keys() if self.subscription_manager.get_tier(uid) == 'basic' and not self.subscription_manager.is_trial(uid)])
            premium_users = len([uid for uid in self.users.keys() if self.subscription_manager.get_tier(uid) == 'premium'])
            vip_users = len([uid for uid in self.users.keys() if self.subscription_manager.get_tier(uid) == 'vip'])
            
            stats = f"""
👑 <b>System Statistics</b>

👥 <b>Total Users:</b> {total_users}
🎯 <b>Active Users:</b> {active_users}
💳 <b>Subscribed Users:</b> {total_subs}
🎁 <b>Trial Users:</b> {trial_users}
💰 <b>Basic Users:</b> {basic_users}
🚀 <b>Premium Users:</b> {premium_users}
👑 <b>VIP Users:</b> {vip_users}
👨‍💼 <b>Admins:</b> {len(self.admin_ids)}

📊 <b>Currently Active Users:</b>
"""
            active_found = False
            for uid, uconf in self.users.items():
                if uconf.is_active:
                    user_name = uconf.user_name or "Unknown"
                    stats += f"\n• <b>{user_name}</b> (ID: {uid}): {len(uconf.channels)} channels, {uconf.table_counter} predictions"
                    active_found = True
            
            if not active_found:
                stats += "\n• No active users at the moment"
            
            await query.edit_message_text(
                stats,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
            )
        
        # Handle admin control all users
        elif data == 'admin_control_all' and is_admin:
            await query.edit_message_text(
                "🎮 <b>Control All Users</b>\n\nManage predictions for all users:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('admin_control_all', is_admin, user_config)
            )
        
        # Handle admin start all users
        elif data == 'admin_start_all' and is_admin:
            started = 0
            for uid, uconf in self.users.items():
                if not uconf.is_active and uconf.channels:
                    # Check subscription for non-admin users only
                    if uid not in self.admin_ids and self.settings.get('subscription_enabled'):
                        if not self.subscription_manager.is_subscribed(uid):
                            continue
                    
                    uconf.reset_state()
                    uconf.is_active = True
                    self.save_user_config(uid)
                    asyncio.create_task(self.user_prediction_loop(context, uid))
                    started += 1
            
            await query.edit_message_text(
                f"✅ <b>Started predictions for {started} users!</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_control_all")]])
            )
            await self.send_log(context, f"👑 <b>Admin Started All Users</b>\nStarted {started} users")
        
        # Handle admin stop all users
        elif data == 'admin_stop_all' and is_admin:
            stopped = 0
            for uid, uconf in self.users.items():
                if uconf.is_active:
                    uconf.is_active = False
                    self.save_user_config(uid)
                    stopped += 1
            
            await query.edit_message_text(
                f"⏹️ <b>Stopped predictions for {stopped} users!</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_control_all")]])
            )
            await self.send_log(context, f"👑 <b>Admin Stopped All Users</b>\nStopped {stopped} users")
        
        # Handle admin restart all users
        elif data == 'admin_restart_all' and is_admin:
            restarted = 0
            for uid, uconf in self.users.items():
                if uconf.is_active and uconf.channels:
                    uconf.reset_state()
                    self.save_user_config(uid)
                    restarted += 1
            
            await query.edit_message_text(
                f"🔄 <b>Restarted {restarted} users!</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_control_all")]])
            )
            await self.send_log(context, f"👑 <b>Admin Restarted All Users</b>\nRestarted {restarted} users")
        
        # Handle admin broadcast
        elif data == 'admin_broadcast' and is_admin:
            self.user_state[chat_id] = 'awaiting_broadcast'
            await query.edit_message_text(
                "📢 <b>Broadcast Message</b>\n\nSend the message you want to broadcast to all users:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
            )
        
        # Handle admin subscription control
        elif data == 'admin_subscription' and is_admin:
            await query.edit_message_text(
                "💳 <b>Subscription Management</b>\n\nManage user subscriptions:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('admin_subscription', is_admin, user_config)
            )
        
        # Handle admin add subscription
        elif data == 'admin_add_sub' and is_admin:
            self.user_state[chat_id] = 'awaiting_add_sub'
            await query.edit_message_text(
                "➕ <b>Add Subscription</b>\n\nSend User ID to add subscription:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_subscription")]])
            )
        
        # Handle admin add custom subscription
        elif data == 'admin_add_sub_custom' and is_admin:
            self.user_state[chat_id] = 'awaiting_add_sub_custom'
            await query.edit_message_text(
                "➕ <b>Add Custom Subscription</b>\n\nSend UserID:Days:Tier (format: 123456789:30:premium):",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_subscription")]])
            )
        
        # Handle admin list subscriptions
        elif data == 'admin_list_subs' and is_admin:
            active_subs = []
            expired_subs = []
            
            for uid_str, sub_data in self.subscription_manager.subscriptions.items():
                if sub_data.get('is_trial', False):
                    continue
                user_id_int = int(uid_str)
                user_name = self.users[user_id_int].user_name if user_id_int in self.users else "Unknown"
                
                tier = sub_data.get('tier', 'basic')
                sub_type = f"💰 {tier.upper()}"
                
                expiry = datetime.fromisoformat(sub_data['expiry'])
                days_left = (expiry - datetime.now()).days
                
                sub_info = f"{sub_type} <b>{user_name}</b> (ID: {uid_str}): {days_left} days left"
                
                if days_left > 0 and not sub_data.get('is_trial', False):
                    active_subs.append(sub_info)
                else:
                    expired_subs.append(f"❌ Expired: {sub_info}")
            
            subs_text = "📋 <b>Active Subscriptions</b>\n\n"
            
            if active_subs:
                subs_text += "📅 <b>Active Subscriptions:</b>\n" + "\n".join(active_subs)
            else:
                subs_text += "No active subscriptions\n"
            
            if expired_subs:
                subs_text += "\n\n<b>Expired Subscriptions:</b>\n" + "\n".join(expired_subs)
            
            await query.edit_message_text(
                subs_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_subscription")]])
            )
        
        # Handle admin remove subscription
        elif data == 'admin_remove_sub' and is_admin:
            self.user_state[chat_id] = 'awaiting_remove_sub'
            await query.edit_message_text(
                "🚫 <b>Remove Subscription</b>\n\nSend User ID to remove subscription:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_subscription")]])
            )
        
        # Handle admin bot settings
        elif data == 'admin_bot_settings' and is_admin:
            await query.edit_message_text(
                "⚙️ <b>Bot Settings</b>\n\nConfigure system-wide settings:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('admin_bot_settings', is_admin, user_config)
            )
        
        # Handle admin set channel
        elif data == 'admin_set_channel' and is_admin:
            self.user_state[chat_id] = 'awaiting_set_channel'
            await query.edit_message_text(
                f"📢 <b>Set Mandatory Channel</b>\n\nCurrent: {self.settings.get('mandatory_channel')}\n\nSend new channel username:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_bot_settings")]])
            )
        
        # Handle admin set basic price
        elif data == 'admin_set_basic_price' and is_admin:
            self.user_state[chat_id] = 'awaiting_set_basic_price'
            await query.edit_message_text(
                f"💰 <b>Set Basic Price</b>\n\nCurrent: ₹{self.settings.get('basic_price')}\n\nSend new price:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_bot_settings")]])
            )
        
        # Handle admin set premium price
        elif data == 'admin_set_premium_price' and is_admin:
            self.user_state[chat_id] = 'awaiting_set_premium_price'
            await query.edit_message_text(
                f"🚀 <b>Set Premium Price</b>\n\nCurrent: ₹{self.settings.get('premium_price')}\n\nSend new price:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_bot_settings")]])
            )
        
        # Handle admin set vip price
        elif data == 'admin_set_vip_price' and is_admin:
            self.user_state[chat_id] = 'awaiting_set_vip_price'
            await query.edit_message_text(
                f"👑 <b>Set VIP Price</b>\n\nCurrent: ₹{self.settings.get('vip_price')}\n\nSend new price:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_bot_settings")]])
            )
        
        # Handle admin set UPI
        elif data == 'admin_set_upi' and is_admin:
            self.user_state[chat_id] = 'awaiting_set_upi'
            await query.edit_message_text(
                f"💳 <b>Set UPI ID</b>\n\nCurrent: {self.settings.get('payment_upi')}\n\nSend new UPI ID:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_bot_settings")]])
            )
        
        # Handle admin set register link
        elif data == 'admin_set_register_link' and is_admin:
            self.user_state[chat_id] = 'awaiting_admin_set_register_link'
            await query.edit_message_text(
                f"🔗 <b>Set Default Register Link</b>\n\nCurrent: {self.settings.get('default_register_link', 'https://your-registration-link.com')}\n\nSend new default register link for new users:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_bot_settings")]])
            )
        
        # Handle admin toggle subscription
        elif data == 'admin_toggle_sub' and is_admin:
            self.settings['subscription_enabled'] = not self.settings.get('subscription_enabled', True)
            self.save_settings()
            status = "Enabled" if self.settings['subscription_enabled'] else "Disabled"
            await query.edit_message_text(
                f"✅ <b>Subscription system:</b> <b>{status}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_bot_settings")]])
            )
            await self.send_log(context, f"👑 <b>Admin Toggled Subscription System</b>\nStatus: {status}")
        
        # Handle admin user management
        elif data == 'admin_user_mgmt' and is_admin:
            await query.edit_message_text(
                "👥 <b>User Management</b>\n\nManage users and administrators:",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard('admin_user_mgmt', is_admin, user_config)
            )
        
        # Handle admin list users
        elif data == 'admin_list_users' and is_admin:
            user_list = "📋 <b>All Users</b>\n\n"
            for uid, uconf in self.users.items():
                status = "🟢" if uconf.is_active else "🔴"
                
                if self.subscription_manager.is_subscribed(uid):
                    is_trial = self.subscription_manager.is_trial(uid)
                    tier = self.subscription_manager.get_tier(uid)
                    if is_trial:
                        sub = "🎁"
                    elif tier == 'premium':
                        sub = "🚀"
                    elif tier == 'vip':
                        sub = "👑"
                    else:
                        sub = "💰"
                else:
                    sub = "❌"
                
                user_name = uconf.user_name or "Unknown"
                user_list += f"{status} {sub} <b>{user_name}</b> (ID: {uid}): {len(uconf.channels)} channels\n"
            
            await query.edit_message_text(
                user_list,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_mgmt")]])
            )
        
        # Handle admin view user details
        elif data == 'admin_view_user' and is_admin:
            self.user_state[chat_id] = 'awaiting_view_user'
            await query.edit_message_text(
                "🔍 <b>View User Details</b>\n\nSend User ID:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_mgmt")]])
            )
        
        # Handle admin add admin
        elif data == 'admin_add_admin' and is_admin:
            self.user_state[chat_id] = 'awaiting_add_admin'
            await query.edit_message_text(
                "➕ <b>Add Administrator</b>\n\nSend User ID to add as admin:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_mgmt")]])
            )
        
        # Handle admin list admins
        elif data == 'admin_list_admins' and is_admin:
            admins_list = "📋 <b>Administrators</b>\n\n"
            for aid in self.admin_ids:
                user_name = self.users[aid].user_name if aid in self.users else "Unknown"
                admins_list += f"• <b>{user_name}</b> (<code>{aid}</code>)\n"
            
            await query.edit_message_text(
                admins_list,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_mgmt")]])
            )
        
        # Handle admin clear user data
        elif data == 'admin_clear_user_data' and is_admin:
            self.user_state[chat_id] = 'awaiting_clear_user_data'
            await query.edit_message_text(
                "🗑️ <b>Clear User Data</b>\n\nSend User ID to clear all data (channels, settings, predictions):",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_user_mgmt")]])
            )
        
        # Default handler for unknown callbacks
        else:
            keyboard_type = 'admin_main' if is_admin else 'main'
            await query.edit_message_text(
                "👋 <b>Main Menu - AI Prediction System</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard(keyboard_type, is_admin, user_config)
            )
    
    async def end_custom_session(self, context: ContextTypes.DEFAULT_TYPE, user_config, reason="time_limit"):
        """End custom session and send end message"""
        try:
            # Send end media if available
            if user_config.custom_session_end_media:
                await self.send_media_sequence(context, user_config.custom_session_channel, user_config.custom_session_end_media)

            # Send end message
            end_message = self.format_message(user_config.custom_session_end_message, {
                'duration': user_config.custom_session_duration,
                'channel': user_config.custom_session_channel,
                'reason': reason
            })

            await self.send_message_with_retry(context, user_config.custom_session_channel, text=end_message, parse_mode=ParseMode.HTML)

            logging.info(f"[User {user_config.user_id}] ⏰ Custom session ended - {reason}")

        except Exception as e:
            logging.error(f"❌ Error ending custom session for user {user_config.user_id}: {e}")

        # Reset session state
        user_config.custom_session_active = False
        user_config.custom_session_start_time = None
        user_config.custom_session_last_win = None
        self.save_user_config(user_config.user_id)

    def get_tier_features(self, tier):
        """Get features for each tier"""
        features = {
            'Basic': 'Big/Small Predictions, 1 Channel, Standard Templates',
            'Premium': 'All Predictions (Big/Small + Colors), Multiple Channels, Custom Templates, Multiple Media, Language Support, Custom Sessions',
            'VIP': 'All Premium Features, Priority Support, Advanced Analytics, Custom Branding, Custom Sessions'
        }
        return features.get(tier, 'Basic Features')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user messages for media and settings"""
        if not update.effective_user:
            return
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        chat_id = update.effective_chat.id
        message = update.message
        
        if not message:
            return
            
        user_config = self.get_or_create_user(user_id, user_name)
        is_admin = user_id in self.admin_ids
        
        if chat_id not in self.user_state:
            return
        
        state = self.user_state[chat_id]
        text = message.text if message.text else ""
        
        # Handle broadcast messages
        if state == 'awaiting_broadcast' and is_admin:
            success = 0
            failed = 0
            
            for uid in self.users.keys():
                try:
                    if message.photo:
                        await message.copy_to(chat_id=uid)
                    else:
                        await context.bot.send_message(chat_id=uid, text=text, parse_mode=ParseMode.HTML)
                    success += 1
                except Exception as e:
                    failed += 1
            
            await message.reply_text(f"✅ <b>Broadcast completed!</b>\n\nSuccess: {success}\nFailed: {failed}", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
            await self.send_log(context, f"📢 <b>Admin Broadcast Sent</b>\nSuccess: {success}, Failed: {failed}")
        
        # Handle broadcast to specific channel
        elif state == 'awaiting_broadcast_specific_channel' and is_admin:
            if text:
                self.user_state[chat_id] = 'awaiting_broadcast_message_for_channel'
                self.user_state[f'{chat_id}_target_channel'] = text
                await message.reply_text(
                    f"🎯 <b>Channel Selected: {text}</b>\n\nNow send the message you want to broadcast to this channel:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="admin_channel_broadcast")]])
                )
        
        # Handle broadcast message for specific channel
        elif state == 'awaiting_broadcast_message_for_channel' and is_admin:
            target_channel = self.user_state.get(f'{chat_id}_target_channel')
            if target_channel:
                try:
                    if message.photo:
                        await message.copy_to(chat_id=target_channel)
                    elif message.animation:
                        await context.bot.send_animation(chat_id=target_channel, animation=message.animation.file_id, caption=message.caption)
                    elif message.video:
                        await context.bot.send_video(chat_id=target_channel, video=message.video.file_id, caption=message.caption)
                    else:
                        await context.bot.send_message(chat_id=target_channel, text=text, parse_mode=ParseMode.HTML)
                    
                    await message.reply_text(f"✅ <b>Message sent to {target_channel} successfully!</b>", parse_mode=ParseMode.HTML)
                    await self.send_log(context, f"📢 <b>Admin Channel Broadcast</b>\nChannel: {target_channel}\nMessage: {text[:100]}...")
                except Exception as e:
                    await message.reply_text(f"❌ <b>Failed to send to {target_channel}: {str(e)}</b>", parse_mode=ParseMode.HTML)
                
                # Clean up state
                if f'{chat_id}_target_channel' in self.user_state:
                    del self.user_state[f'{chat_id}_target_channel']
                del self.user_state[chat_id]
        
        # Handle broadcast to all channels
        elif state == 'awaiting_broadcast_all_channels' and is_admin:
            all_channels = []
            for uid, uconf in self.users.items():
                for channel in uconf.channels:
                    if channel not in all_channels:
                        all_channels.append(channel)
            
            if not all_channels:
                await message.reply_text("❌ <b>No channels found in the system!</b>", parse_mode=ParseMode.HTML)
                del self.user_state[chat_id]
                return
            
            success = 0
            failed = 0
            failed_channels = []
            
            await message.reply_text(f"📢 <b>Broadcasting to {len(all_channels)} channels...</b>", parse_mode=ParseMode.HTML)
            
            for channel in all_channels:
                try:
                    if message.photo:
                        await message.copy_to(chat_id=channel)
                    elif message.animation:
                        await context.bot.send_animation(chat_id=channel, animation=message.animation.file_id, caption=message.caption)
                    elif message.video:
                        await context.bot.send_video(chat_id=channel, video=message.video.file_id, caption=message.caption)
                    else:
                        await context.bot.send_message(chat_id=channel, text=text, parse_mode=ParseMode.HTML)
                    
                    success += 1
                    await asyncio.sleep(0.1)
                except Exception as e:
                    failed += 1
                    failed_channels.append(f"{channel}: {str(e)[:50]}")
            
            await message.reply_text(
                f"✅ <b>Broadcast completed!</b>\n\n"
                f"📢 <b>Total Channels:</b> {len(all_channels)}\n"
                f"✅ <b>Success:</b> {success}\n"
                f"❌ <b>Failed:</b> {failed}\n\n"
                f"{'⚠️ <b>Failed Channels:</b> ' + ', '.join(failed_channels[:5]) + ('...' if len(failed_channels) > 5 else '') if failed_channels else ''}",
                parse_mode=ParseMode.HTML
            )
            await self.send_log(
                context, 
                f"📢 <b>Admin Broadcast to All Channels</b>\n"
                f"Total: {len(all_channels)}, Success: {success}, Failed: {failed}\n"
                f"Message: {text[:100]}..."
            )
            del self.user_state[chat_id]
        
        # Handle broadcast to user's channels
        elif state == 'awaiting_broadcast_user_id' and is_admin and text and text.isdigit():
            target_user = int(text)
            if target_user in self.users:
                user_config_target = self.users[target_user]
                if not user_config_target.channels:
                    await message.reply_text(f"❌ <b>User {user_config_target.user_name} has no channels configured!</b>", parse_mode=ParseMode.HTML)
                    del self.user_state[chat_id]
                    return
                
                self.user_state[chat_id] = 'awaiting_broadcast_message_for_user'
                self.user_state[f'{chat_id}_target_user'] = target_user
                await message.reply_text(
                    f"👤 <b>User Selected: {user_config_target.user_name}</b>\n"
                    f"📢 <b>Channels:</b> {len(user_config_target.channels)}\n\n"
                    f"Now send the message you want to broadcast to all their channels:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="admin_channel_broadcast")]])
                )
            else:
                await message.reply_text("❌ <b>User not found!</b>", parse_mode=ParseMode.HTML)
                del self.user_state[chat_id]
        
        # Handle broadcast message for user's channels
        elif state == 'awaiting_broadcast_message_for_user' and is_admin:
            target_user = self.user_state.get(f'{chat_id}_target_user')
            if target_user and target_user in self.users:
                user_config_target = self.users[target_user]
                channels = user_config_target.channels
                
                success = 0
                failed = 0
                failed_channels = []
                
                await message.reply_text(f"📢 <b>Broadcasting to {len(channels)} channels of {user_config_target.user_name}...</b>", parse_mode=ParseMode.HTML)
                
                for channel in channels:
                    try:
                        if message.photo:
                            await message.copy_to(chat_id=channel)
                        elif message.animation:
                            await context.bot.send_animation(chat_id=channel, animation=message.animation.file_id, caption=message.caption)
                        elif message.video:
                            await context.bot.send_video(chat_id=channel, video=message.video.file_id, caption=message.caption)
                        else:
                            await context.bot.send_message(chat_id=channel, text=text, parse_mode=ParseMode.HTML)
                        
                        success += 1
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        failed += 1
                        failed_channels.append(f"{channel}: {str(e)[:50]}")
                
                await message.reply_text(
                    f"✅ <b>Broadcast completed for {user_config_target.user_name}!</b>\n\n"
                    f"📢 <b>Total Channels:</b> {len(channels)}\n"
                    f"✅ <b>Success:</b> {success}\n"
                    f"❌ <b>Failed:</b> {failed}\n\n"
                    f"{'⚠️ <b>Failed Channels:</b> ' + ', '.join(failed_channels[:5]) + ('...' if len(failed_channels) > 5 else '') if failed_channels else ''}",
                    parse_mode=ParseMode.HTML
                )
                await self.send_log(
                    context, 
                    f"📢 <b>Admin Broadcast to User's Channels</b>\n"
                    f"User: {user_config_target.user_name} (ID: {target_user})\n"
                    f"Channels: {len(channels)}, Success: {success}, Failed: {failed}\n"
                    f"Message: {text[:100]}..."
                )
                
                # Clean up state
                if f'{chat_id}_target_user' in self.user_state:
                    del self.user_state[f'{chat_id}_target_user']
                del self.user_state[chat_id]
        
        # Handle channel management
        elif state == 'awaiting_add_channel' and text:
            if text.startswith('@') or text.startswith('-100'):
                if text not in user_config.channels:
                    user_config.channels.append(text)
                    user_config.multipliers[text] = 1
                    user_config.prices[text] = user_config.base_price
                    # Set default prediction type
                    user_config.prediction_type[text] = 'big_small'
                    self.save_user_config(user_id)
                    await message.reply_text(f"✅ <b>Channel {text} added successfully!</b>", parse_mode=ParseMode.HTML)
                else:
                    await message.reply_text("⚠️ <b>Channel already exists in your list!</b>", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("❌ <b>Channel must start with @ or -100 for channel IDs</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        elif state == 'awaiting_remove_channel' and text and text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(user_config.channels):
                removed = user_config.channels.pop(idx)
                # Remove associated data
                user_config.multipliers.pop(removed, None)
                user_config.prices.pop(removed, None)
                user_config.prediction_type.pop(removed, None)
                user_config.predictions.pop(removed, None)
                user_config.prediction_tables.pop(removed, None)
                self.save_user_config(user_id)
                await message.reply_text(f"✅ <b>Channel {removed} removed successfully!</b>", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("❌ <b>Invalid channel number!</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        # Handle media setting
        elif state in ['awaiting_win_media', 'awaiting_loss_media', 'awaiting_big_media', 'awaiting_small_media', 'awaiting_red_media', 'awaiting_green_media']:
            if message.animation or message.sticker:
                media_id = message.animation.file_id if message.animation else message.sticker.file_id
                
                if state == 'awaiting_win_media':
                    user_config.win_media_ids.append(media_id)
                    media_type = "Win"
                elif state == 'awaiting_loss_media':
                    user_config.lose_media_ids.append(media_id)
                    media_type = "Loss"
                elif state == 'awaiting_big_media':
                    user_config.big_media_ids.append(media_id)
                    media_type = "Big"
                elif state == 'awaiting_small_media':
                    user_config.small_media_ids.append(media_id)
                    media_type = "Small"
                elif state == 'awaiting_red_media':
                    user_config.red_media_ids.append(media_id)
                    media_type = "Red"
                elif state == 'awaiting_green_media':
                    user_config.green_media_ids.append(media_id)
                    media_type = "Green"
                
                self.save_user_config(user_id)
                await message.reply_text(f"✅ <b>{media_type} media added successfully!</b>\n\nSend another media or click Done.",
                                       parse_mode=ParseMode.HTML,
                                       reply_markup=InlineKeyboardMarkup([[
                                           InlineKeyboardButton("✅ Done", callback_data="media_settings")
                                       ]]))
            elif text and text.lower() == '/done':
                del self.user_state[chat_id]
                await message.reply_text("✅ <b>Media setup completed!</b>", parse_mode=ParseMode.HTML)
        
        # NEW: Handle media deletion
        elif state in ['awaiting_delete_win_media', 'awaiting_delete_loss_media', 'awaiting_delete_big_media', 
                      'awaiting_delete_small_media', 'awaiting_delete_red_media', 'awaiting_delete_green_media']:
            if text and text.isdigit():
                idx = int(text) - 1
                
                if state == 'awaiting_delete_win_media':
                    media_list = user_config.win_media_ids
                    media_type = "Win"
                elif state == 'awaiting_delete_loss_media':
                    media_list = user_config.lose_media_ids
                    media_type = "Loss"
                elif state == 'awaiting_delete_big_media':
                    media_list = user_config.big_media_ids
                    media_type = "Big"
                elif state == 'awaiting_delete_small_media':
                    media_list = user_config.small_media_ids
                    media_type = "Small"
                elif state == 'awaiting_delete_red_media':
                    media_list = user_config.red_media_ids
                    media_type = "Red"
                elif state == 'awaiting_delete_green_media':
                    media_list = user_config.green_media_ids
                    media_type = "Green"
                else:
                    media_list = []
                    media_type = ""
                
                if 0 <= idx < len(media_list):
                    deleted_media = media_list.pop(idx)
                    self.save_user_config(user_id)
                    await message.reply_text(f"✅ <b>{media_type} media deleted successfully!</b>\n\nRemaining {media_type.lower()} media: {len(media_list)}", parse_mode=ParseMode.HTML)
                else:
                    await message.reply_text("❌ <b>Invalid media number!</b>", parse_mode=ParseMode.HTML)
                
                del self.user_state[chat_id]
        
        # Handle template editing
        elif state in ['awaiting_prediction_template', 'awaiting_win_template', 'awaiting_lose_template']:
            if state == 'awaiting_prediction_template':
                user_config.prediction_template = text
                template_type = "Prediction"
            elif state == 'awaiting_win_template':
                user_config.win_template = text
                template_type = "Win"
            elif state == 'awaiting_lose_template':
                user_config.lose_template = text
                template_type = "Loss"
            
            self.save_user_config(user_id)
            del self.user_state[chat_id]
            await message.reply_text(f"✅ <b>{template_type} template updated successfully!</b>", parse_mode=ParseMode.HTML)
        
        # Handle prediction type setting via buttons (fallback)
        elif state.startswith('awaiting_prediction_type_for_') and text:
            channel = state.replace('awaiting_prediction_type_for_', '')
            if channel in user_config.channels and text.lower() in ['big_small', 'color']:
                pred_type = text.lower()
                
                # Check if user has access to color predictions
                if pred_type == 'color' and not self.subscription_manager.can_access_feature(user_id, 'color_predictions'):
                    await message.reply_text("❌ <b>Color predictions require Premium or VIP subscription!</b>", parse_mode=ParseMode.HTML)
                    return
                
                user_config.prediction_type[channel] = pred_type
                self.save_user_config(user_id)
                await message.reply_text(f"✅ <b>Prediction type for {channel} set to {pred_type.upper()}</b>", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("❌ <b>Invalid prediction type! Use 'big_small' or 'color'</b>", parse_mode=ParseMode.HTML)
            
            if chat_id in self.user_state:
                del self.user_state[chat_id]
        
        # Handle base price setting
        elif state == 'awaiting_base_price' and text and text.isdigit():
            user_config.base_price = int(text)
            if not user_config.is_active:
                user_config.current_price = user_config.base_price
            self.save_user_config(user_id)
            await message.reply_text("✅ <b>Base price updated successfully!</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        # Handle banner change
        elif state == 'awaiting_banner':
            if message.photo:
                try:
                    photo = message.photo[-1]
                    photo_file = await photo.get_file()
                    
                    # Ensure user_banners directory exists
                    os.makedirs("user_banners", exist_ok=True)
                    
                    # Download banner to user_banners folder
                    banner_path = f"user_banners/banner_{user_id}.jpg"
                    await photo_file.download_to_drive(banner_path)
                    
                    # Update user config
                    user_config.banner_image = banner_path
                    self.save_user_config(user_id)
                    
                    await message.reply_text("✅ <b>Banner updated successfully!</b>\n\nNew banner will be used in next prediction.", parse_mode=ParseMode.HTML)
                    logging.info(f"✅ User {user_id} updated banner: {banner_path}")
                    
                except Exception as e:
                    logging.error(f"❌ Error updating banner: {e}")
                    await message.reply_text("❌ <b>Error updating banner! Please try again.</b>", parse_mode=ParseMode.HTML)
            
            elif text and text == '/cancel':
                await message.reply_text("❌ <b>Banner change cancelled</b>", parse_mode=ParseMode.HTML)
            
            del self.user_state[chat_id]
        
        # Handle register link setting
        elif state == 'awaiting_register_link' and text:
            user_config.register_link = text
            self.save_user_config(user_id)
            await message.reply_text(f"✅ <b>Register link updated successfully!</b>\n\nNew link: {text}", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        # Handle admin set register link
        elif state == 'awaiting_admin_set_register_link' and is_admin and text:
            self.settings['default_register_link'] = text
            self.save_settings()
            await message.reply_text(f"✅ <b>Default register link updated successfully!</b>\n\nNew default link: {text}", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        # Handle admin subscription management
        elif state == 'awaiting_add_sub' and is_admin and text and text.isdigit():
            target_user = int(text)
            days = self.settings.get('subscription_days', 30)
            expiry = self.subscription_manager.add_subscription(target_user, days, 'basic')
            user_name = self.users[target_user].user_name if target_user in self.users else "Unknown"
            await message.reply_text(f"✅ <b>Basic subscription added for {user_name} (ID: {target_user}) for {days} days (expires: {expiry.strftime('%d %B %Y')})</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
            await self.send_log(context, f"👑 <b>Admin Added Subscription</b>\nUser: {user_name} (ID: {target_user})\nTier: Basic, Days: {days}")
        
        elif state == 'awaiting_add_sub_custom' and is_admin and text:
            try:
                if ':' in text:
                    parts = text.split(':')
                    if len(parts) >= 2:
                        user_id_str = parts[0].strip()
                        days_str = parts[1].strip()
                        tier = parts[2].strip() if len(parts) > 2 else 'basic'
                        
                        target_user = int(user_id_str)
                        days = int(days_str)
                        
                        if days <= 0:
                            await message.reply_text("❌ <b>Days must be a positive number!</b>", parse_mode=ParseMode.HTML)
                            return
                        
                        if tier not in ['basic', 'premium', 'vip']:
                            tier = 'basic'
                        
                        expiry = self.subscription_manager.add_subscription(target_user, days, tier)
                        user_name = self.users[target_user].user_name if target_user in self.users else "Unknown"
                        await message.reply_text(f"✅ <b>Custom {tier} subscription added for {user_name} (ID: {target_user}) for {days} days (expires: {expiry.strftime('%d %B %Y')})</b>", parse_mode=ParseMode.HTML)
                        await self.send_log(context, f"👑 <b>Admin Added Custom Subscription</b>\nUser: {user_name} (ID: {target_user})\nTier: {tier}, Days: {days}")
                    else:
                        await message.reply_text("❌ <b>Invalid format! Use: UserID:Days or UserID:Days:Tier</b>", parse_mode=ParseMode.HTML)
                else:
                    await message.reply_text("❌ <b>Invalid format! Use: UserID:Days or UserID:Days:Tier</b>", parse_mode=ParseMode.HTML)
            except ValueError:
                await message.reply_text("❌ <b>Invalid format! Use: UserID:Days or UserID:Days:Tier</b>", parse_mode=ParseMode.HTML)
            except Exception as e:
                await message.reply_text(f"❌ <b>Error: {e}</b>", parse_mode=ParseMode.HTML)
            
            del self.user_state[chat_id]
        
        elif state == 'awaiting_remove_sub' and is_admin and text and text.isdigit():
            target_user = int(text)
            self.subscription_manager.remove_subscription(target_user)
            user_name = self.users[target_user].user_name if target_user in self.users else "Unknown"
            await message.reply_text(f"✅ <b>Subscription removed for {user_name} (ID: {target_user})</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
            await self.send_log(context, f"👑 <b>Admin Removed Subscription</b>\nUser: {user_name} (ID: {target_user})")
        
        # Handle admin bot settings
        elif state == 'awaiting_set_channel' and is_admin and text:
            self.settings['mandatory_channel'] = text
            self.save_settings()
            await message.reply_text(f"✅ <b>Mandatory channel set to {text}</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        elif state == 'awaiting_set_basic_price' and is_admin and text and text.isdigit():
            self.settings['basic_price'] = int(text)
            self.save_settings()
            await message.reply_text(f"✅ <b>Basic price set to ₹{text}</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        elif state == 'awaiting_set_premium_price' and is_admin and text and text.isdigit():
            self.settings['premium_price'] = int(text)
            self.save_settings()
            await message.reply_text(f"✅ <b>Premium price set to ₹{text}</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        elif state == 'awaiting_set_vip_price' and is_admin and text and text.isdigit():
            self.settings['vip_price'] = int(text)
            self.save_settings()
            await message.reply_text(f"✅ <b>VIP price set to ₹{text}</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        elif state == 'awaiting_set_upi' and is_admin and text:
            self.settings['payment_upi'] = text
            self.save_settings()
            await message.reply_text(f"✅ <b>UPI ID set to {text}</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        # Handle admin user management
        elif state == 'awaiting_add_admin' and is_admin and text and text.isdigit():
            new_admin = int(text)
            if new_admin not in self.admin_ids:
                self.admin_ids.append(new_admin)
                self.save_admin_config()
                user_name = self.users[new_admin].user_name if new_admin in self.users else "Unknown"
                await message.reply_text(f"✅ <b>{user_name} (ID: {new_admin}) added as administrator!</b>", parse_mode=ParseMode.HTML)
                await self.send_log(context, f"👑 <b>New Admin Added</b>\nUser: {user_name} (ID: {new_admin})")
            else:
                await message.reply_text("⚠️ <b>User is already an administrator!</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        elif state == 'awaiting_view_user' and is_admin and text and text.isdigit():
            target = int(text)
            if target in self.users:
                uconf = self.users[target]
                status = "🟢 Active" if uconf.is_active else "🔴 Inactive"
                
                if self.subscription_manager.is_subscribed(target):
                    is_trial = self.subscription_manager.is_trial(target)
                    tier = self.subscription_manager.get_tier(target)
                    if is_trial:
                        sub_status = "🎁 Trial"
                    else:
                        sub_status = f"✅ {tier.upper()}"
                else:
                    sub_status = "❌ Expired"
                
                # Calculate total predictions across all channels
                total_predictions = sum(len(table) for table in uconf.prediction_tables.values())
                total_table_size = uconf.max_table_rows * len(uconf.channels) if uconf.channels else uconf.max_table_rows
                
                # Get channel details
                channels_details = ""
                if uconf.channels:
                    channels_details = "\n\n<b>Channels:</b>\n" + "\n".join([f"• {ch} ({uconf.prediction_type.get(ch, 'big_small')})" for ch in uconf.channels])
                
                # Media counts
                media_counts = f"""
🖼️ <b>Media Counts:</b>
• 🎉 Win: {len(uconf.win_media_ids)}
• 💫 Loss: {len(uconf.lose_media_ids)}
• 🎲 Big: {len(uconf.big_media_ids)}
• 🎲 Small: {len(uconf.small_media_ids)}
• 🎨 Red: {len(uconf.red_media_ids)}
• 🎨 Green: {len(uconf.green_media_ids)}
"""
                
                details = f"""
🔍 <b>User Details - {uconf.user_name or 'Unknown'}</b>

🎯 <b>Status:</b> {status}
💳 <b>Subscription:</b> {sub_status}
📢 <b>Total Channels:</b> {len(uconf.channels)}
💰 <b>Base Price:</b> ₹{uconf.base_price}
🔗 <b>Register Link:</b> {uconf.register_link}
📈 <b>Total Predictions:</b> {uconf.table_counter}
🚀 <b>Multiplier:</b> {uconf.current_multiplier}x
✅ <b>Wins:</b> {uconf.consecutive_wins}
❌ <b>Losses:</b> {uconf.consecutive_losses}
📋 <b>Current Table Size:</b> {total_predictions}/{total_table_size}
🌐 <b>Language:</b> {uconf.language.upper()}
{media_counts}
{channels_details}
"""
                await message.reply_text(details, parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("❌ <b>User not found in the system!</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
        
        elif state == 'awaiting_clear_user_data' and is_admin and text and text.isdigit():
            target = int(text)
            if target in self.users:
                user_name = self.users[target].user_name or "Unknown"
                self.users[target].clear_user_data()
                self.save_user_config(target)
                await message.reply_text(f"✅ <b>All data cleared for {user_name} (ID: {target})!</b>", parse_mode=ParseMode.HTML)
                await self.send_log(context, f"👑 <b>Admin Cleared User Data</b>\nUser: {user_name} (ID: {target})")
            else:
                await message.reply_text("❌ <b>User not found in the system!</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]

        # Handle custom session duration
        elif state == 'awaiting_session_duration' and text and text.isdigit():
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await message.reply_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML
                )
                del self.user_state[chat_id]
                return

            duration = int(text)
            if 1 <= duration <= 1440:  # Max 24 hours
                user_config.custom_session_duration = duration
                self.save_user_config(user_id)
                await message.reply_text(f"✅ <b>Session duration set to {duration} minutes!</b>", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("❌ <b>Duration must be between 1-1440 minutes (24 hours)!</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]

        # Handle session message editing
        elif state in ['awaiting_session_start_message', 'awaiting_session_end_message'] and text:
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await message.reply_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML
                )
                del self.user_state[chat_id]
                return

            if state == 'awaiting_session_start_message':
                user_config.custom_session_start_message = text
                msg_type = "start"
            else:
                user_config.custom_session_end_message = text
                msg_type = "end"

            self.save_user_config(user_id)
            await message.reply_text(f"✅ <b>Session {msg_type} message updated successfully!</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]

        # Handle session media setting
        elif state in ['awaiting_session_start_media', 'awaiting_session_end_media']:
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await message.reply_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML
                )
                del self.user_state[chat_id]
                return

            if message.animation or message.sticker or message.photo or message.video:
                if message.animation:
                    media_id = message.animation.file_id
                elif message.sticker:
                    media_id = message.sticker.file_id
                elif message.photo:
                    media_id = message.photo[-1].file_id
                elif message.video:
                    media_id = message.video.file_id

                if state == 'awaiting_session_start_media':
                    user_config.custom_session_start_media.append(media_id)
                    media_type = "start"
                else:
                    user_config.custom_session_end_media.append(media_id)
                    media_type = "end"

                self.save_user_config(user_id)
                await message.reply_text(
                    f"✅ <b>Session {media_type} media added successfully!</b>\n\nSend another media or click Done.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="session_media_settings")]])
                )
            elif text and text.lower() == '/done':
                del self.user_state[chat_id]
                await message.reply_text("✅ <b>Session media setup completed!</b>", parse_mode=ParseMode.HTML)

        # Handle extra messages
        elif state == 'awaiting_add_extra_message' and text:
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await message.reply_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML
                )
                del self.user_state[chat_id]
                return

            # Parse format: timing:message or timing:message:media_url
            parts = text.split(':', 2)
            if len(parts) >= 2:
                timing = parts[0].strip().lower()
                msg_text = parts[1].strip()
                media_url = parts[2].strip() if len(parts) > 2 else None

                if timing in ['start', 'end']:
                    extra_msg = {
                        'timing': timing,
                        'message': msg_text,
                        'media': [media_url] if media_url else []
                    }
                    user_config.extra_messages.append(extra_msg)
                    self.save_user_config(user_id)

                    await message.reply_text(
                        f"✅ <b>Extra message added!</b>\n\nTiming: {timing.upper()}\nMessage: {msg_text[:50]}...\nMedia: {'Yes' if media_url else 'No'}",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await message.reply_text("❌ <b>Timing must be 'start' or 'end'!</b>", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("❌ <b>Format: timing:message or timing:message:media_url</b>\n\nExample: start:Welcome to session! or end:Session ended:photo123", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]

        elif state == 'awaiting_delete_extra_message' and text and text.isdigit():
            # Check if user has access to custom session
            if not self.subscription_manager.can_access_feature(user_id, 'custom_session'):
                await message.reply_text(
                    "❌ <b>Custom Session is a Premium/VIP feature!</b>\n\nUpgrade to Premium or VIP to access session settings.",
                    parse_mode=ParseMode.HTML
                )
                del self.user_state[chat_id]
                return

            idx = int(text) - 1
            if 0 <= idx < len(user_config.extra_messages):
                deleted = user_config.extra_messages.pop(idx)
                self.save_user_config(user_id)
                await message.reply_text(f"✅ <b>Extra message deleted!</b>\n\nTiming: {deleted['timing'].upper()}\nMessage: {deleted['message'][:30]}...", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("❌ <b>Invalid message number!</b>", parse_mode=ParseMode.HTML)
            del self.user_state[chat_id]
    
    def run(self):
        """Start the bot"""
        application = Application.builder().token(self.token).build()
        
        application.add_handler(CommandHandler(["start", "menu"], self.start))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        application.add_handler(MessageHandler(filters.ALL, self.handle_message))
        
        logging.info("🚀 Starting ADVANCED WinGo Multi-User Bot...")
        logging.info(f"👑 Administrators: {self.admin_ids}")
        logging.info(f"👥 Total Users: {len(self.users)}")
        logging.info(f"💳 Subscription System: {'Enabled' if self.settings.get('subscription_enabled') else 'Disabled'}")
        logging.info(f"💰 Basic Price: ₹{self.settings.get('basic_price', 299)}")
        logging.info(f"🚀 Premium Price: ₹{self.settings.get('premium_price', 599)}")
        logging.info(f"👑 VIP Price: ₹{self.settings.get('vip_price', 999)}")
        logging.info(f"🎁 Trial Period: {self.settings.get('trial_days', 1)} days")
        logging.info(f"🔗 Default Register Link: {self.settings.get('default_register_link', 'https://your-registration-link.com')}")
        logging.info("🎯 FEATURES: Multiple Media, Color Predictions, Language Support, Template Editing, Register Link Management, Custom Sessions")
        logging.info("📊 SUBSCRIPTION: 3 Tiers (Basic, Premium, VIP) - All Monthly")
        logging.info("🌐 LANGUAGES: Multiple Language Support (PREDICTION SYSTEM ONLY)")
        logging.info("📝 TEMPLATES: Fully Customizable")
        logging.info("🎯 CUSTOM SESSIONS: Available for Premium and VIP users only")
        logging.info("🔗 REGISTER LINK: User-customizable registration links")
        logging.info("📢 LOGGING: Comprehensive activity tracking")
        logging.info("🖼️ SEPARATE MEDIA: Big, Small, Red, Green have separate media support")
        logging.info("🗑️ MEDIA MANAGEMENT: Users can delete their media files")
        logging.info("💰 DYNAMIC PRICING: Subscription prices update everywhere automatically")
        logging.info("📢 NEW FEATURE: Admin can broadcast to any user's channels!")
        
        application.run_polling()

# Main execution
if __name__ == "__main__":
    BOT_TOKEN = "6979013732:AAH90hLEMRXl-UZMHBJb7QlJKtJvj29WlOk"

    bot = WinGoBotMultiUser(BOT_TOKEN)
    bot.run()