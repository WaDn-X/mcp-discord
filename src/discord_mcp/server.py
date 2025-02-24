import os
import asyncio
import logging
import json
import signal
import sys
import atexit
import threading
import ctypes
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from functools import wraps
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord.ext.commands import Bot
from .template_manager import TemplateManager  # Korrigierter Import

# Globale Template-Instanz
templates = TemplateManager()

# Lokale MCP-Klassen
@dataclass
class Tool:
    name: str
    description: str
    inputSchema: Dict[str, Any]

@dataclass
class TextContent:
    type: str = "text"
    text: str = ""

@dataclass
class EmptyResult:
    pass

class Server:
    def __init__(self, name: str):
        self.name = name
        self._tool_list_handler = None
        self._tool_call_handler = None
    
    def list_tools(self):
        def decorator(func):
            self._tool_list_handler = func
            return func
        return decorator
    
    def call_tool(self):
        def decorator(func):
            self._tool_call_handler = func
            return func
        return decorator
        
    def create_initialization_options(self):
        return {"name": self.name}
        
    async def run(self, read_stream: Any, write_stream: Any, options: dict):
        logger.info(f"Starting MCP server: {self.name}")
        while True:
            try:
                # Lese Daten - unterstützt beide Stream-Typen
                try:
                    if hasattr(read_stream, 'receive'):
                        # MemoryObjectReceiveStream
                        data = await read_stream.receive()
                    else:
                        # Standard StreamReader
                        data = await read_stream.readline()
                except anyio.EndOfStream:
                    logger.info("Input stream closed, shutting down MCP server")
                    break

                if not data:
                    logger.info("Input stream closed")
                    # Weitere Verarbeitung folgt hier ...
                    command = json.loads(data.decode('utf-8'))
                    logger.debug(f"Received command: {command}")
                    if command.get("type") == "list_tools" and self._tool_list_handler:
                        tools = await self._tool_list_handler()
                        response = {
                            "type": "tools",
                            "tools": [asdict(tool) for tool in tools]
                        }
                    elif command.get("type") == "call_tool" and self._tool_call_handler:
                        tool_name = command.get("tool")
                        args = command.get("arguments", {})
                        result = await self._tool_call_handler(tool_name, args)
                        response = {
                            "type": "result",
                            "result": [asdict(r) for r in result]
                        }
                    else:
                        response = {
                            "type": "error",
                            "error": "Invalid command or handler not set"
                        }
                        
                    # Sende Antwort - unterstützt beide Stream-Typen
                    response_data = json.dumps(response).encode('utf-8') + b'\n'
                    if hasattr(write_stream, 'send'):
                        # MemoryObjectSendStream
                        await write_stream.send(response_data)
                    else:
                        # Standard StreamWriter
                        write_stream.write(response_data)
                        await write_stream.drain()
                else:
                    # Verarbeite Daten
                    command = json.loads(data.decode('utf-8'))
                    logger.debug(f"Received command: {command}")
                    if command.get("type") == "list_tools" and self._tool_list_handler:
                        tools = await self._tool_list_handler()
                        response = {
                            "type": "tools",
                            "tools": [asdict(tool) for tool in tools]
                        }
                    elif command.get("type") == "call_tool" and self._tool_call_handler:
                        tool_name = command.get("tool")
                        args = command.get("arguments", {})
                        result = await self._tool_call_handler(tool_name, args)
                        response = {
                            "type": "result",
                            "result": [asdict(r) for r in result]
                        }
                    else:
                        response = {
                            "type": "error",
                            "error": "Invalid command or handler not set"
                        }
                        
                    # Sende Antwort - unterstützt beide Stream-Typen
                    response_data = json.dumps(response).encode('utf-8') + b'\n'
                    if hasattr(write_stream, 'send'):
                        # MemoryObjectSendStream
                        await write_stream.send(response_data)
                    else:
                        # Standard StreamWriter
                        write_stream.write(response_data)
                        await write_stream.drain()
                        
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                error_data = json.dumps({"type": "error", "error": str(e)}).encode('utf-8') + b'\n'
                try:
                    if hasattr(write_stream, 'send'):
                        await write_stream.send(error_data)
                    else:
                        write_stream.write(error_data)
                        await write_stream.drain()
                except Exception as e2:
                    logger.error("Failed to send error response", exc_info=True)
            except Exception as e:
                logger.error(f"Error processing command: {e}", exc_info=True)
                error_data = json.dumps({"type": "error", "error": str(e)}).encode('utf-8') + b'\n'
                try:
                    if hasattr(write_stream, 'send'):
                        await write_stream.send(error_data)
                    else:
                        write_stream.write(error_data)
                        await write_stream.drain()
                except Exception as e2:
                    logger.error("Failed to send error response", exc_info=True)

