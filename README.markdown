# 3D Print Order Bot

A Telegram bot for 3D print orders, supporting STL, OBJ, STEP, and IGES files. Calculates volume, generates screenshots, saves files to Google Drive, and logs orders in Google Sheets.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   npm install three three-stdlib
   ```

2. **Environment Variables**:
   Create a `.env` file:
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

3. **Run locally**:
   ```bash
   python -m src.bot
   ```

4. **Deploy to Render**:
   - Push to GitHub.
   - Create a Web Service with Docker runtime.
   - Set environment variables in Render Dashboard.
   - Deploy using Dockerfile.

## Usage
- Send `/start`, upload a STL/OBJ/STEP/IGES file, specify quantity, and choose technology (FDM/SLA/SLS/Projet 2500W).
- Files are saved to Google Drive, and order details are logged in Google Sheets.

## Notes
- SLDPRT files require conversion to STEP/IGES.
- File size limit: 20 MB.
- Ensure Google Drive/Sheets are shared with the service account.