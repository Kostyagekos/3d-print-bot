# 3D Print Order Bot

Telegram-бот для заказов на 3D-печать, поддерживающий STL, OBJ, STEP и IGES файлы. Рассчитывает объем, генерирует скриншоты, сохраняет файлы в Google Drive и логирует заказы в Google Sheets.

## Установка

1. **Установка зависимостей**:
   ```bash
   pip install -r requirements.txt
   npm install three three-stdlib
   ```

2. **Переменные окружения**:
   Создайте файл `.env`:
   ```
   TELEGRAM_API_TOKEN=7238711097:AAEcE1mDj3msHlPBDn65K_201_rgkKGAk2A
   WEBHOOK_URL=https://your-app-name.onrender.com
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   GOOGLE_REFRESH_TOKEN=your_refresh_token
   GOOGLE_DRIVE_FOLDER_ID=your_folder_id
   GOOGLE_SHEET_ID=your_sheet_id
   PORT=10000
   ```

3. **Локальный запуск**:
   ```bash
   python -m src.bot
   ```

4. **Деплой на Render**:
   - Запушьте в GitHub.
   - Создайте Web Service с Docker.
   - Установите переменные окружения в Render Dashboard.
   - Используйте Dockerfile для деплоя.

## Использование
- Отправьте `/start`, загрузите файл STL/OBJ/STEP/IGES, укажите количество, выберите технологию (FDM/SLA/SLS/Projet 2500W).
- Файлы сохраняются в Google Drive, данные заказов — в Google Sheets.

## Примечания
- SLDPRT требует конвертации в STEP/IGES.
- Лимит размера файла: 20 МБ.
- Убедитесь, что Google Drive и Sheets доступны для service account.