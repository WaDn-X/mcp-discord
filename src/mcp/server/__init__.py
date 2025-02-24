from typing import Any, List, Optional
from dataclasses import dataclass

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
        while True:
            try:
                data = await read_stream.readline()
                if not data:
                    break
                # Hier würde die eigentliche Verarbeitung stattfinden
                await write_stream.write(b"ok\n")
            except Exception as e:
                print(f"Error: {e}")
                break
