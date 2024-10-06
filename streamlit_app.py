import streamlit as st
import json
import time
import subprocess
import os
import signal
import psutil

# Constants
STATUS_FILE = 'bot_status.json'
MESSAGES_FILE = 'bot_messages.json'
BOT_SCRIPT = 'discord_bot.py'

# Streamlit configs
st.set_page_config(page_title="Discord Bot Monitor")
st.title("Discord Bot Monitor")

def is_bot_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if BOT_SCRIPT in ' '.join(proc.info['cmdline']):
                return True, proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False, None

def start_bot():
    subprocess.Popen(['python', BOT_SCRIPT])
    time.sleep(5)  # Give the bot some time to start

def stop_bot():
    running, pid = is_bot_running()
    if running and pid:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)  # Give the bot some time to shut down

def read_status():
    try:
        with open(STATUS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('status', 'Status unknown')
    except FileNotFoundError:
        return "Bot status file not found"
    except json.JSONDecodeError:
        return "Error reading bot status"

def read_messages():
    try:
        with open(MESSAGES_FILE, 'r') as f:
            data = json.load(f)
            return data.get('messages', [])
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

# Sidebar
st.sidebar.header("Bot Controls")
running, pid = is_bot_running()

if running:
    st.sidebar.success(f"Bot is running (PID: {pid})")
    if st.sidebar.button("Stop Bot"):
        stop_bot()
        st.experimental_rerun()
else:
    st.sidebar.warning("Bot is not running")
    if st.sidebar.button("Start Bot"):
        start_bot()
        st.experimental_rerun()

# Display environment settings
st.sidebar.header("Environment Settings")
st.sidebar.text(f"Guild ID: {os.getenv('DISCORD_GUILD_ID', 'Not set')}")
st.sidebar.text(f"Channel ID: {os.getenv('DISCORD_CHANNEL_ID', 'Not set')}")

# Main content
status_container = st.empty()
messages_container = st.empty()

def update_display():
    status = read_status()
    messages = read_messages()
    
    status_container.write(f"Bot Status: {status}")
    if messages:
        messages_container.write("\n".join(messages))
    else:
        messages_container.write("No messages yet")

# Auto-refresh
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 1, 60, 5)

if auto_refresh:
    while True:
        update_display()
        time.sleep(refresh_interval)
else:
    update_display()