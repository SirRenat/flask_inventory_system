import requests
import logging
from flask import current_app

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = None
        self.chat_id = None
        self.base_url = None
    
    def init_app(self, app):
        """Инициализирует бота с настройками из конфига"""
        self.token = app.config.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = app.config.get('TELEGRAM_CHAT_ID')
        if self.token:
            self.base_url = f"https://api.telegram.org/bot{self.token}"
        logger.info(f"Telegram бот инициализирован: токен={bool(self.token)}, chat_id={self.chat_id}")
    
    def send_message(self, text, parse_mode='HTML', disable_web_page_preview=True):
        """Отправляет сообщение в Telegram"""
        if not self.token or not self.chat_id:
            logger.error("Не указан токен бота или chat_id в конфигурации")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': disable_web_page_preview
            }
            
            logger.info(f"Отправляем сообщение в Telegram: {text[:50]}...")
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"✅ Сообщение успешно отправлено в Telegram")
            return True
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Ошибка подключения к Telegram API: {e}")
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"❌ Таймаут при отправке в Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения в Telegram: {e}")
            return False
    
    def send_new_user_notification(self, user):
        """Отправляет уведомление о новом пользователе"""
        if not user:
            return False
        
        try:
            # Получаем общее количество пользователей
            from app.models import User
            total_users = User.query.count()
            
            text = f"""
🚀 <b>НОВЫЙ ПОЛЬЗОВАТЕЛЬ ЗАРЕГИСТРИРОВАЛСЯ!</b>

👤 <b>Пользователь:</b> {user.username}
📧 <b>Email:</b> {user.email}
🏢 <b>Компания:</b> {user.company_name or 'Не указана'}
📞 <b>Телефон:</b> {user.phone or 'Не указан'}
📅 <b>Регистрация:</b> {user.created_at.strftime('%d.%m.%Y %H:%M') if hasattr(user, 'created_at') and user.created_at else 'Только что'}

📊 <b>Всего пользователей:</b> {total_users}
            """
            
            return self.send_message(text)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при формировании уведомления: {e}")
            return False
    
    def send_test_message(self):
        """Отправляет тестовое сообщение"""
        text = "✅ <b>ТЕСТОВОЕ СООБЩЕНИЕ</b>\n\nБот системы продажи остатков работает корректно!"
        return self.send_message(text)

# Создаем глобальный экземпляр бота
telegram_bot = TelegramBot()