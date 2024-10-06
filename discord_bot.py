import discord
from discord.ext import tasks
import os
import json
import asyncio
import signal
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN', '123')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', '123'))
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', '123'))

# File for communication with Streamlit
STATUS_FILE = 'bot_status.json'
MESSAGES_FILE = 'bot_messages.json'

class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        self.client = discord.Client(intents=intents)
        self.guild = None
        self.channel = None
        self.setup_events()

    def setup_events(self):
        @self.client.event
        async def on_ready():
            try:
                self.guild = self.client.get_guild(GUILD_ID)
                if not self.guild:
                    raise ValueError(f"Could not find guild with ID {GUILD_ID}")
                
                self.channel = self.guild.get_channel(CHANNEL_ID)
                if not self.channel:
                    raise ValueError(f"Could not find channel with ID {CHANNEL_ID} in guild {self.guild.name}")
                
                logger.info(f'{self.client.user} has connected to Discord!')
                logger.info(f'Connected to guild: {self.guild.name}')
                logger.info(f'Monitoring channel: {self.channel.name}')
                
                self.update_status(f"Bot connected as {self.client.user}")
                self.fetch_messages.start()
            
            except Exception as e:
                logger.error(f"Error in on_ready: {str(e)}")
                self.update_status(f"Error: {str(e)}")

        @tasks.loop(seconds=60)
        async def fetch_messages():
            if self.channel:
                try:
                    await self.channel.send(str(datetime.now()))
                    '''messages = []
                    async for message in self.channel.history(limit=10):
                        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        msg_content = f"{timestamp} - {message.author}: {message.content}"
                        messages.append(msg_content)
                    
                    self.save_messages(messages)'''
                except Exception as e:
                    logger.error(f"Error fetching messages: {str(e)}")

        self.fetch_messages = fetch_messages

    def update_status(self, status):
        try:
            with open(STATUS_FILE, 'w') as f:
                json.dump({"status": status, "timestamp": datetime.now().isoformat()}, f)
        except Exception as e:
            logger.error(f"Error updating status: {str(e)}")

    def save_messages(self, messages):
        try:
            with open(MESSAGES_FILE, 'w') as f:
                json.dump({"messages": messages, "timestamp": datetime.now().isoformat()}, f)
        except Exception as e:
            logger.error(f"Error saving messages: {str(e)}")

    async def start(self):
        try:
            await self.client.start(TOKEN)
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            self.update_status(f"Error: {str(e)}")

async def main():
    bot = DiscordBot()
    
    def signal_handler(signum, frame):
        logger.info("Signal received, closing bot...")
        asyncio.create_task(bot.client.close())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, closing bot...")
    finally:
        await bot.client.close()

if __name__ == "__main__":
    asyncio.run(main())