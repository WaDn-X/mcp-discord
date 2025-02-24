"""WaDn ~ Discord MCP Server Package"""
import asyncio
import warnings
import tracemalloc
import signal
import sys
import logging
from . import server

__version__ = "0.1.13"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("discord-mcp")

def main():
    """Main entry point for the package."""
    # Enable tracemalloc for better debugging
    tracemalloc.start()
    
    # Suppress PyNaCl warning since we don't use voice features
    warnings.filterwarnings('ignore', module='discord.client', message='PyNaCl is not installed')
    
    try:
        # Windows-kompatibles Signal-Handling
        if sys.platform == 'win32':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                return loop.run_until_complete(server.main())
            except Exception as e:
                logger.error(f"Error in event loop: {e}", exc_info=True)
                return 1
            finally:
                loop.close()
        else:
            # Unix-Systeme können asyncio.run() direkt verwenden
            return asyncio.run(server.main())
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested via keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

# Expose important items at package level
__all__ = ['main', 'server']