# Entferne die duplizierte stdio_server Funktion (sie ist bereits im mcp.server.stdio Modul)
from mcp.server.stdio import stdio_server
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-mcp-server")

# Lade .env Datei
load_dotenv()

# Bot Configuration
BOT_NAME = os.getenv("BOT_NAME", "WaDn ~ MCP")
ORGA_NAME = os.getenv("ORGA_NAME", "WaDn-X.De")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://wadn-x.de")
DISCORD_INVITE = os.getenv("DISCORD_INVITE", "https://discord.gg/qSVqRDrRbX")

# Discord bot setup
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    print("Error: DISCORD_TOKEN not found in environment variables")
    print("Please create a .env file with your Discord token. See .env.example for reference.")
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Initialize Discord bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True  # DM-Nachrichten aktivieren
bot: Bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)

# Initialize MCP server
app = Server("discord-server")

# Store Discord client reference
discord_client = None

# Füge Dictionary für Benutzer-Status hinzu
welcomed_users = set()

HELP_TEXT = """
**Verfügbare Befehle:**
- `/roles` - Zeigt deine Rollen in allen Servern
- `/help` - Zeigt diese Hilfe
- `/status` - Zeigt den Bot-Status
"""

WELCOME_TEXT = """
👋 Willkommen! Ich bin der Discord-Bot von **WaDn-X.De**!

Um loszulegen, tippe einfach `/help`
- damit zeige ich dir alle verfügbaren Befehle.

Falls du Fragen hast, besuche uns auf https://wadn-x.de
oder Direckt im Discord unter https://discord.gg/qSVqRDrRbX

Viel Spaß! 🚀
"""

# Befehle als Slash-Commands neu definieren
@bot.tree.command(name="roles", description="Zeigt deine Rollen in allen Servern")
async def roles(interaction: discord.Interaction):
    """Zeigt die Rollen des Benutzers"""
    if isinstance(interaction.channel, discord.DMChannel):
        user_roles = []
        for guild in bot.guilds:
            member = guild.get_member(interaction.user.id)
            if member:
                roles = [role.name for role in member.roles if role.name != "@everyone"]
                if roles:
                    user_roles.append(f"Server {guild.name}: {', '.join(roles)}")
        
        response = "Deine Rollen:\n" + "\n".join(user_roles) if user_roles else "Du hast keine Rollen in gemeinsamen Servern."
        await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="status", description="Zeigt den Bot-Status")
async def status(interaction: discord.Interaction):
    """Zeigt den Status des Bots"""
    if isinstance(interaction.channel, discord.DMChannel):
        status = f"""
Bot Status:
- Name: {bot.user.name}
- ID: {bot.user.id}
- Server: {len(bot.guilds)}
- Ping: {round(bot.latency * 1000)}ms
- Uptime: {datetime.now() - bot.start_time}
"""
        await interaction.response.send_message(status, ephemeral=True)

@bot.tree.command(name="help", description="Zeigt diese Hilfe")
async def help(interaction: discord.Interaction):
    """Zeigt die Hilfe"""
    help_text = templates.get("help")
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.event
async def on_ready():
    global discord_client
    discord_client = bot
    bot.start_time = datetime.now()
    
    # Synchronisiere Slash-Commands
    await bot.tree.sync()
    
    logger.info(f"Logged in as {bot.user.name}")

