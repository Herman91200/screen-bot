# main.py
# Бот: по команде /screenshot делает снимок экрана и отправляет тебе.
# Команда доступна только ADMIN_ID.

import asyncio
import logging
import os
from datetime import datetime

import pyautogui
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

from config import BOT_TOKEN, ADMIN_ID, TEMP_DIR, LOG_PATH


# ---------- Логирование ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Создаём папку для временных файлов
os.makedirs(TEMP_DIR, exist_ok=True)


# ---------- Проверка админа ----------
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ---------- Клавиатура с кнопкой ----------
def get_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопка «Сделать скриншот»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Сделать скриншот", callback_data="make_screenshot")],
    ])


# ---------- Функция скриншота ----------
def take_screenshot() -> str | None:
    """
    Делает скриншот всего экрана и сохраняет во временный файл.
    Возвращает путь к файлу или None при ошибке.
    """
    try:
        # Делаем снимок
        image = pyautogui.screenshot()

        # Имя файла с датой и временем — чтобы не перезаписывать
        filename = f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path = os.path.join(TEMP_DIR, filename)

        # Сохраняем как JPEG (меньше размер, чем PNG)
        image.convert("RGB").save(path, "JPEG", quality=85)

        logger.info(f"✅ Скриншот сохранён: {path}")
        return path

    except Exception as e:
        logger.error(f"❌ Ошибка скриншота: {e}")
        return None


# ---------- Отправка скриншота ----------
async def send_screenshot(chat_id: int, message: Message | None = None) -> None:
    """
    Делает скриншот и отправляет его пользователю.
    Если message не None — отвечает на сообщение; иначе шлёт новое.
    """
    path = take_screenshot()

    if not path:
        # Не смогли сделать скриншот
        text = "❌ Не удалось сделать скриншот. Подробности — в логе."
        if message:
            await message.answer(text)
        else:
            await bot.send_message(chat_id=chat_id, text=text)
        return

    # Подпись с датой и временем
    caption = f"📸 Скриншот от {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"

    try:
        photo = FSInputFile(path)
        if message:
            await message.answer_photo(photo=photo, caption=caption)
        else:
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
        logger.info(f"✅ Скриншот отправлен в чат {chat_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки скриншота: {e}")
        if message:
            await message.answer(f"❌ Не удалось отправить: {e}")

    # Удаляем временный файл, чтобы не копить мусор
    try:
        os.remove(path)
        logger.info(f"🗑 Временный файл удалён: {path}")
    except Exception as e:
        logger.warning(f"Не смог удалить {path}: {e}")


# ---------- /start ----------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Бот приватный.")
        return
    await message.answer(
        "👋 <b>Бот скриншотов</b>\n\n"
        "Команды:\n"
        "/screenshot — сделать скриншот экрана\n\n"
        "Или нажми кнопку ниже 👇",
        reply_markup=get_keyboard(),
    )


# ---------- /screenshot ----------
@dp.message(Command("screenshot"))
async def cmd_screenshot(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Команда только для владельца.")
        return

    await message.answer("⏳ Делаю скриншот...")
    await send_screenshot(chat_id=message.chat.id, message=message)


# ---------- Кнопка «Сделать скриншот» ----------
@dp.callback_query(F.data == "make_screenshot")
async def cb_screenshot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Только для владельца", show_alert=True)
        return

    await callback.answer("Делаю...")
    await send_screenshot(chat_id=callback.message.chat.id, message=callback.message)


# ---------- Игнор всех остальных ----------
@dp.message()
async def any_message(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(
            "Нажми /screenshot или кнопку ниже 👇",
            reply_markup=get_keyboard(),
        )


# ---------- Запуск ----------
async def main():
    logger.info("Бот запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")