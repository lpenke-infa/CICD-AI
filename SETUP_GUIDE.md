# 🚀 IDMC CI/CD Automation - Complete Setup Guide

A comprehensive step-by-step guide to set up the IDMC CI/CD Automation and Slack Bot from scratch.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites Installation](#prerequisites-installation)
- [Project Setup](#project-setup)
- [Slack App Configuration](#slack-app-configuration)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This guide will help you set up the IDMC automation bot even if you're starting from scratch. After completing this guide, you'll have a fully functional Slack bot that can:

- Perform CI/CD migrations between IDMC environments
- Run pre and post-migration validations
- Manage IDMC assets (query, tag, manage projects/folders)
- Respond to natural language queries about your IDMC org

**Time Required**: 30-45 minutes

---

## 🔧 Prerequisites Installation

### Step 1: Install Python

#### Windows

1. **Download Python**
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Download Python 3.9 or higher (3.11 recommended)

2. **Install Python**
   - Run the downloaded installer
   - ✅ **CRITICAL**: Check **"Add Python to PATH"** checkbox
   - Click "Install Now"
   - Wait for installation to complete

3. **Verify Installation**
   ```bash
   # Open Command Prompt (cmd) or PowerShell
   python --version
   # Should show: Python 3.11.x

   pip --version
   # Should show: pip 23.x.x
   ```

#### macOS

```bash
# Option 1: Using Homebrew (Recommended)
# Install Homebrew first if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Verify
python3 --version
pip3 --version

# Option 2: Download from python.org
# Visit python.org/downloads and download the macOS installer
```

#### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.11
sudo apt install python3.11 python3-pip python3.11-venv

# Verify
python3 --version
pip3 --version
```

### Step 2: Install Git (Optional but Recommended)

#### Windows

1. Download Git from [git-scm.com](https://git-scm.com/downloads)
2. Run installer with default settings
3. Verify: Open cmd and run `git --version`

#### macOS

```bash
# Using Homebrew
brew install git

# Verify
git --version
```

#### Linux

```bash
sudo apt install git

# Verify
git --version
```

### Step 3: Text Editor (Optional)

Choose one:
- **VS Code**: [code.visualstudio.com](https://code.visualstudio.com/) (Recommended)
- **Notepad++**: [notepad-plus-plus.org](https://notepad-plus-plus.org/) (Windows)
- **Sublime Text**: [sublimetext.com](https://www.sublimetext.com/)
- Or use any text editor you prefer

---

## 📦 Project Setup

### Step 1: Extract Project Files

```bash
# Extract the CICD_Final.zip to your desired location

# Windows Example
C:\Projects\CICD_Final\

# Mac/Linux Example
~/Projects/CICD_Final/
```

### Step 2: Open Terminal in Project Directory

#### Windows
- Open File Explorer
- Navigate to `C:\Projects\CICD_Final`
- Type `cmd` in the address bar and press Enter
- **OR** Shift + Right-click → "Open PowerShell window here"

#### Mac
- Open Terminal
- Run: `cd ~/Projects/CICD_Final`

#### Linux
- Open Terminal
- Run: `cd ~/Projects/CICD_Final`

### Step 3: Create Virtual Environment

```bash
# Windows
python -m venv venv

# Mac/Linux
python3 -m venv venv
```

**What is a virtual environment?**
It's an isolated Python environment for this project, preventing conflicts with other Python projects.

### Step 4: Activate Virtual Environment

```bash
# Windows (Command Prompt)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Mac/Linux
source venv/bin/activate
```

**Success indicator**: Your terminal prompt should now start with `(venv)`

Example:
```
(venv) C:\Projects\CICD_Final>
```

### Step 5: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages including:
- Slack bot framework and API client
- AI/LangChain integration
- Excel report generation (pandas, openpyxl)
- HTTP clients and utilities

**Installation time**: 2-3 minutes

> 💡 **Tip:** See `requirements.txt` for the complete list of dependencies.

### Step 6: Verify Installation

```bash
pip list | findstr slack
# Windows PowerShell: pip list | Select-String slack
# Mac/Linux: pip list | grep slack

# Should show:
# slack-bolt
# slack-sdk
```

---

## 🤖 Slack App Configuration

### Step 1: Create Slack Workspace (if needed)

1. Go to [slack.com](https://slack.com)
2. Click "Create a new workspace"
3. Follow the prompts
4. Or use an existing workspace where you have admin access

### Step 2: Create Slack App

1. **Go to Slack API**
   - Visit [api.slack.com/apps](https://api.slack.com/apps)
   - Sign in with your Slack account

2. **Create New App**
   - Click **"Create New App"**
   - Choose **"From scratch"**
   - App Name: `IDMC-Automations` (or any name you prefer)
   - Pick your workspace
   - Click **"Create App"**

### Step 3: Configure OAuth Permissions

1. In the left sidebar, click **"OAuth & Permissions"**

2. Scroll to **"Scopes"** section

3. Under **"Bot Token Scopes"**, click **"Add an OAuth Scope"** and add:
   ```
   app_mentions:read       # Read when bot is mentioned
   channels:history        # Read channel messages
   chat:write              # Send messages
   files:write             # Upload files (for Excel reports)
   im:history              # Read direct messages
   im:read                 # View DM info
   im:write                # Send direct messages
   ```

4. Scroll to top and click **"Install to Workspace"**

5. Click **"Allow"**

6. **Copy the Bot User OAuth Token**
   - It starts with `xoxb-`
   - Example: `xoxb-1234567890-1234567890123-abcdefghijklmnopqrstuvwx`
   - ⚠️ **Save this** - you'll need it for `.env` file

### Step 4: Enable Socket Mode

1. In the left sidebar, click **"Socket Mode"**

2. Toggle **"Enable Socket Mode"** to ON

3. You'll be prompted to create an app-level token:
   - Token Name: `socket-token`
   - Add scope: `connections:write`
   - Click **"Generate"**

4. **Copy the App-Level Token**
   - It starts with `xapp-`
   - Example: `xapp-1-A1234ABCD-1234567890-abcdefghijklmnopqrstuvwxyz1234567890abcdefghij`
   - ⚠️ **Save this** - you'll need it for `.env` file

### Step 5: Subscribe to Events

1. In the left sidebar, click **"Event Subscriptions"**

2. Toggle **"Enable Events"** to ON

3. Under **"Subscribe to bot events"**, click **"Add Bot User Event"**:
   ```
   app_mention             # When @bot is mentioned
   message.im              # Direct messages to bot
   ```

4. Click **"Save Changes"** at the bottom

### Step 6: Enable App Home (Optional but Recommended)

1. Click **"App Home"** in sidebar
2. Under "Show Tabs", enable **"Messages Tab"**
3. Check **"Allow users to send Slash commands and messages from the messages tab"**

---

## ⚙️ Environment Configuration

### Step 1: Create `.env` File

In your project directory `C:\Projects\CICD_Final\`:

**Windows (Command Prompt):**
```bash
copy NUL .env
notepad .env
```

**Windows (PowerShell):**
```bash
New-Item .env
notepad .env
```

**Mac/Linux:**
```bash
touch .env
nano .env
# or use your preferred editor
```

### Step 2: Add Configuration to `.env`

Paste this template into `.env` file:

```env
# ============================================
# Slack Configuration (Required)
# ============================================
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# ============================================
# Claude AI Configuration (Required)
# ============================================
# Option 1: Bedrock Endpoint
ANTHROPIC_BEDROCK_BASE_URL=https://your-bedrock-endpoint.amazonaws.com
ANTHROPIC_AUTH_TOKEN=your-aws-auth-token

# Option 2: Direct Anthropic API
# ANTHROPIC_BEDROCK_BASE_URL=https://api.anthropic.com
# ANTHROPIC_AUTH_TOKEN=sk-ant-your-anthropic-api-key

# ============================================
# IDMC Source Environment (Optional - can provide via chat)
# ============================================
IICS_SRC_username=
IICS_SRC_password=
IICS_SRC_region=dm-us

# ============================================
# IDMC Target Environment (Optional - can provide via chat)
# ============================================
IICS_TGT_username=
IICS_TGT_password=
IICS_TGT_region=dm-us

# ============================================
# Additional Configuration (Optional)
# ============================================
# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

### Step 3: Fill in Your Credentials

Replace these values:

1. **SLACK_BOT_TOKEN**: Paste the token from Step 3 (starts with `xoxb-`)
2. **SLACK_APP_TOKEN**: Paste the token from Step 4 (starts with `xapp-`)
3. **ANTHROPIC_BEDROCK_BASE_URL**: Your Claude AI endpoint
4. **ANTHROPIC_AUTH_TOKEN**: Your AI authentication token

**⚠️ IDMC credentials are optional** - you can provide them:
- In `.env` file (for permanent setup)
- Via configuration JSON files
- Through Slack conversation when prompted

### Step 4: Verify `.env` File

```bash
# Check if file exists and has content
# Windows
type .env

# Mac/Linux
cat .env
```

**Security Check:**
- ✅ File should NOT be committed to Git (it's in `.gitignore`)
- ✅ Keep this file private
- ✅ Never share tokens publicly

---

## 🎯 Running the Application

### Step 1: Verify Setup

```bash
# Make sure you're in project directory
cd C:\Projects\CICD_Final  # Windows
cd ~/Projects/CICD_Final   # Mac/Linux

# Make sure virtual environment is activated
# You should see (venv) in prompt
```

If venv is not activated:
```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Step 2: Test Configuration

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Slack Bot Token:', 'Found ✅' if os.getenv('SLACK_BOT_TOKEN') else 'Missing ❌'); print('Slack App Token:', 'Found ✅' if os.getenv('SLACK_APP_TOKEN') else 'Missing ❌')"
```

Expected output:
```
Slack Bot Token: Found ✅
Slack App Token: Found ✅
```

### Step 3: Start the Bot

```bash
python agent.py
```

**Expected Output:**
```
🚀 Starting Refactored CI/CD & IDMC Automation Agent...
📋 Features:
   • Pre-Migration Check (modular tool)
   • CI/CD Migration (modular tool)
   • Post-Migration Validation (modular tool)
   • IDMC Operations (modular tool)
   • Conversational AI powered by Claude Sonnet 4
   • Real-time progress updates

⚡ Bot is now listening for messages and mentions...
```

**If you see errors**, check [Troubleshooting](#troubleshooting) section below.

### Step 4: Test in Slack

1. Open your Slack workspace
2. Find your bot (e.g., `@IDMC-Automations`)
3. Send a direct message: `hello`

**Expected Response:**
```
Hello! I'm your IDMC CI/CD Automation Assistant.

What would you like to do?
1️⃣ Pre-Migration Check
2️⃣ CI/CD Migration
3️⃣ Post-Migration Validation
4️⃣ IDMC Asset Management
```

🎉 **Success!** Your bot is running!

### Step 5: Stopping the Bot

To stop the bot:
- Press `Ctrl + C` in the terminal
- Wait for graceful shutdown

---

## 💬 Usage Examples

### Example 1: Get Asset Count

```
You: how many mappings do we have in the org?

Bot: To get the mapping count, I need your IDMC credentials:
1. Username:
2. Password:
3. Region: (dm-us, dm-eu, dm-ap)

You: 
Username: admin@company.com
Password: mypassword
Region: dm-us

Bot: 📊 Total count: 256 items
```

### Example 2: List Assets with Tag

```
You: list all assets with tag "Production"

Bot: 📊 Found 45 items

Report generated: IDMCFunctionalities_20260628_152318.xlsx

[Excel file is uploaded to Slack]
```

### Example 3: Tag Multiple Assets

```
You: tag these assets with "DemoTest":
- 45dPQypUYMubE7uvuG79AL
- 8Hxli8p7hbSfLiND9fqEYC
- 56bBf1iHpwZle59c5nM2g8

Bot: ⚠️ Skipped 0 unsupported asset(s)
✅ Successfully tagged 3 asset(s)!
```

### Example 4: Run Migration with Config File

```
You: [Upload config_prod.json file to Slack]

Bot: ✅ Configuration file saved: config_prod.json

What would you like to do?
1️⃣ Run pre-migration check
2️⃣ Run CI/CD migration
3️⃣ Run post-migration validation
4️⃣ Just keep it for later

You: 1

Bot: 🔍 Starting Pre-Migration Check...
✅ Logged into Org: Production_Org
📊 Found 150 assets to migrate
[Excel report uploaded]

Would you like to proceed with CI/CD migration?
```

---

## 🐛 Troubleshooting

### Issue 1: "python: command not found"

**Solution:**
```bash
# Windows - Use full path
C:\Python311\python.exe agent.py

# Or add Python to PATH:
# Search "Environment Variables" in Windows
# Edit PATH and add: C:\Python311\

# Mac/Linux - Use python3
python3 agent.py
```

### Issue 2: "No module named 'slack_bolt'"

**Solution:**
```bash
# Make sure venv is activated (should see (venv) in prompt)
# If not, activate it:

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# Then reinstall
pip install -r requirements.txt
```

### Issue 3: "Invalid token" Error

**Solution:**
1. Check `.env` file has correct tokens
2. Tokens should start with:
   - Bot Token: `xoxb-`
   - App Token: `xapp-`
3. Make sure there are no extra spaces
4. If tokens were regenerated, update `.env` with new tokens

### Issue 4: Bot Doesn't Respond

**Checklist:**
- ✅ Is `agent.py` running? (check terminal)
- ✅ Did you see "Bot is now listening" message?
- ✅ Is Socket Mode enabled in Slack app?
- ✅ Are event subscriptions configured?
- ✅ Did you install bot to workspace?
- ✅ In channels, is bot invited? `/invite @bot-name`

### Issue 5: "Permission denied" for .env

**Windows:**
```bash
# Run as administrator or check file permissions
icacls .env
```

**Mac/Linux:**
```bash
chmod 600 .env  # Owner read/write only
```

### Issue 6: Import Error for Local Modules

**Solution:**
```bash
# Make sure you're running from project root
cd C:\Projects\CICD_Final  # Windows
cd ~/Projects/CICD_Final   # Mac/Linux

python agent.py
```

### Issue 7: SSL Certificate Error

**Solution:**
```bash
pip install --upgrade certifi
```

Or add to `.env`:
```env
PYTHONHTTPSVERIFY=0
```

### Viewing Logs

All operations are logged:

```bash
# Windows
type Logs\IDMCFunctionalities.log

# Mac/Linux
tail -f Logs/IDMCFunctionalities.log
```

---

## 📞 Getting Help

If you're still stuck:

1. **Check Logs**: Look in `Logs/` directory for detailed error messages
2. **Verify All Steps**: Re-read this guide and ensure you didn't skip anything
3. **Test Components**:
   ```bash
   # Test Python
   python --version
   
   # Test virtual environment
   pip list
   
   # Test environment variables
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('SLACK_BOT_TOKEN')[:10])"
   ```

---

## ✅ Setup Complete!

You should now have:
- ✅ Python 3.9+ installed
- ✅ Virtual environment created and activated
- ✅ All dependencies installed
- ✅ Slack app configured
- ✅ `.env` file with credentials
- ✅ Bot running and responding in Slack

**Next Steps:**
1. Try the usage examples above
2. Upload or create configuration files in `Configs/`
3. Start automating your IDMC workflows!

---

## 📚 Additional Resources

- **Main README**: See `README.md` for detailed feature documentation
- **Project Structure**: Understand the codebase layout
- **API Reference**: Learn about query filters and asset types
- **Security**: Best practices for credential management

---

**Happy Automating! 🚀**
