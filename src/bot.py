import os
import uuid
import logging
import asyncio
from concurrent.futures import ProcessPoolExecutor
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import trimesh
import io
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IGESControl import IGESControl_Reader
from OCC.Core.TopoDS import topods_Face
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.Topo import Topo

# Загрузка .env
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Инициализация бота
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
executor = ProcessPoolExecutor()

# Цены
PRICES = {
    "FDM": 4.0,
    "SLA": 40.0,
    "SLS": 35.0,
    "Projet 2500W": 1000.0,
}

user_data = {}

def parse_quantity(text):
    digits = ''.join(c for c in text if c.isdigit())
    return int(digits) if digits else 1

# Google API
def get_drive_service():
    creds = Credentials.from_authorized_user_info({
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN")
    }, scopes=["https://www.googleapis.com/auth/drive.file"])
    return build('drive', 'v3', credentials=creds)

def get_sheets_service():
    creds = Credentials.from_authorized_user_info({
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN")
    }, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build('sheets', 'v4', credentials=creds)

async def upload_to_drive(file_path, filename):
    drive_service = get_drive_service()
    file_metadata = {
        "name": filename,
        "parents": [GOOGLE_DRIVE_FOLDER_ID]
    }
    media = MediaIoBaseUpload(io.FileIO(file_path, 'rb'), mimetype='application/octet-stream')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

def append_order_row(data):
    sheets_service = get_sheets_service()
    values = [[
        data["user_id"],
        data["model"],
        data["technology"],
        data["quantity"],
        data["volume"],
        data["total_volume"],
        data["price"],
        data["screenshot_url"],
        data.get("drive_link", "")
    ]]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range="Sheet1!A:I",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

def render_model_screenshot(model_path, output_path):
    import subprocess
    try:
        subprocess.run(["node", "render.js", model_path, output_path], check=True)
    except Exception as e:
        raise RuntimeError(f"Failed to render screenshot: {e}")

def process_step_iges(file_path, extension):
    try:
        if extension == 'step':
            reader = STEPControl_Reader()
        else:  # iges
            reader = IGESControl_Reader()
        reader.ReadFile(file_path)
        reader.TransferRoots()
        shape = reader.OneShape()

        # Меширование для рендеринга
        mesh = BRepMesh_IncrementalMesh(shape, 0.1)
        mesh.Perform()

        # Расчет объема
        volume = 0
        topo = Topo(shape)
        for face in topo.faces():
            surface = BRep_Tool.Surface(face)
            # Упрощенный расчет объема (предполагаем замкнутую модель)
            # Для точности использовать GProp_GProps, но это требует доп. кода
            volume += 0.001  # Заглушка, см³ (заменить на реальный расчет)

        # Сохранение меша как STL для рендеринга
        stl_path = file_path.replace(f'.{extension}', '.stl')
        # Здесь должен быть код для экспорта в STL (например, через OCC)
        # Для простоты используем заглушку
        return volume, stl_path
    except Exception as e:
        raise RuntimeError(f"STEP/IGES processing error: {e}")

async def process_model(model_path, extension):
    loop = asyncio.get_running_loop()
    try:
        if extension in ['stl', 'obj']:
            mesh = await loop.run_in_executor(executor, lambda: trimesh.load(model_path, force='mesh'))
            if not isinstance(mesh, trimesh.Trimesh):
                raise ValueError("Not a valid mesh")
            if len(mesh.faces) > 10000:
                mesh = mesh.simplify_quadratic_decimation(len(mesh.faces) // 2)
            volume = mesh.volume / 1000
            return volume, model_path
        elif extension in ['step', 'iges']:
            volume, stl_path = await loop.run_in_executor(executor, lambda: process_step_iges(model_path, extension))
            return volume, stl_path
        else:
            raise ValueError("Unsupported format")
    except Exception as e:
        raise RuntimeError(f"Model processing error: {e}")

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    user_data[message.from_user.id] = {}
    await message.answer("👋 Пришли STL, OBJ, STEP или IGES файл для расчёта 3D-печати.")

@dp.message(F.document)
async def handle_model(message: Message):
    user_id = message.from_user.id
    file = message.document
    extension = file.file_name.split('.')[-1].lower()

    if extension not in ['stl', 'obj', 'step', 'iges']:
        if extension == 'sldprt':
            await message.answer("❌ SLDPRT не поддерживается. Конвертируйте в STEP/IGES.")
        else:
            await message.answer("❌ Поддерживаются только STL, OBJ, STEP, IGES.")
        return

    if file.file_size > 20 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой (>20 МБ).")
        return

    file_info = await bot.get_file(file.file_id)
    filename = f"temp/{uuid.uuid4()}.{extension}"
    os.makedirs("temp", exist_ok=True)
    await bot.download_file(file_info.file_path, filename)

    try:
        volume, render_path = await process_model(filename, extension)
        screenshot_path = filename.replace(f'.{extension}', '.png')
        await asyncio.get_running_loop().run_in_executor(executor, lambda: render_model_screenshot(render_path, screenshot_path))

        drive_link = await upload_to_drive(filename, file.file_name)

        user_data[user_id] = {
            "filename": filename,
            "volume": volume,
            "screenshot": screenshot_path,
            "drive_link": drive_link
        }

        await message.answer_photo(
            FSInputFile(screenshot_path, filename='screenshot.png'),
            caption=f"📦 Объем модели: {volume:.2f} см³"
        )
        await message.answer("Сколько копий нужно?")
    except Exception as e:
        logging.exception(e)
        await message.answer(f"❌ Ошибка обработки файла: {str(e)}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
        if 'render_path' in locals() and render_path != filename and os.path.exists(render_path):
            os.remove(render_path)

@dp.message(lambda m: m.from_user.id in user_data and "quantity" not in user_data[m.from_user.id])
async def handle_quantity(message: Message):
    user_id = message.from_user.id
    qty = parse_quantity(message.text)
    user_data[user_id]["quantity"] = qty

    kb = InlineKeyboardBuilder()
    for tech in PRICES:
        kb.button(text=tech, callback_data=f"tech_{tech}")
    kb.adjust(2)

    await message.answer(f"Вы указали {qty} шт. Выберите технологию:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("tech_"))
async def handle_technology(callback: CallbackQuery):
    tech = callback.data.split("_")[1]
    user_id = callback.from_user.id
    data = user_data.get(user_id)
    if not data or "volume" not in data:
        await callback.message.answer("❌ Сначала отправьте файл.")
        await callback.answer()
        return

    total_volume = data["volume"] * data["quantity"]
    price = total_volume * PRICES[tech]

    await callback.message.answer(
        f"✅ Технология: {tech}\n📦 Объём: {total_volume:.2f} см³\n💰 Цена: {price:.2f} грн"
    )

    append_order_row({
        "user_id": user_id,
        "model": os.path.basename(data["filename"]),
        "technology": tech,
        "quantity": data["quantity"],
        "volume": data["volume"],
        "total_volume": total_volume,
        "price": price,
        "screenshot_url": data["screenshot"],
        "drive_link": data["drive_link"]
    })

    del user_data[user_id]
    await callback.answer()

# Webhook
WEBHOOK_PATH = "/webhook"

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")

async def on_shutdown(app):
    await bot.delete_webhook()

async def create_app():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    app["bot"] = bot

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp)
    return app

if __name__ == "__main__":
    app = asyncio.run(create_app())
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
