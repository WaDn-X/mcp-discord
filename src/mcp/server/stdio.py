import asyncio
import sys
from contextlib import asynccontextmanager

async def _read_from_stream(stream):
    """Liest asynchron aus einem beliebigen Stream"""
    if hasattr(stream, 'readline'):
        return await stream.readline()
    elif hasattr(stream, 'receive'):
        try:
            return await stream.receive()
        except Exception:
            return b''
    return b''

async def _write_to_stream(stream, data):
    """Schreibt asynchron in einen beliebigen Stream"""
    if hasattr(stream, 'write'):
        stream.write(data)
        await stream.drain()
    elif hasattr(stream, 'send'):
        await stream.send(data)

class StreamAdapter:
    """Universal Stream Adapter"""
    def __init__(self, stream):
        self._stream = stream
        self._buffer = bytearray()

    async def readline(self):
        """Liest eine Zeile aus dem Stream"""
        data = await _read_from_stream(self._stream)
        if not data:
            return b''
        self._buffer.extend(data)
        
        if b'\n' in self._buffer:
            idx = self._buffer.index(b'\n') + 1
            line = bytes(self._buffer[:idx])
            del self._buffer[:idx]
            return line
        return data

    async def write(self, data):
        """Schreibt Daten in den Stream"""
        await _write_to_stream(self._stream, data)

    async def drain(self):
        """Wartet bis alle Daten geschrieben sind"""
        if hasattr(self._stream, 'drain'):
            await self._stream.drain()

    def close(self):
        """Schließt den Stream"""
        if hasattr(self._stream, 'close'):
            self._stream.close()

    async def wait_closed(self):
        """Wartet auf das Schließen des Streams"""
        if hasattr(self._stream, 'wait_closed'):
            await self._stream.wait_closed()

@asynccontextmanager
async def stdio_server():
    """Stream-Handler für verschiedene Stream-Typen"""
    try:
        # Verwende direkte Streams für stdin/stdout
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        
        if sys.platform == 'win32':
            await loop.connect_read_pipe(lambda: protocol, sys.stdin.buffer)
        else:
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        # Wrapper für ein- und ausgehende Streams
        read_adapter = StreamAdapter(reader)
        write_adapter = StreamAdapter(sys.stdout.buffer if sys.platform == 'win32' else sys.stdout)
        
        yield read_adapter, write_adapter
    except Exception as e:
        print(f"Error setting up stdio server: {e}", file=sys.stderr)
        raise
