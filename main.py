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
TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '123')  # Default for development
GUILD_ID = os.environ.get('DISCORD_GUILD_ID', '123')  # Default for development
CHANNEL_ID = os.environ.get('DISCORD_CHANNEL_ID', '123')  # Default for development

# Streamlit configs
st.set_page_config(page_title="Discord Bot Monitor")
st.title("Discord Bot Message Monitor")

# Global lock for bot instance
bot_lock = threading.Lock()
bot_instance = None

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
                
                st.session_state['bot_status'] = f"""
                Bot connected as {self.client.user}
                Guild: {self.guild.name}
                Channel: {self.channel.name}
                """
                
                if not self.is_running:
                    self.fetch_messages.start()
                    self.check_connection.start()
                    self.is_running = True
            
            except ValueError as e:
                st.error(str(e))
                logger.error(str(e))
            except Exception as e:
                st.error(f"An unexpected error occurred during setup: {str(e)}")
                logger.error(f"An unexpected error occurred during setup: {str(e)}")

        @tasks.loop(seconds=60)
        async def fetch_messages():
            if self.channel:
                try:
                    async for message in self.channel.history(limit=10):
                        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        msg_content = f"{timestamp} - {message.author}: {message.content}"
                        if msg_content not in self.messages:
                            self.messages.insert(0, msg_content)
                    
                    # Limit the number of stored messages
                    self.messages = self.messages[:100]
                    
                    # Update Streamlit session state
                    st.session_state['bot_messages'] = self.messages.copy()
                
                except discord.errors.HTTPException as e:
                    logger.error(f"HTTP error occurred while fetching messages: {e}")
                    await asyncio.sleep(60)  # Simple backoff
                except Exception as e:
                    logger.error(f"Error fetching messages: {str(e)}")

        @tasks.loop(minutes=5)
        async def check_connection():
            if not self.client.is_ready():
                logger.warning("Bot disconnected, attempting to reconnect...")
                await self.start_bot(TOKEN)
        
        self.fetch_messages = fetch_messages
        self.check_connection = check_connection

    async def start_bot(self, token):
        if not self.is_running:
            try:
                await self.client.start(token)
            except discord.LoginFailure:
                error_msg = "Failed to login. Please check your token."
                st.error(error_msg)
                logger.error(error_msg)
            except Exception as e:
                error_msg = f"An error occurred while starting the bot: {str(e)}"
                st.error(error_msg)
                logger.error(error_msg)

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

def update_display():
    while True:
        status_container.write(st.session_state['bot_status'])
        messages_container.write("\n".join(st.session_state['bot_messages']))
        time.sleep(1)

# Start bot automatically
with bot_lock:
    if bot_instance is None:
        bot_instance = SingletonBot()
        
        # Start the display update thread
        display_thread = threading.Thread(target=update_display, daemon=True)
        display_thread.start()
        
        # Start the bot
        st.write("Starting bot...")
        asyncio.run(bot_instance.start_bot(TOKEN))

def on_shutdown():
    if bot_instance and bot_instance.client:
        asyncio.run(bot_instance.client.close())

st.on_session_end(on_shutdown)

# Keep the script running
if __name__ == "__main__":
    st.write("Bot is running with environment settings.")