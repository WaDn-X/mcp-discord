# WaDn ~ Discord MCP-Server

[![smithery badge](https://smithery.ai/badge/@CeeJay79)](https://smithery.ai/server/@CeeJay79)
Ein Model Context Protocol (MCP) Server für Discord-Integration, der es ermöglicht, Discord-Funktionen über eine standardisierte Schnittstelle zu nutzen.

## Schnellstart

1. **Environment vorbereiten:**
   ```bash
   # Virtuelle Umgebung erstellen und aktivieren
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

2. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Bot starten:**
   ```bash
   # Direkt aus dem Projektverzeichnis
   python -m discord_mcp
   ```

## Features

### Server-Information
- `get_server_info`: Hole detaillierte Server-Informationen
- `list_members`: Liste Server-Mitglieder und ihre Rollen auf

### Nachrichten-Management
- `send_message`: Sende Nachrichten in einen Kanal
- `read_messages`: Lese kürzliche Nachrichten (mit Limit)
- `moderate_message`: Lösche Nachrichten und optional Timeout für Nutzer

### Reaktionen
- `add_reaction`: Füge eine Reaktion zu einer Nachricht hinzu
- `add_multiple_reactions`: Füge mehrere Reaktionen gleichzeitig hinzu
- `remove_reaction`: Entferne eine Reaktion von einer Nachricht

### Kanal-Management
- `create_text_channel`: Erstelle einen neuen Textkanal
- `delete_channel`: Lösche einen existierenden Kanal

### Rollen-Management
- `add_role`: Füge einem Nutzer eine Rolle hinzu
- `remove_role`: Entferne eine Rolle von einem Nutzer

### Webhook Management
- `create_webhook`: Create a new webhook
- `list_webhooks`: List webhooks in a channel
- `send_webhook_message`: Send messages via webhook
- `modify_webhook`: Update webhook settings
- `delete_webhook`: Delete a webhook

## Prerequisites

1. **Set up your Discord bot**:
   - Create a new application at [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a bot and copy the token
   - Enable required privileged intents:
     - MESSAGE CONTENT INTENT
     - PRESENCE INTENT
     - SERVER MEMBERS INTENT
   - Invite the bot to your server using OAuth2 URL Generator

2. **Python Requirements**:
   - Python 3.8 or higher
   - pip (Python package installer)

## Installation

1. **Repository klonen:**
   ```bash
   git clone https://github.com/yourusername/mcp-discord.git
   cd mcp-discord
   ```

2. **Virtuelle Umgebung erstellen:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/macOS
   python -m venv venv
   source venv/bin/activate
   ```

3. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Configure Claude Desktop**:

Add this to your claude_desktop_config.json:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "discord": {
      "command": "python",
      "args": ["-m", "mcp_discord"],
      "cwd": "path/to/mcp-discord",
      "env": {
        "DISCORD_TOKEN": "your_bot_token"
      }
    }
  }
}
```
Note: 
- Replace "path/to/mcp-discord" with the actual path to your cloned repository
- Replace "your_bot_token" with your Discord bot token

## Debugging

If you run into issues, check Claude Desktop's MCP logs:
```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
```

Common issues:
1. **Token Errors**:
   - Verify your Discord bot token is correct
   - Check that all required intents are enabled

2. **Permission Issues**:
   - Ensure the bot has proper permissions in your Discord server
   - Verify the bot's role hierarchy for role management commands

3. **Installation Issues**:
   - Make sure you're using the correct Python version
   - Try recreating the virtual environment
   - Check that all dependencies are installed correctly

## Beispiele

### Nachricht senden:
```json
{
  "type": "call_tool",
  "tool": "send_message",
  "arguments": {
    "channel_id": "123456789",
    "content": "Hallo Welt!"
  }
}
```

### Nachrichten lesen:
```json
{
  "type": "call_tool",
  "tool": "read_messages",
  "arguments": {
    "channel_id": "123456789",
    "limit": 10
  }
}
```

### Reaktion hinzufügen:
```json
{
  "type": "call_tool",
  "tool": "add_reaction",
  "arguments": {
    "channel_id": "123456789",
    "message_id": "987654321",
    "emoji": "👍"
  }
}
```

## Fehlerbehandlung

Häufige Fehler und Lösungen:

1. **"Discord client not ready"**
   - Warte, bis der Bot vollständig gestartet ist
   - Überprüfe die Bot-Token-Konfiguration

2. **"Channel not found"**
   - Stelle sicher, dass der Bot Zugriff auf den Kanal hat
   - Überprüfe die Channel-ID

3. **"Missing permissions"**
   - Überprüfe die Bot-Berechtigungen im Server
   - Stelle sicher, dass die Bot-Rolle ausreichende Rechte hat

## Logging

Der Server protokolliert detaillierte Informationen:
- Bot-Start und -Status
- Empfangene Befehle
- Fehler und Warnungen

Logs findest du in der Konsolenausgabe oder in den konfigurierten Log-Dateien.

## License

MIT License - siehe LICENSE für Details.

---
Note: This is a fork of the [original mcp-discord repository](https://github.com/hanweg/mcp-discord).

<a href="https://glama.ai/mcp/servers/wvwjgcnppa"><img width="380" height="200" src="https://glama.ai/mcp/servers/wvwjgcnppa/badge" alt="mcp-discord MCP server" /></a>