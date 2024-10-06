import discord
from discord.ext import tasks
import streamlit as st
import asyncio
import os
from datetime import datetime
import threading
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN', st.secrets.get("DISCORD_BOT_TOKEN", "123"))
GUILD_ID = os.getenv('DISCORD_GUILD_ID', st.secrets.get("DISCORD_GUILD_ID", "123"))
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID', st.secrets.get("DISCORD_CHANNEL_ID", "123"))

# Streamlit configs
st.set_page_config(page_title="Discord Bot Monitor")
st.title("Discord Bot Message Monitor")

# Global variables
bot_lock = threading.Lock()
bot_instance = None
stop_event = threading.Event()

class SingletonBot:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SingletonBot, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
        
        self.initialized = True
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        self.client = discord.Client(intents=intents)
        self.is_running = False
        self.messages = []
        self.guild = None
        self.channel = None
        
        @self.client.event
        async def on_ready():
            try:
                self.guild = self.client.get_guild(int(GUILD_ID))
                if not self.guild:
                    raise ValueError(f"Could not find guild with ID {GUILD_ID}")
                
                self.channel = self.guild.get_channel(int(CHANNEL_ID))
                if not self.channel:
                    raise ValueError(f"Could not find channel with ID {CHANNEL_ID} in guild {self.guild.name}")
                
                logger.info(f'{self.client.user} has connected to Discord!')
                logger.info(f'Connected to guild: {self.guild.name}')
                logger.info(f'Monitoring channel: {self.channel.name}')
                
                if 'bot_status' in st.session_state:
                    st.session_state['bot_status'] = f"""
                    Bot connected as {self.client.user}
                    Guild: {self.guild.name}
                    Channel: {self.channel.name}
                    """
                
                if not self.is_running:
                    self.fetch_messages.start()
                    self.is_running = True
            
            except ValueError as e:
                logger.error(str(e))
                if 'bot_status' in st.session_state:
                    st.session_state['bot_status'] = f"Error: {str(e)}"
            except Exception as e:
                logger.error(f"An unexpected error occurred during setup: {str(e)}")
                if 'bot_status' in st.session_state:
                    st.session_state['bot_status'] = f"Error: {str(e)}"

        @tasks.loop(seconds=1)
        async def fetch_messages():
            if self.channel and not stop_event.is_set():
                try:
                    await self.channel.send(str(datetime.now()))
                    '''new_messages = []
                    async for message in self.channel.history(limit=10):
                        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        msg_content = f"{timestamp} - {message.author}: {message.content}"
                        new_messages.append(msg_content)
                    
                    if 'bot_messages' in st.session_state:
                        st.session_state['bot_messages'] = new_messages'''
                
                except discord.errors.HTTPException as e:
                    logger.error(f"HTTP error occurred while fetching messages: {e}")
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Error fetching messages: {str(e)}")
        
        self.fetch_messages = fetch_messages

    async def start_bot(self):
        if not self.is_running:
            try:
                await self.client.start(TOKEN)
            except discord.LoginFailure:
                logger.error("Failed to login. Please check your token.")
                if 'bot_status' in st.session_state:
                    st.session_state['bot_status'] = "Failed to login. Please check your token."
            except Exception as e:
                logger.error(f"An error occurred while starting the bot: {str(e)}")
                if 'bot_status' in st.session_state:
                    st.session_state['bot_status'] = f"Error: {str(e)}"

async def run_bot():
    global bot_instance
    bot_instance = SingletonBot()
    await bot_instance.start_bot()

# Initialize session state
if 'bot_status' not in st.session_state:
    st.session_state['bot_status'] = "Bot not started"
if 'bot_messages' not in st.session_state:
    st.session_state['bot_messages'] = []

# Main content area
status_container = st.empty()
messages_container = st.empty()

# Display current environment settings
st.sidebar.header("Environment Settings")
st.sidebar.text(f"Guild ID: {GUILD_ID}")
st.sidebar.text(f"Channel ID: {CHANNEL_ID}")

if st.sidebar.button("Start Bot"):
    stop_event.clear()
    st.session_state['bot_status'] = "Starting bot..."
    asyncio.run(run_bot())

if st.sidebar.button("Stop Bot"):
    stop_event.set()
    st.session_state['bot_status'] = "Bot stopped"
    if bot_instance and bot_instance.client:
        asyncio.run(bot_instance.client.close())

# Display status and messages
status_container.write(st.session_state['bot_status'])
if st.session_state['bot_messages']:
    messages_container.write("\n".join(st.session_state['bot_messages']))

# Keep the script running
if __name__ == "__main__":
    st.write("Configure settings in the sidebar and click 'Start Bot'")