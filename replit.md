# Telegram File Downloader Bot

## Overview
This is a powerful Telegram bot that downloads and sends files from over 1000 websites, including YouTube, social media platforms, and direct file links. The bot uses yt-dlp for video sites and direct HTTP downloads for other files.

## Project Structure
- `main.py` - Main bot application with Telegram handlers and download logic
- `keep_alive.py` - Flask health check server (runs on port 5000)
- `requirements.txt` - Python dependencies
- `.env` - Environment configuration (API keys and settings)
- `downloads/` - Temporary folder for downloaded files (auto-created, gitignored)

## Current State
**Status:** ✅ Fully operational and running on Replit

The bot is currently running with:
- Python 3.11
- Flask health server on port 5000 (for Replit web preview)
- Telegram bot polling for messages
- All required dependencies installed

## Environment Variables
The following environment variables are configured in `.env`:
- `BOT_TOKEN` - Telegram bot token (from @BotFather)
- `API_ID` - Telegram API ID
- `API_HASH` - Telegram API hash
- `PORT` - Flask server port (default: 5000 for Replit)
- `PROXY_URL` - Optional proxy for restricted environments
- `ALLOW_DOWNLOAD_VIA_PROXY` - Use proxy for downloads (default: false)
- `DIRECT_SEND_ONLY` - Skip local downloads, use Telegram direct send only (default: false)

## Features
- 🎬 Downloads from 1000+ video sites via yt-dlp (YouTube, Vimeo, TikTok, etc.)
- 📥 Direct file downloads from any URL
- 📹 Sends videos as video files with streaming support
- 📄 Sends other files as documents
- 📊 Shows download progress with size and speed
- ⚡ No file size limits (within Telegram's limits)

## Workflow Configuration
- **Name:** telegram-bot
- **Command:** `python main.py`
- **Port:** 5000 (Flask health check server)
- **Output:** Web preview (health endpoints)

## Health Check Endpoints
- `/` - Status check (returns bot info)
- `/health` - Health status endpoint
- `/ping` - Simple ping endpoint

## Recent Changes
- **2025-11-01:** Imported from GitHub and configured for Replit environment
  - Updated Flask server to use port 5000 (Replit standard)
  - Installed all Python dependencies
  - Configured workflow to run the bot
  - Added Python .gitignore

## User Preferences
- No specific preferences documented yet

## Bot Commands
- `/start` - Welcome message and feature overview
- `/help` - Usage instructions
- Send any valid URL to download and receive the file

## Technical Notes
- The Flask server runs in a separate thread for health checks
- Downloads are stored temporarily in `downloads/` folder
- Files are automatically deleted after sending
- Bot uses long polling (not webhooks) for message updates
- Progress updates are throttled to every 2 seconds to avoid rate limits

## Deployment Notes
- For Replit: Uses port 5000 for web preview (health check)
- For PythonAnywhere: Requires proxy configuration (see PYTHONANYWHERE.md)
- For other hosts: May need to adjust PORT environment variable
