from dataclasses import dataclass
from typing import Dict, Any, Optional, List

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
