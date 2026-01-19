import os
import json
import logging
import threading
import time
from datetime import datetime
import telebot
from telebot import types
import yt_dlp
import subprocess

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Конфигурация
CONFIG_FILE = 'config.json'
ADMINS_FILE = 'admins.json'
USER_STATS_FILE = 'stats.json'

# Ваши данные
BOT_TOKEN = "8491638240:AAGCSihuQ6GbtMR-Qc7z1j53MB71U2-8538"
ADMIN_ID = 7756791842  # Ваш Telegram ID

class YouTubeDownloaderBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.config = self.load_config()
        self.admins = self.load_admins()
        self.user_stats = self.load_stats()
        
        # Создаем папки
        os.makedirs('downloads', exist_ok=True)
        os.makedirs('temp', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Инициализация вашего админа
        self.admins.add(ADMIN_ID)
        self.save_admins()
        
        # Лог запуска
        logger.info(f"Бот запущен! Админ ID: {ADMIN_ID}")
        
        # Регистрация обработчиков
        self.register_handlers()
        
    def load_config(self):
        """Загрузка конфигурации"""
        default_config = {
            'max_file_size': 1500,  # MB
            'allowed_formats': ['mp4', 'mp3', 'm4a'],
            'max_daily_downloads': 10,
            'welcome_message': '🎬 **YouTube Downloader Bot**\n\nОтправь мне ссылку на YouTube видео или используй команды:\n\n• Просто отправь ссылку\n• /download [ссылка]\n• /audio - для скачивания аудио\n• /formats - доступные форматы\n\n📱 *Работает на Pydroid*',
            'admin_welcome': f'🛠 **Админ-панель**\n\nВаш ID: {ADMIN_ID}\n\nДоступные команды в меню ниже:'
        }
        
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info("Конфиг загружен")
                return config
        except Exception as e:
            logger.warning(f"Конфиг не найден, создан новый: {e}")
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
    
    def save_config(self):
        """Сохранение конфигурации"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Конфиг сохранен")
        except Exception as e:
            logger.error(f"Ошибка сохранения конфига: {e}")
    
    def load_admins(self):
        """Загрузка списка админов"""
        try:
            with open(ADMINS_FILE, 'r') as f:
                admins = set(json.load(f))
                logger.info(f"Загружено {len(admins)} админов")
                return admins
        except Exception as e:
            logger.warning(f"Файл админов не найден, создан новый: {e}")
            # Добавляем основного админа
            admins = {ADMIN_ID}
            with open(ADMINS_FILE, 'w') as f:
                json.dump(list(admins), f)
            return admins
    
    def save_admins(self):
        """Сохранение списка админов"""
        try:
            with open(ADMINS_FILE, 'w') as f:
                json.dump(list(self.admins), f)
            logger.info(f"Сохранено {len(self.admins)} админов")
        except Exception as e:
            logger.error(f"Ошибка сохранения админов: {e}")
    
    def load_stats(self):
        """Загрузка статистики"""
        try:
            with open(USER_STATS_FILE, 'r') as f:
                stats = json.load(f)
                logger.info(f"Загружена статистика для {len(stats)} пользователей")
                return stats
        except Exception as e:
            logger.warning(f"Файл статистики не найден, создан новый: {e}")
            return {}
    
    def save_stats(self):
        """Сохранение статистики"""
        try:
            with open(USER_STATS_FILE, 'w') as f:
                json.dump(self.user_stats, f, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики: {e}")
    
    def is_admin(self, user_id):
        """Проверка прав админа"""
        return user_id in self.admins
    
    def register_handlers(self):
        """Регистрация обработчиков команд"""
        
        @self.bot.message_handler(commands=['start'])
        def start_handler(message):
            user_id = message.from_user.id
            username = message.from_user.username or f"user_{user_id}"
            
            # Регистрация нового пользователя
            if str(user_id) not in self.user_stats:
                self.user_stats[str(user_id)] = {
                    'username': username,
                    'first_name': message.from_user.first_name or '',
                    'downloads_today': 0,
                    'total_downloads': 0,
                    'last_download': None,
                    'first_seen': datetime.now().isoformat(),
                    'last_seen': datetime.now().isoformat()
                }
                logger.info(f"Новый пользователь: {username} (ID: {user_id})")
            else:
                self.user_stats[str(user_id)]['last_seen'] = datetime.now().isoformat()
            
            self.save_stats()
            
            # Приветственное сообщение
            if self.is_admin(user_id):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                btn1 = types.KeyboardButton('📥 Скачать видео')
                btn2 = types.KeyboardButton('🎵 Скачать аудио')
                btn3 = types.KeyboardButton('🛠 Админ-панель')
                btn4 = types.KeyboardButton('📊 Статистика')
                markup.add(btn1, btn2, btn3, btn4)
                
                self.bot.reply_to(message, f"👋 Привет, Администратор!\n\n{self.config['admin_welcome']}", 
                                reply_markup=markup, parse_mode='Markdown')
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                btn1 = types.KeyboardButton('📥 Скачать видео')
                btn2 = types.KeyboardButton('🎵 Скачать аудио')
                btn3 = types.KeyboardButton('📋 Помощь')
                markup.add(btn1, btn2, btn3)
                
                self.bot.reply_to(message, self.config['welcome_message'], 
                                reply_markup=markup, parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['download', 'video'])
        def download_video_handler(message):
            """Скачивание видео"""
            user_id = message.from_user.id
            
            # Проверка лимитов
            if not self.check_limits(user_id):
                self.bot.reply_to(message, "⚠️ *Дневной лимит исчерпан!*\n\nПопробуйте завтра или обратитесь к администратору.", 
                                parse_mode='Markdown')
                return
            
            # Получение URL из сообщения
            text = message.text.replace('/download ', '').replace('/video ', '').strip()
            
            # Если текст пустой, ждем следующее сообщение
            if not text:
                msg = self.bot.reply_to(message, "📎 *Отправьте ссылку на YouTube видео:*", 
                                      parse_mode='Markdown')
                self.bot.register_next_step_handler(msg, self.process_video_download)
                return
            
            self.process_video_download_with_text(message, text)
        
        @self.bot.message_handler(commands=['audio', 'mp3'])
        def download_audio_handler(message):
            """Скачивание аудио"""
            user_id = message.from_user.id
            
            # Проверка лимитов
            if not self.check_limits(user_id):
                self.bot.reply_to(message, "⚠️ *Дневной лимит исчерпан!*\n\nПопробуйте завтра или обратитесь к администратору.", 
                                parse_mode='Markdown')
                return
            
            # Получение URL из сообщения
            text = message.text.replace('/audio ', '').replace('/mp3 ', '').strip()
            
            # Если текст пустой, ждем следующее сообщение
            if not text:
                msg = self.bot.reply_to(message, "📎 *Отправьте ссылку на YouTube видео для конвертации в MP3:*", 
                                      parse_mode='Markdown')
                self.bot.register_next_step_handler(msg, self.process_audio_download)
                return
            
            self.process_audio_download_with_text(message, text)
        
        @self.bot.message_handler(commands=['formats', 'help'])
        def formats_handler(message):
            """Показать доступные форматы"""
            formats = '\n'.join([f"• {fmt}" for fmt in self.config['allowed_formats']])
            help_text = f"""
📁 *Доступные форматы:*
{formats}

*Как использовать:*
1. Отправьте ссылку на YouTube
2. Или используйте команды:
   /download [ссылка] - скачать видео
   /audio [ссылка] - скачать MP3
   
*Ограничения:*
• Макс. размер: {self.config['max_file_size']}MB
• Макс. скачиваний в день: {self.config['max_daily_downloads']}

*Контакты:* [Администратор](tg://user?id={ADMIN_ID})
            """
            self.bot.reply_to(message, help_text, parse_mode='Markdown', disable_web_page_preview=True)
        
        @self.bot.message_handler(commands=['admin'])
        def admin_handler(message):
            """Панель админа"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                self.bot.reply_to(message, "❌ *Доступ запрещен!*", parse_mode='Markdown')
                return
            
            self.show_admin_panel(message)
        
        @self.bot.message_handler(commands=['stats'])
        def stats_handler(message):
            """Статистика для админа"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                self.bot.reply_to(message, "❌ *Доступ запрещен!*", parse_mode='Markdown')
                return
            
            self.show_stats(message)
        
        @self.bot.message_handler(commands=['broadcast'])
        def broadcast_handler(message):
            """Рассылка для админа"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                self.bot.reply_to(message, "❌ *Доступ запрещен!*", parse_mode='Markdown')
                return
            
            msg = self.bot.reply_to(message, "📢 *Введите сообщение для рассылки:*", parse_mode='Markdown')
            self.bot.register_next_step_handler(msg, self.broadcast_message)
        
        @self.bot.message_handler(commands=['users'])
        def users_handler(message):
            """Список пользователей для админа"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                self.bot.reply_to(message, "❌ *Доступ запрещен!*", parse_mode='Markdown')
                return
            
            self.show_users(message)
        
        @self.bot.message_handler(commands=['settings'])
        def settings_handler(message):
            """Настройки для админа"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                self.bot.reply_to(message, "❌ *Доступ запрещен!*", parse_mode='Markdown')
                return
            
            self.show_settings(message)
        
        @self.bot.message_handler(commands=['addadmin'])
        def add_admin_handler(message):
            """Добавить админа"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                self.bot.reply_to(message, "❌ *Доступ запрещен!*", parse_mode='Markdown')
                return
            
            text = message.text.replace('/addadmin ', '').strip()
            if text:
                try:
                    new_admin = int(text)
                    self.add_admin(message, new_admin)
                except:
                    self.bot.reply_to(message, "❌ *Неверный формат ID!*\nИспользуйте: /addadmin [ID]", parse_mode='Markdown')
            else:
                msg = self.bot.reply_to(message, "👥 *Введите ID пользователя для добавления в админы:*", parse_mode='Markdown')
                self.bot.register_next_step_handler(msg, lambda m: self.add_admin_step(m))
        
        @self.bot.message_handler(commands=['restart'])
        def restart_handler(message):
            """Перезапуск бота (только для главного админа)"""
            user_id = message.from_user.id
            
            if user_id != ADMIN_ID:
                self.bot.reply_to(message, "❌ *Только главный администратор может перезапустить бота!*", parse_mode='Markdown')
                return
            
            self.bot.reply_to(message, "🔄 *Перезапуск бота...*", parse_mode='Markdown')
            logger.info("Перезапуск бота по команде администратора")
            os._exit(0)  # Перезапуск через внешний скрипт
        
        # Обработчики кнопок
        @self.bot.message_handler(func=lambda message: True)
        def text_handler(message):
            """Обработка текстовых сообщений"""
            text = message.text
            
            if text == '📥 Скачать видео':
                msg = self.bot.reply_to(message, "📎 *Отправьте ссылку на YouTube видео:*", parse_mode='Markdown')
                self.bot.register_next_step_handler(msg, self.process_video_download)
            
            elif text == '🎵 Скачать аудио':
                msg = self.bot.reply_to(message, "📎 *Отправьте ссылку на YouTube видео для конвертации в MP3:*", parse_mode='Markdown')
                self.bot.register_next_step_handler(msg, self.process_audio_download)
            
            elif text == '🛠 Админ-панель':
                if self.is_admin(message.from_user.id):
                    self.show_admin_panel(message)
                else:
                    self.bot.reply_to(message, "❌ *Доступ запрещен!*", parse_mode='Markdown')
            
            elif text == '📊 Статистика':
                if self.is_admin(message.from_user.id):
                    self.show_stats(message)
                else:
                    # Показываем статистику пользователя
                    user_id = message.from_user.id
                    if str(user_id) in self.user_stats:
                        stats = self.user_stats[str(user_id)]
                        user_stats_text = f"""
📊 *Ваша статистика:*
• Всего скачиваний: {stats['total_downloads']}
• Скачиваний сегодня: {stats['downloads_today']}
• Лимит в день: {self.config['max_daily_downloads']}
• Последнее скачивание: {stats.get('last_download', 'еще не было')}
                        """
                        self.bot.reply_to(message, user_stats_text, parse_mode='Markdown')
                    else:
                        self.bot.reply_to(message, "📭 *Статистика не найдена*", parse_mode='Markdown')
            
            elif text == '📋 Помощь':
                formats_handler(message)
            
            # Если это ссылка YouTube
            elif 'youtube.com' in text or 'youtu.be' in text:
                self.process_video_download_with_text(message, text)
    
    def process_video_download(self, message):
        """Обработка скачивания видео из следующего сообщения"""
        text = message.text.strip()
        self.process_video_download_with_text(message, text)
    
    def process_video_download_with_text(self, message, text):
        """Обработка скачивания видео с текстом"""
        user_id = message.from_user.id
        
        if not text or ('youtube.com' not in text and 'youtu.be' not in text):
            self.bot.reply_to(message, "❌ *Пожалуйста, отправьте валидную ссылку YouTube*", parse_mode='Markdown')
            return
        
        # Проверка лимитов
        if not self.check_limits(user_id):
            self.bot.reply_to(message, "⚠️ *Дневной лимит исчерпан!*", parse_mode='Markdown')
            return
        
        # Отправка сообщения о начале загрузки
        msg = self.bot.reply_to(message, "⏬ *Начинаю скачивание видео...*", parse_mode='Markdown')
        
        # Запуск скачивания в отдельном потоке
        threading.Thread(target=self.download_video, 
                       args=(message.chat.id, text, msg.message_id, user_id, 'video')).start()
    
    def process_audio_download(self, message):
        """Обработка скачивания аудио из следующего сообщения"""
        text = message.text.strip()
        self.process_audio_download_with_text(message, text)
    
    def process_audio_download_with_text(self, message, text):
        """Обработка скачивания аудио с текстом"""
        user_id = message.from_user.id
        
        if not text or ('youtube.com' not in text and 'youtu.be' not in text):
            self.bot.reply_to(message, "❌ *Пожалуйста, отправьте валидную ссылку YouTube*", parse_mode='Markdown')
            return
        
        # Проверка лимитов
        if not self.check_limits(user_id):
            self.bot.reply_to(message, "⚠️ *Дневной лимит исчерпан!*", parse_mode='Markdown')
            return
        
        # Отправка сообщения о начале загрузки
        msg = self.bot.reply_to(message, "⏬ *Начинаю конвертацию в MP3...*", parse_mode='Markdown')
        
        # Запуск скачивания в отдельном потоке
        threading.Thread(target=self.download_video, 
                       args=(message.chat.id, text, msg.message_id, user_id, 'audio')).start()
    
    def check_limits(self, user_id):
        """Проверка лимитов скачивания"""
        user_id = str(user_id)
        today = datetime.now().strftime('%Y-%m-%d')
        
        if user_id not in self.user_stats:
            return True
        
        stats = self.user_stats[user_id]
        
        # Сброс счетчика если прошлый день
        last_download = stats.get('last_download')
        if last_download:
            last_date = datetime.fromisoformat(last_download).strftime('%Y-%m-%d')
            if last_date != today:
                stats['downloads_today'] = 0
        
        return stats.get('downloads_today', 0) < self.config['max_daily_downloads']
    
    def download_video(self, chat_id, url, message_id, user_id, download_type='video'):
        """Скачивание видео/аудио"""
        try:
            # Обновление сообщения
            self.bot.edit_message_text("🔍 *Получаю информацию о видео...*", 
                                     chat_id, message_id, parse_mode='Markdown')
            
            # Опции для yt-dlp
            if download_type == 'audio':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'downloads/%(title)s.%(ext)s',
                    'quiet': False,
                    'no_warnings': False,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'max_filesize': self.config['max_file_size'] * 1024 * 1024,
                }
            else:
                ydl_opts = {
                    'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
                    'outtmpl': 'downloads/%(title)s.%(ext)s',
                    'quiet': False,
                    'no_warnings': False,
                    'max_filesize': self.config['max_file_size'] * 1024 * 1024,
                }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'video')[:50]
                duration = info.get('duration', 0)
                
                # Проверка длительности (макс 2 часа)
                if duration > 7200:  # 2 часа в секундах
                    self.bot.edit_message_text(
                        "❌ *Видео слишком длинное! Максимум 2 часа.*",
                        chat_id, message_id, parse_mode='Markdown'
                    )
                    return
                
                self.bot.edit_message_text(
                    f"📥 *Скачиваю: {title}...*",
                    chat_id, message_id, parse_mode='Markdown'
                )
                
                # Скачивание
                ydl.download([url])
                
                # Поиск скачанного файла
                filename = ydl.prepare_filename(info)
                
                # Для аудио меняем расширение
                if download_type == 'audio':
                    filename = os.path.splitext(filename)[0] + '.mp3'
                
                if not os.path.exists(filename):
                    # Ищем файл с другим расширением
                    base_name = os.path.splitext(filename)[0]
                    for ext in ['.mp4', '.mkv', '.webm', '.mp3', '.m4a']:
                        if os.path.exists(base_name + ext):
                            filename = base_name + ext
                            break
                
                if not os.path.exists(filename):
                    raise FileNotFoundError("Файл не найден после скачивания")
                
                file_size = os.path.getsize(filename) / (1024 * 1024)  # MB
                
                self.bot.edit_message_text(
                    f"📤 *Отправляю файл ({file_size:.1f}MB)...*",
                    chat_id, message_id, parse_mode='Markdown'
                )
                
                # Отправка файла
                try:
                    with open(filename, 'rb') as f:
                        if download_type == 'audio':
                            self.bot.send_audio(chat_id, f, 
                                              title=info.get('title', 'Audio'),
                                              performer=info.get('uploader', 'YouTube'),
                                              caption=f"🎵 *{info.get('title', 'Аудио')}*")
                        else:
                            self.bot.send_video(chat_id, f, 
                                              caption=f"🎬 *{info.get('title', 'Видео')}*",
                                              supports_streaming=True)
                    
                    # Обновление статистики
                    self.update_stats(user_id)
                    
                    self.bot.delete_message(chat_id, message_id)
                    self.bot.send_message(chat_id, "✅ *Скачивание завершено успешно!*", parse_mode='Markdown')
                    
                except Exception as send_error:
                    logger.error(f"Ошибка отправки файла: {send_error}")
                    self.bot.edit_message_text(
                        f"❌ *Ошибка отправки файла: {str(send_error)[:100]}*",
                        chat_id, message_id, parse_mode='Markdown'
                    )
                
                # Удаление файла
                try:
                    os.remove(filename)
                except:
                    pass
                
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Download error: {e}")
            error_msg = str(e)
            if 'File is larger' in error_msg:
                error_msg = f"Файл слишком большой! Максимум {self.config['max_file_size']}MB"
            self.bot.edit_message_text(
                f"❌ *Ошибка при скачивании:*\n`{error_msg[:200]}`",
                chat_id, message_id, parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.bot.edit_message_text(
                f"❌ *Неожиданная ошибка:*\n`{str(e)[:200]}`",
                chat_id, message_id, parse_mode='Markdown'
            )
    
    def update_stats(self, user_id):
        """Обновление статистики пользователя"""
        user_id = str(user_id)
        today = datetime.now().strftime('%Y-%m-%d')
        
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                'downloads_today': 0,
                'total_downloads': 0,
                'last_download': None
            }
        
        # Сброс счетчика если новый день
        last_download = self.user_stats[user_id].get('last_download')
        if last_download:
            last_date = datetime.fromisoformat(last_download).strftime('%Y-%m-%d')
            if last_date != today:
                self.user_stats[user_id]['downloads_today'] = 0
        
        self.user_stats[user_id]['downloads_today'] += 1
        self.user_stats[user_id]['total_downloads'] += 1
        self.user_stats[user_id]['last_download'] = datetime.now().isoformat()
        
        self.save_stats()
        
        # Лог скачивания
        logger.info(f"Пользователь {user_id} скачал файл. Всего: {self.user_stats[user_id]['total_downloads']}")
    
    # АДМИН ФУНКЦИИ
    def show_admin_panel(self, message):
        """Показать панель админа"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton("📊 Статистика", callback_data='admin_stats'),
            types.InlineKeyboardButton("👥 Пользователи", callback_data='admin_users'),
            types.InlineKeyboardButton("⚙️ Настройки", callback_data='admin_settings'),
            types.InlineKeyboardButton("📢 Рассылка", callback_data='admin_broadcast'),
            types.InlineKeyboardButton("➕ Добавить админа", callback_data='admin_add'),
            types.InlineKeyboardButton("🔄 Перезапуск", callback_data='admin_restart')
        ]
        keyboard.add(*buttons)
        
        self.bot.send_message(message.chat.id, 
                            f"🛠 **Панель администратора**\n\nID: `{message.from_user.id}`\nВсего админов: {len(self.admins)}", 
                            reply_markup=keyboard, parse_mode='Markdown')
    
    def show_stats(self, message):
        """Показать статистику"""
        total_users = len(self.user_stats)
        total_downloads = sum([u.get('total_downloads', 0) for u in self.user_stats.values()])
        
        # Активные пользователи (последние 7 дней)
        active_users = 0
        week_ago = datetime.now().timestamp() - 7 * 24 * 3600
        
        for user_data in self.user_stats.values():
            last_seen = user_data.get('last_seen')
            if last_seen:
                last_seen_dt = datetime.fromisoformat(last_seen)
                if last_seen_dt.timestamp() > week_ago:
                    active_users += 1
        
        stats_text = f"""
📊 **Статистика бота:**

• Всего пользователей: {total_users}
• Активных (7 дней): {active_users}
• Всего скачиваний: {total_downloads}
• Админов: {len(self.admins)}

⚙️ **Настройки:**
• Макс. скачиваний в день: {self.config['max_daily_downloads']}
• Макс. размер файла: {self.config['max_file_size']}MB
• Форматы: {', '.join(self.config['allowed_formats'])}

📱 **Система:**
• Папка downloads: {len(os.listdir('downloads')) if os.path.exists('downloads') else 0} файлов
• Папка temp: {len(os.listdir('temp')) if os.path.exists('temp') else 0} файлов
        """
        self.bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')
    
    def show_users(self, message):
        """Показать пользователей"""
        if not self.user_stats:
            self.bot.send_message(message.chat.id, "📭 *Нет данных о пользователях*", parse_mode='Markdown')
            return
        
        users_text = "👥 **Последние 20 пользователей:**\n\n"
        
        # Сортировка по последнему визиту
        sorted_users = sorted(self.user_stats.items(), 
                            key=lambda x: x[1].get('last_seen', ''), 
                            reverse=True)[:20]
        
        for i, (user_id, stats) in enumerate(sorted_users, 1):
            username = stats.get('username', f"ID: {user_id}")
            first_name = stats.get('first_name', '')
            downloads = stats.get('total_downloads', 0)
            
            users_text += f"{i}. {first_name} (@{username})\n"
            users_text += f"   📥: {downloads} скачиваний\n"
            users_text += f"   🆔: `{user_id}`\n\n"
        
        self.bot.send_message(message.chat.id, users_text, parse_mode='Markdown')
    
    def show_settings(self, message):
        """Показать настройки"""
        settings_text = f"""
⚙️ **Текущие настройки:**

• Макс. размер файла: {self.config['max_file_size']}MB
• Допустимые форматы: {', '.join(self.config['allowed_formats'])}
• Лимит скачиваний в день: {self.config['max_daily_downloads']}

**Изменить настройки:**
/set_size [MB] - изменить макс. размер
/set_limit [число] - изменить дневной лимит
        """
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Изменить размер", callback_data='set_size'),
            types.InlineKeyboardButton("Изменить лимит", callback_data='set_limit')
        )
        
        self.bot.send_message(message.chat.id, settings_text, 
                            reply_markup=keyboard, parse_mode='Markdown')
    
    def broadcast_message(self, message):
        """Рассылка сообщения всем пользователям"""
        if not self.is_admin(message.from_user.id):
            return
        
        text = message.text
        if not text:
            self.bot.reply_to(message, "❌ *Сообщение не может быть пустым!*", parse_mode='Markdown')
            return
        
        sent = 0
        failed = 0
        
        progress = self.bot.send_message(message.chat.id, 
                                       f"📢 *Рассылка начата...*\n0/{len(self.user_stats)}", 
                                       parse_mode='Markdown')
        
        for user_id in self.user_stats.keys():
            try:
                self.bot.send_message(user_id, f"📢 *Сообщение от администратора:*\n\n{text}", 
                                    parse_mode='Markdown')
                sent += 1
            except Exception as e:
                failed += 1
                logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            
            # Обновляем прогресс каждые 10 пользователей
            if (sent + failed) % 10 == 0:
                self.bot.edit_message_text(
                    f"📢 *Рассылка...*\n{sent + failed}/{len(self.user_stats)}",
                    progress.chat.id, progress.message_id,
                    parse_mode='Markdown'
                )
        
        self.bot.edit_message_text(
            f"✅ *Рассылка завершена!*\n\n✅ Успешно: {sent}\n❌ Не удалось: {failed}",
            progress.chat.id, progress.message_id,
            parse_mode='Markdown'
        )
        
        # Лог рассылки
        logger.info(f"Рассылка от {message.from_user.id}: отправлено {sent}, не удалось {failed}")
    
    def add_admin_step(self, message):
        """Добавить админа (шаг 2)"""
        try:
            new_admin = int(message.text.strip())
            self.add_admin(message, new_admin)
        except ValueError:
            self.bot.reply_to(message, "❌ *Неверный формат ID!*", parse_mode='Markdown')
    
    def add_admin(self, message, new_admin):
        """Добавить админа"""
        try:
            if new_admin in self.admins:
                self.bot.reply_to(message, f"⚠️ *Пользователь {new_admin} уже админ*", parse_mode='Markdown')
                return
            
            self.admins.add(new_admin)
            self.save_admins()
            
            # Пытаемся уведомить нового админа
            try:
                self.bot.send_message(new_admin, f"🎉 *Вас добавили в администраторы бота!*\n\nID: `{new_admin}`", 
                                    parse_mode='Markdown')
            except:
                pass
            
            self.bot.reply_to(message, f"✅ *Пользователь {new_admin} добавлен в админы*\n\nВсего админов: {len(self.admins)}", 
                            parse_mode='Markdown')
            
            logger.info(f"Добавлен новый админ: {new_admin}")
        except Exception as e:
            self.bot.reply_to(message, f"❌ *Ошибка:* `{str(e)[:100]}`", parse_mode='Markdown')
            logger.error(f"Ошибка добавления админа: {e}")
    
    @self.bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        """Обработчик inline кнопок"""
        user_id = call.from_user.id
        bot_instance = call.bot  # Получаем экземпляр бота
        
        if not self.is_admin(user_id):
            bot_instance.answer_callback_query(call.id, "❌ Доступ запрещен!", show_alert=True)
            return
        
        try:
            if call.data == 'admin_stats':
                self.show_stats(call.message)
            elif call.data == 'admin_users':
                self.show_users(call.message)
            elif call.data == 'admin_settings':
                self.show_settings(call.message)
            elif call.data == 'admin_broadcast':
                bot_instance.send_message(call.message.chat.id, 
                                        "📢 *Введите сообщение для рассылки:*", 
                                        parse_mode='Markdown')
                bot_instance.register_next_step_handler(call.message, self.broadcast_message)
            elif call.data == 'admin_add':
                bot_instance.send_message(call.message.chat.id, 
                                        "👥 *Введите ID пользователя для добавления в админы:*", 
                                        parse_mode='Markdown')
                bot_instance.register_next_step_handler(call.message, self.add_admin_step)
            elif call.data == 'admin_restart':
                if user_id == ADMIN_ID:
                    bot_instance.send_message(call.message.chat.id, 
                                            "🔄 *Перезапуск бота...*", 
                                            parse_mode='Markdown')
                    logger.info("Перезапуск бота по кнопке администратора")
                    os._exit(0)
                else:
                    bot_instance.answer_callback_query(call.id, 
                                                      "❌ Только главный админ может перезапускать!", 
                                                      show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка в callback: {e}")
            bot_instance.answer_callback_query(call.id, f"❌ Ошибка: {str(e)[:50]}", show_alert=True)
        
        bot_instance.answer_callback_query(call.id)
    
    def run(self):
        """Запуск бота"""
        logger.info("=" * 50)
        logger.info(f"БОТ ЗАПУЩЕН!")
        logger.info(f"Админ ID: {ADMIN_ID}")
        logger.info(f"Токен: {BOT_TOKEN[:10]}...")
        logger.info("=" * 50)
        
        # Попытка отправить сообщение админу о запуске
        try:
            self.bot.send_message(ADMIN_ID, 
                                f"🤖 *Бот успешно запущен!*\n\nДата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nID: `{ADMIN_ID}`", 
                                parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение админу: {e}")
        
        # Бесконечный цикл с переподключением
        while True:
            try:
                logger.info("Запуск polling...")
                self.bot.polling(none_stop=True, interval=3, timeout=60)
            except Exception as e:
                logger.error(f"Ошибка polling: {e}")
                time.sleep(5)

# 🚀 ЗАПУСК БОТА
if __name__ == "__main__":
    # Для стабильности на Pydroid
    import sys
    sys.setrecursionlimit(10000)
    
    # Создаем папки если их нет
    os.makedirs('downloads', exist_ok=True)
    os.makedirs('temp', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    print("=" * 50)
    print("🎬 YOUTUBE DOWNLOADER BOT")
    print("📱 Версия для Pydroid")
    print("=" * 50)
    print(f"👑 Админ: {ADMIN_ID}")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print("=" * 50)
    print("Запуск...")
    
    try:
        bot = YouTubeDownloaderBot(BOT_TOKEN)
        bot.run()
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
        time.sleep(10)
