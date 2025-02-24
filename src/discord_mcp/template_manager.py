import os
from pathlib import Path
from typing import Dict, Any

class TemplateManager:
    def __init__(self):
        self.templates: Dict[str, str] = {}
        self.template_dir = Path(__file__).parent.parent.parent / "templates" / "messages"
        self.load_templates()

    def load_templates(self) -> None:
        """Lädt alle Template-Dateien aus dem templates/messages Verzeichnis"""
        if not self.template_dir.exists():
            raise FileNotFoundError(
                f"Template-Verzeichnis nicht gefunden: {self.template_dir}\n"
                "Bitte stelle sicher, dass die .md Template-Dateien existieren."
            )

        # Lade alle .md Templates
        for template_file in self.template_dir.glob("*.md"):
            template_name = template_file.stem
            self.templates[template_name] = template_file.read_text(encoding='utf-8').strip()

    def get(self, key: str, **kwargs) -> str:
        """Hole und formatiere ein Template"""
        if key not in self.templates:
            raise KeyError(f"Template nicht gefunden: {key}")
            
        template = self.templates[key]
        return template.format(**kwargs)

# Globale Template-Instanz
templates = TemplateManager()