@bot.event
async def on_message(message):
    """Handle incoming messages"""
    if message.author == bot.user:
        return

    try:
        # Handle DMs
        if isinstance(message.channel, discord.DMChannel):
            # Prüfe ob der Benutzer bereits begrüßt wurde
            if message.author.id not in welcomed_users:
                welcome_msg = templates.get("welcome",
                    user=message.author.mention,
                    bot_name=BOT_NAME,
                    orga_name=ORGA_NAME,
                    website=WEBSITE_URL,
                    discord_invite=DISCORD_INVITE
                )
                await message.channel.send(welcome_msg)
                welcomed_users.add(message.author.id)
        
        # Handle mentions in channels
        else:
            # Check for direct bot mention
            if bot.user in message.mentions:
                response = templates.get("bot_mention", user=message.author.mention)
                await message.channel.send(response)
                return

            # Check for role mentions
            mentioned_roles = set(role.id for role in message.role_mentions)
            bot_roles = set(role.id for role in message.guild.get_member(bot.user.id).roles)
            
            if mentioned_roles & bot_roles:
                # Finde die erste gemeinsame Rolle für die Erwähnung
                role_id = (mentioned_roles & bot_roles).pop()
                role = discord.utils.get(message.guild.roles, id=role_id)
                response = templates.get("role_mention",
                    user=message.author.mention,
                    role=role.mention if role else "unbekannt"
                )
                await message.channel.send(response)
                return
            
    except Exception as e:
        error_msg = templates.get("error", error=str(e))
        logger.error(f"Error handling message: {e}", exc_info=True)
        await message.channel.send(error_msg)

    await bot.process_commands(message)

# Continue processing commands
    await bot.process_commands(message)

