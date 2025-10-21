# Telegram to cTrader Signal Copier

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![cTrader Version](https://img.shields.io/badge/cTrader-4.5+-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A sophisticated Python application that acts as a bridge between public Telegram signal channels and the **cTrader** platform. It allows you to automatically copy trades from any Telegram channel to your trading account.

This tool listens for new messages, parses them according to your custom rules, and serves the structured trade signals via a local web API to a cTrader cBot. It features a rich web-based dashboard for real-time monitoring, configuration, and performance tracking.

---

### Dashboard Preview

<img width="842" height="587" alt="Project-1" src="https://github.com/user-attachments/assets/166523f6-2484-426a-a798-73ba0f89119f" />



---

## Core Features

*   **Telegram Message Listener:** Monitors multiple Telegram channels in real-time.
*   **Dynamic Signal Parsing:** Configure a unique RegEx for each channel to parse any message format.
*   **Web Dashboard:** A modern, single-page web interface for managing the bot.
*   **Performance Tracking:** Tracks P/L in both pips and USD and displays an equity curve chart for each channel.
*   **cTrader Integration:** Comes with a ready-to-use cBot script for cTrader.
*   **Simple API:** Your cBot communicates via simple HTTP requests to fetch signals and report closed trades.

---

## Setup Guide: Step-by-Step

Follow these steps carefully to get the entire system running.

### Part 1: Backend Setup (Python)

#### Step 1.1: Install Dependencies

First, get the Python application ready.

```bash
# Clone the repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# Create and activate a virtual environment (recommended)
# On Windows:
python -m venv venv
venv\Scripts\activate
# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

#### Step 1.2: Configure Critical Credentials

This is the most important step. **The application will not work without this.**

1.  Open the `signal_listener.py` file in a code editor.
2.  **Add API Credentials:** Find this section at the top of the file and enter your `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).

    ```python
    # --- 1. CONFIGURATION & DATA PERSISTENCE ---
    API_ID = 12345678; API_HASH = 'your_api_hash_here'; DATA_FILE = "bot_data.json"
    ```

3.  **Add Phone Number:** Scroll down to the bottom of the file to the `STARTUP LOGIC` section. Find the `client.start()` line and enter your full phone number (including country code).

    ```python
    # --- 4. STARTUP LOGIC ---
    async def start_telegram():
        if not initial_channel_ids: log_message("No channels configured.", "WARN"); return
        try: 
            # ADD YOUR PHONE NUMBER HERE
            await client.start(phone='+1234567890') 
            log_message("Telegram client connected.", "SUCCESS")
            await client.run_until_disconnected()
        except Exception as e: log_message(f"FATAL ERROR: {e}", "ERROR")
    ```

    > **WARNING:** Without a valid `API_ID`, `API_HASH`, and `phone` number, the script cannot connect to Telegram and will fail.

---

### Part 2: Frontend Setup (cTrader)

#### Step 2.1: Create the cBot

1.  Open your **cTrader Desktop** application (tested on version 4.5.9).
2.  Navigate to the **Automate** section on the left-hand side.
3.  Click the **"New"** button to create a new cBot.
4.  Name the bot exactly `Copier` and hit Enter.
5.  A new code editor window will open with default template code. **Delete all of it.**
6.  Open the `CTRADE_SCRIPT.cs` file from this project.
7.  **Copy the entire contents** of `CTRADE_SCRIPT.cs` and **paste it** into the cTrader code editor.
8.  Click the **"Build"** button in cTrader. You should see a "Build Successful" message in the log panel at the bottom.

#### Step 2.2: Run and Configure the cBot

1.  In the cBots list, find `Copier` and click the `+` icon to add an instance to a chart (any chart will do, e.g., EURUSD).
2.  A parameters window will appear. **The `Magic Number` is the most important parameter.**
    *   This `Magic Number` must exactly match the `Assigned cBot Magic #` you set for a channel in the web dashboard. This is how the cBot knows which signals to ask for.
3.  Ensure the `Server URL` is correct. If running on the same PC, `http://127.0.0.1:5000` is correct.
4.  Click "OK" and then press the **Play button** on the chart panel to start the cBot.

---

### Part 3: Running the System

1.  **Start the Backend:** In your terminal, run the Python script.
    ```bash
    python signal_listener.py
    ```
    On the very first run, you will be prompted in the terminal to enter a login code sent to your Telegram app. This creates your `bot_session` file.

2.  **Open the Dashboard:** In your web browser, go to `http://localhost:5000`.

3.  **Add & Configure Channels:** Use the dashboard to add Telegram channel IDs and configure their settings (Parser RegEx, Magic Number, etc.).

4.  **Start the cBot:** Press the Play button for the `Copier` instance in cTrader. The bot will now start polling the Python script for signals.

Your system is now live! The Python script listens to Telegram, and the cTrader bot asks the script for trades to execute.

---

## Deployment & Security

When deploying to a new server:

*   **Delete `bot_data.json`:** This file contains your local configurations. The script will generate a new, empty one.
*   **Delete `bot_session`:** This is your Telegram login token. Deleting it forces you to securely re-authenticate on the new server.
*   **Use `.gitignore`:** Never commit `bot_data.json` or `bot_session` to a public repository.

## Disclaimer

**This software is for educational purposes only. Forex trading is highly risky. Do not use this tool with real money unless you fully understand the code and the risks involved. The author is not responsible for any financial losses.**
