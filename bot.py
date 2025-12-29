import json
import os
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Конфигурация
TOKEN = "8357039756:AAHmoQd4WLwQvmpNrrIOYYOY9X5PzSWxbFE"
ADMIN_ID = 7296765144  # Ваш ID
DATA_FILE = "questions.json"

# Глобальные переменные
questions_db = {}
admin_mode = {}

class QuestionDatabase:
    def __init__(self, filename: str):
        self.filename = filename
        self.data = {}
        self.load()
    
    def load(self):
        """Загрузка данных из файла"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except:
                self.data = {}
        else:
            self.data = {}
    
    def save(self):
        """Сохранение данных в файл"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_question(self, question: str, answer: str):
        """Добавление нового вопроса"""
        self.data[question.lower()] = answer
        self.save()
    
    def remove_question(self, question: str):
        """Удаление вопроса"""
        question_lower = question.lower()
        if question_lower in self.data:
            del self.data[question_lower]
            self.save()
            return True
        return False
    
    def get_answer(self, question: str):
        """Получение ответа на вопрос"""
        return self.data.get(question.lower())
    
    def get_all_questions(self):
        """Получение всех вопросов"""
        return list(self.data.keys())

# Инициализация базы данных
db = QuestionDatabase(DATA_FILE)

# Команды для пользователей
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот с ответами на вопросы.

🔍 Просто напишите свой вопрос, и я постараюсь на него ответить.

📋 Чтобы увидеть все доступные вопросы, используйте /list
❓ Чтобы задать вопрос, просто напишите его текстом
    """
    
    if update.effective_user.id == ADMIN_ID:
        welcome_text += "\n\n⚙️ Вы администратор. Используйте /admin для доступа к панели управления"
    
    await update.message.reply_text(welcome_text)

async def list_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все доступные вопросы"""
    questions = db.get_all_questions()
    
    if not questions:
        await update.message.reply_text("📭 В базе данных пока нет вопросов.")
        return
    
    text = "📋 Список доступных вопросов:\n\n"
    for i, question in enumerate(questions, 1):
        text += f"{i}. {question}\n"
    
    text += "\n❓ Чтобы получить ответ, просто напишите вопрос текстом"
    await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # Проверяем, находится ли пользователь в режиме администрирования
    if user_id in admin_mode and admin_mode[user_id] == "waiting_for_question":
        admin_mode[user_id] = {"mode": "waiting_for_answer", "question": message_text}
        await update.message.reply_text("✏️ Теперь отправьте ответ на этот вопрос:")
        return
    
    if user_id in admin_mode and admin_mode[user_id].get("mode") == "waiting_for_answer":
        question = admin_mode[user_id]["question"]
        db.add_question(question, message_text)
        del admin_mode[user_id]
        await update.message.reply_text(f"✅ Вопрос добавлен!\n\n❓ Вопрос: {question}\n💡 Ответ: {message_text}")
        return
    
    # Проверяем, находится ли пользователь в режиме удаления вопроса
    if user_id in admin_mode and admin_mode[user_id] == "waiting_for_delete":
        if db.remove_question(message_text):
            del admin_mode[user_id]
            await update.message.reply_text("✅ Вопрос успешно удален!")
        else:
            await update.message.reply_text("❌ Вопрос не найден в базе данных.")
        return
    
    # Обычный режим: поиск ответа на вопрос
    answer = db.get_answer(message_text)
    
    if answer:
        await update.message.reply_text(f"💡 Ответ:\n\n{answer}")
    else:
        response = "❌ Извините, я не знаю ответ на этот вопрос.\n\n"
        response += "📋 Посмотреть список доступных вопросов: /list"
        
        if user_id == ADMIN_ID:
            response += "\n\n⚙️ Добавить этот вопрос в базу: /admin"
        
        await update.message.reply_text(response)

# Админ-панель
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Панель администратора"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет прав доступа к админ-панели.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить вопрос", callback_data="add_question")],
        [InlineKeyboardButton("🗑️ Удалить вопрос", callback_data="remove_question")],
        [InlineKeyboardButton("📋 Просмотреть все вопросы", callback_data="view_questions")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("❌ Выйти из админ-панели", callback_data="exit_admin")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚙️ Панель администратора:\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback-запросов от кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("⛔ У вас нет прав доступа.")
        return
    
    if query.data == "add_question":
        admin_mode[user_id] = "waiting_for_question"
        await query.edit_message_text(
            "➕ Добавление нового вопроса:\n\n"
            "Пожалуйста, отправьте вопрос, который хотите добавить:"
        )
    
    elif query.data == "remove_question":
        admin_mode[user_id] = "waiting_for_delete"
        await query.edit_message_text(
            "🗑️ Удаление вопроса:\n\n"
            "Пожалуйста, отправьте вопрос, который хотите удалить:"
        )
    
    elif query.data == "view_questions":
        questions = db.get_all_questions()
        
        if not questions:
            text = "📭 В базе данных пока нет вопросов."
        else:
            text = "📋 Список всех вопросов:\n\n"
            for i, question in enumerate(questions, 1):
                answer = db.get_answer(question)
                text += f"{i}. ❓ {question}\n   💡 {answer[:50]}..."
                if len(answer) > 50:
                    text += "..."
                text += "\n\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data == "stats":
        questions_count = len(db.get_all_questions())
        
        text = f"📊 Статистика бота:\n\n"
        text += f"• Всего вопросов в базе: {questions_count}\n"
        text += f"• Администратор: {'Вы'}\n"
        text += f"• ID администратора: {ADMIN_ID}"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data == "back_to_admin":
        await admin_panel_callback(query)
    
    elif query.data == "exit_admin":
        if user_id in admin_mode:
            del admin_mode[user_id]
        await query.edit_message_text("👋 Вы вышли из админ-панели.")

async def admin_panel_callback(query):
    """Обновление сообщения админ-панели"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить вопрос", callback_data="add_question")],
        [InlineKeyboardButton("🗑️ Удалить вопрос", callback_data="remove_question")],
        [InlineKeyboardButton("📋 Просмотреть все вопросы", callback_data="view_questions")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("❌ Выйти из админ-панели", callback_data="exit_admin")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "⚙️ Панель администратора:\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Команда помощи
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    help_text = """
📚 Доступные команды:

/start - Начать работу с ботом
/list - Показать все доступные вопросы
/help - Показать это сообщение

❓ Чтобы получить ответ на вопрос, просто напишите его текстом.

⚙️ Если вы администратор, используйте /admin для доступа к панели управления.
    """
    
    if update.effective_user.id == ADMIN_ID:
        help_text += "\n\n👑 Вы администратор этого бота."
    
    await update.message.reply_text(help_text)

# Основная функция
def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_questions))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Регистрируем обработчики callback-запросов (кнопки)
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
