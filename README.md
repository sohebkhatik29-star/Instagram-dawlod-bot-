# 📥 Movies Instagram Downloader & Group Guardian Bot 🚀

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#)
[![Framework](https://img.shields.io/badge/Framework-Pyrogram-2AA9EE)](https://docs.pyrogram.org/)
[![Platform](https://img.shields.io/badge/Platform-Render%20%7C%20VPS%20%7C%20Termux-orange)](#)
[![Owner](https://img.shields.io/badge/Owner-%40movies__1780-blue?logo=telegram)](https://t.me/movies_1780)
[![Updates](https://img.shields.io/badge/Channel-%40MoviesGroupG3-blue?logo=telegram)](https://t.me/MoviesGroupG3)

A high-speed Telegram Bot and Web Downloader that effortlessly downloads **Instagram Reels, Posts, Carousels, and Videos** with a **live progress bar**, **caption retention**, **force-subscribe verification**, and full **group moderation toolkit**.

- **Repository**: [sohebkhatik29-star/Instagram-dawlod-bot-](https://github.com/sohebkhatik29-star/Instagram-dawlod-bot-)
- **Source Template**: [diractory/insta-downloader](https://github.com/diractory/insta-downloader)
- **Bot Owner**: [@movies_1780](https://t.me/movies_1780)
- **Official Updates Channel**: [https://t.me/MoviesGroupG3](https://t.me/MoviesGroupG3) (`@MoviesGroupG3`)
- **Contact / Author**: `sohebkhatik29@gmail.com`

---

## ✨ Features

- 📥 **Instant Instagram Downloads**: Paste any Instagram Reel, Post, Carousel, or Video link to download in high definition.
- 📊 **Realtime Progress Bar**: Visual percentage and speed meter during both download and Telegram upload.
- 📝 **Show Caption Button**: Interactive inline button allowing users to view the post's original caption at any time.
- 🔒 **Force-Subscribe Gate**: Protect your bot by requiring users to join [@MoviesGroupG3](https://t.me/MoviesGroupG3) before accessing downloads.
- 👮 **Full Group Admin Suite**: Moderation commands like `/mute`, `/unmute`, `/ban`, `/unban`, `/kick`, `/promote`, `/demote`, `/warn`, `/purge`, and `/pin`.
- 🌐 **Built-in Web Downloader**: Includes a lightweight web interface and REST API `/api/download` running alongside the bot.
- 📢 **Owner Broadcast**: Broadcast notices or announcements to all private chat users or groups with a single command.
- ⚡ **Auto-Installer**: Automatically checks and installs any missing Python packages on initial launch.

---

## ⚙️ Environment Configuration (`.env`)

Create a `.env` file in the root directory:

```env
API_ID=12345678                          # From https://my.telegram.org
API_HASH=your_api_hash_here              # From https://my.telegram.org
BOT_TOKEN=your_bot_token_from_botfather  # From @BotFather on Telegram
OWNER_IDS=8192070400                     # Numeric Telegram ID of @movies_1780
FORCE_SUB_CHANNEL=MoviesGroupG3          # Channel username (without @)
UPDATE_CHANNEL_URL=https://t.me/MoviesGroupG3
OWNER_LINK=https://t.me/movies_1780
BOT_NAME="Movies Instagram Downloader"
PORT=8080
```

---

## 🚀 Deployment Methods

### 1. Render Deployment (Recommended - Free)
1. Fork or push this repository to GitHub: `https://github.com/sohebkhatik29-star/Instagram-dawlod-bot-`
2. Sign in to [Render.com](https://render.com) and click **New Web Service**.
3. Connect your GitHub repository.
4. Set:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 main.py`
5. In **Environment Variables**, add:
   - `API_ID`
   - `API_HASH`
   - `BOT_TOKEN`
   - `FORCE_SUB_CHANNEL`: `MoviesGroupG3`
   - `PORT`: `8080`
6. Click **Deploy Web Service**!

---

### 2. VPS / Linux Server Setup
```bash
# Clone the repository
git clone https://github.com/sohebkhatik29-star/Instagram-dawlod-bot-.git
cd Instagram-dawlod-bot-

# Install Python requirements
pip3 install -r requirements.txt

# Configure your environment
cp .env.example .env
nano .env

# Run using systemd or screen
python3 main.py
```

---

### 3. Termux (Android) Setup
```bash
pkg update && pkg upgrade -y
pkg install python git ffmpeg -y
git clone https://github.com/sohebkhatik29-star/Instagram-dawlod-bot-.git
cd Instagram-dawlod-bot-
pip install -r requirements.txt
python main.py
```

---

## 📖 Command Reference

| Command | Permission | Description |
| :--- | :--- | :--- |
| `/start` | Everyone | Welcome menu, account details, and quick links |
| `Paste Instagram link` | Everyone | Automatic download with real-time progress bar |
| `/dl [link]` | Everyone | Force download specific URL |
| `/ping` | Everyone | Latency and bot uptime test |
| `/id` | Everyone | Get current Telegram chat and user ID |
| `/info` | Everyone | Inspect Telegram user details |
| `/help` | Everyone | View full interactive command list |
| `/mute`, `/unmute` | Group Admin | Restrict or allow member messaging |
| `/ban`, `/unban` | Group Admin | Remove or restore members in group |
| `/kick` | Group Admin | Kick member |
| `/promote`, `/demote`| Group Admin | Manage admin privileges |
| `/pin`, `/unpin` | Group Admin | Manage pinned announcements |
| `/purge` | Group Admin | Delete messages in bulk up to replied message |
| `/warn`, `/resetwarn`| Group Admin | Warn member (3 warnings triggers auto-ban) |
| `/broadcast` | Owner only | Send broadcast message to all users |
| `/gbroadcast` | Owner only | Send broadcast message to all groups |
| `/stats` | Owner only | Total users and active groups analytics |

---

### 👑 Credits & Contacts
- **Bot Owner**: [@movies_1780](https://t.me/movies_1780)
- **Channel Updates**: [@MoviesGroupG3](https://t.me/MoviesGroupG3)
- **Contact**: `sohebkhatik29@gmail.com`