# Helper function to ensure Discord client is ready
def require_discord_client(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not discord_client:
            raise RuntimeError("Discord client not ready")
        return await func(*args, **kwargs)
    return wrapper

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Discord tools."""
    tools = [
        # Server Information Tools
        Tool(
            name="get_server_info",
            description="Get information about a Discord server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="list_members",
            description="Get a list of members in a server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of members to fetch",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["server_id"]
            }
        ),

        # Role Management Tools
        Tool(
            name="add_role",
            description="Add a role to a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to add role to"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to add"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),
        Tool(
            name="remove_role",
            description="Remove a role from a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to remove role from"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to remove"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),

        # Channel Management Tools
        Tool(
            name="create_text_channel",
            description="Create a new text channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Channel name"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "Optional category ID to place channel in"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Optional channel topic"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),
        Tool(
            name="delete_channel",
            description="Delete a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "ID of channel to delete"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for deletion"
                    }
                },
                "required": ["channel_id"]
            }
        ),

        # Message Reaction Tools
        Tool(
            name="add_reaction",
            description="Add a reaction to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to react with (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="add_multiple_reactions",
            description="Add multiple reactions to a message",
            inputSchema={{
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emojis": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Emoji to react with (Unicode or custom emoji ID)"
                        },
                        "description": "List of emojis to add as reactions"
                    }
                },
                "required": ["channel_id", "message_id", "emojis"]
            }}
        ),
        Tool(
            name="remove_reaction",
            description="Remove a reaction from a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to remove reaction from"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to remove (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="send_message",
            description="Send a message to a specific channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    }
                },
                "required": ["channel_id", "content"]
            }
        ),
        Tool(
            name="read_messages",
            description="Read recent messages from a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of messages to fetch (max 100)",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["channel_id"]
            }
        ),
        Tool(
            name="get_user_info",
            description="Get information about a Discord user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID"
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="moderate_message",
            description="Delete a message and optionally timeout the user",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel ID containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "ID of message to moderate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for moderation"
                    },
                    "timeout_minutes": {
                        "type": "number",
                        "description": "Optional timeout duration in minutes",
                        "minimum": 0,
                        "maximum": 40320  # Max 4 weeks
                    }
                },
                "required": ["channel_id", "message_id", "reason"]
            }
        ),
        
        # User Role Tools
        Tool(
            name="get_user_roles",
            description="Get all roles of a user across all mutual servers",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID"
                    }
                },
                "required": ["user_id"]
            }
        ),
    ]
    return tools

@app.call_tool()
@require_discord_client
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle Discord tool calls."""
    
    if name == "send_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.send(arguments["content"])
        return [TextContent(
            type="text",
            text=f"Message sent successfully. Message ID: {message.id}"
        )]

    elif name == "read_messages":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        limit = min(int(arguments.get("limit", 10)), 100)
        messages = []
        async for message in channel.history(limit=limit):
            reaction_data = []
            for reaction in message.reactions:
                try:
                    emoji_str = (str(reaction.emoji.name) if hasattr(reaction.emoji, 'name') and reaction.emoji.name else str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else str(reaction.emoji))
                    reaction_data.append({"emoji": emoji_str, "count": reaction.count})
                except AttributeError as e:
                    logger.error(f"Error processing emoji: {e}")
                continue
            messages.append({
                "id": str(message.id),
                "author": str(message.author),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "reactions": reaction_data
            })

        formatted_messages = []
        for m in messages:
            reaction_text = "No reactions"
            if m['reactions']:
                reactions = [f"{r['emoji']}({r['count']})" for r in m['reactions']]
                reaction_text = ", ".join(reactions)
            
            message_text = (
                f"{m['author']} ({m['timestamp']}):\n"
                f"{m['content']}\n"
                f"Reactions: {reaction_text}"
            )
            formatted_messages.append(message_text)

        return [TextContent(
            type="text",
            text=f"Retrieved {len(messages)} messages:\n\n" + "\n\n".join(formatted_messages)
        )]

    elif name == "get_user_info":
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        user_info = {
            "id": str(user.id),
            "name": user.name,
            "discriminator": user.discriminator,
            "bot": user.bot,
            "created_at": user.created_at.isoformat()
        }
        return [TextContent(
            type="text",
            text=f"User information:\n" + f"Name: {user_info['name']}#{user_info['discriminator']}\n" + f"ID: {user_info['id']}\n" + f"Bot: {user_info['bot']}\n" + f"Created: {user_info['created_at']}"
        )]

    elif name == "moderate_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        
        # Delete the message
        await message.delete(reason=arguments["reason"])
        
        # Handle timeout if specified
        if "timeout_minutes" in arguments and arguments["timeout_minutes"] > 0:
            if isinstance(message.author, discord.Member):
                try:
                    duration = discord.utils.utcnow() + timedelta(
                        minutes=arguments["timeout_minutes"]
                    )
                    await message.author.timeout(
                        duration,
                        reason=arguments["reason"]
                    )
                    return [TextContent(
                    type="text",
                    text=f"Message deleted and user timed out for {arguments['timeout_minutes']} minutes."
                )]
                except discord.Forbidden:
                    return [TextContent(
                        type="text",
                        text="Message deleted but lacking permissions to timeout user."
                    )]
        
        return [TextContent(
            type="text",
            text="Message deleted successfully."
        )]

    # Server Information Tools
    elif name == "get_server_info":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        info = {
            "name": guild.name,
            "id": str(guild.id),
            "owner_id": str(guild.owner_id),
            "member_count": guild.member_count,
            "created_at": guild.created_at.isoformat(),
            "description": guild.description,
            "premium_tier": guild.premium_tier,
            "explicit_content_filter": str(guild.explicit_content_filter)
        }
        return [TextContent(
            type="text",
            text=f"Server Information:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())
        )]

    elif name == "list_members":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        limit = min(int(arguments.get("limit", 100)), 1000)
        
        members = []
        async for member in guild.fetch_members(limit=limit):
            members.append({
                "id": str(member.id),
                "name": member.name,
                "nick": member.nick,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "roles": [str(role.id) for role in member.roles[1:]]  # Skip @everyone
            })
        
        return [TextContent(
            type="text",
            text=f"Server Members ({len(members)}):\n" + "\n".join(f"{m['name']} (ID: {m['id']}, Roles: {', '.join(m['roles'])})" for m in members)
        )]

    # Role Management Tools
    elif name == "add_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        await member.add_roles(role, reason="Role added via MCP")
        return [TextContent(
            type="text",
            text=f"Added role {role.name} to user {member.name}"
        )]

    elif name == "remove_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        await member.remove_roles(role, reason="Role removed via MCP")
        return [TextContent(
            type="text",
            text=f"Removed role {role.name} from user {member.name}"
        )]

    # Channel Management Tools
    elif name == "create_text_channel":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        category = None
        if "category_id" in arguments:
            category = guild.get_channel(int(arguments["category_id"]))
        
        channel = await guild.create_text_channel(
            name=arguments["name"],
            category=category,
            topic=arguments.get("topic"),
            reason="Channel created via MCP"
        )
        
        return [TextContent(
            type="text",
            text=f"Created text channel #{channel.name} (ID: {channel.id})"
        )]

    elif name == "delete_channel":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        await channel.delete(reason=arguments.get("reason", "Channel deleted via MCP"))
        return [TextContent(
            type="text",
            text=f"Deleted channel successfully"
        )]

    # Message Reaction Tools
    elif name == "add_reaction":
        try:
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            message = await channel.fetch_message(int(arguments["message_id"]))
            await message.add_reaction(arguments["emoji"])
            return [TextContent(
                type="text",
                text=f"Added reaction {arguments['emoji']} to message"
            )]
        except discord.HTTPException as e:
            return [TextContent(
                type="text",
                text=f"Failed to add reaction: {str(e)}"
            )]

    elif name == "add_multiple_reactions":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        for emoji in arguments["emojis"]:
            await message.add_reaction(emoji)
        return [TextContent(
            type="text",
            text=f"Added reactions: {', '.join(arguments['emojis'])} to message"
        )]

    elif name == "remove_reaction":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.remove_reaction(arguments["emoji"], discord_client.user)
        return [TextContent(
            type="text",
            text=f"Removed reaction {arguments['emoji']} from message"
        )]

    elif name == "get_user_roles":
        user_roles = []
        user_id = int(arguments["user_id"])
        
        for guild in discord_client.guilds:
            member = guild.get_member(user_id)
            if member:
                roles = [
                    {
                        "server": guild.name,
                        "server_id": str(guild.id),
                        "role": role.name,
                        "role_id": str(role.id)
                    }
                    for role in member.roles 
                    if role.name != "@everyone"
                ]
                user_roles.extend(roles)
        
        return [TextContent(
            type="text",
            text=f"User Roles:\n" + "\n".join(
                f"Server {r['server']}: {r['role']} (ID: {r['role_id']})" 
                for r in user_roles
            )
        )]

    raise ValueError(f"Unknown tool: {name}")

class GracefulExitEvent:
    """Event für sauberes Beenden unter Windows"""
    def __init__(self):
        self._event = threading.Event()

    def set(self):
        self._event.set()

    async def wait(self):
        # Konvertiere Threading-Event in asyncio-Event
        while not self._event.is_set():
            await asyncio.sleep(0.1)
        return True

def win32_handler(ctrl_type):
    """Windows Console Control Handler"""
    if ctrl_type in (0, 2):  # CTRL_C_EVENT or CTRL_BREAK_EVENT
        logger.info("Shutdown signal received")
        EXIT_EVENT.set()
        return True
    return False

# Globales Exit-Event
EXIT_EVENT = GracefulExitEvent()

async def cleanup():
    """Cleanup function to properly close connections"""
    if discord_client:
        try:
            logger.info("Starting cleanup...")
            
            # Disconnect from Discord
            if not discord_client.is_closed():
                # Stoppe zuerst den Heartbeat falls vorhanden
                if hasattr(discord_client.ws, '_keep_alive'):
                    try:
                        discord_client.ws._keep_alive.stop()
                        await asyncio.sleep(0.5)
                    except:
                        pass
                
                try:
                    await discord_client.close()
                    logger.info("Discord client closed")
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error during Discord client cleanup: {e}", exc_info=True)

def handle_exit():
    """Handle synchronous cleanup on process termination"""
    logger.info("Process termination detected, running cleanup...")
    if discord_client and not discord_client.is_closed():
        try:
            if hasattr(discord_client.ws, '_keep_alive'):
                discord_client.ws._keep_alive.stop()
            loop = asyncio.new_event_loop()
            loop.run_until_complete(discord_client.close())
            loop.close()
        except:
            pass
    logger.info("Emergency cleanup complete")

async def main():
    """Main entry point with proper cleanup"""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable is not set")
        return 1
    
    # Registriere Windows Event Handler
    if sys.platform == 'win32':
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCtrlHandler(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)(win32_handler), True)
    
    # Registriere Notfall-Cleanup
    atexit.register(handle_exit)
    
    try:
        # Start Discord bot
        bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
        logger.info("Starting Discord bot...")
        
        # Wait for bot to be ready
        timeout = 30
        start_time = asyncio.get_event_loop().time()
        while not discord_client:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError("Discord bot failed to start within timeout period")
            await asyncio.sleep(0.1)
        
        logger.info("Bot is ready, starting MCP server...")
        
        try:    
            # Run MCP server
            async with stdio_server() as (read_stream, write_stream):
                server_task = asyncio.create_task(
                    app.run(
                        read_stream,
                        write_stream,
                        app.create_initialization_options()
                    )
                )
                
                # Warte auf Server-Task oder Exit-Event
                await asyncio.wait(
                    [server_task, EXIT_EVENT.wait()],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                logger.info("Starting shutdown sequence...")
                
        except Exception as e:
            logger.error(f"Error in server task: {e}", exc_info=True)
        finally:
            # Cleanup
            await cleanup()
            
            # Cancel remaining tasks
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)
        return 1
    finally:
        logger.info("Shutdown complete")
        
    return 0

if __name__ == "__main__":
    asyncio.run(main())
