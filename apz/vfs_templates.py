"""VFS TEMPLATES: Pre-konfigurierte forensische Umgebungen im VFS.

LLM, Python-Server, eSIM-Forensics, Analysis-Engines - alles im versteckten VFS!
"""
from __future__ import annotations

import os
import json
import time
import hashlib
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from . import ui
from .adb import ADB


class TemplateType(Enum):
    """VFS-Template Typen."""
    LLM = "llm"                    # Lokales 200MB LLM-Modell
    PYTHON_SERVER = "python_server"  # Flask REST API
    ESIM_FORENSICS = "esim"        # SIM-Daten Analyzer
    ANALYSIS_ENGINE = "analysis"   # CPU-intensive Analysis
    CACHE_DB = "cache_db"          # SQLite forensic DB
    REPORTING = "reporting"        # Report-Generator


@dataclass
class TemplateConfig:
    """VFS-Template Konfiguration."""
    template_type: TemplateType
    name: str
    description: str
    size_mb: int
    dependencies: List[str]
    startup_cmd: str
    api_port: int = 0
    files: Dict[str, str] = None  # filename: content

    def __post_init__(self):
        if self.files is None:
            self.files = {}


class VFSTemplateManager:
    """Manager für VFS-Templates."""

    def __init__(self, adb: ADB):
        self.adb = adb
        self.templates = self._load_templates()
        self.installed_templates: List[str] = []

    def show_template_menu(self) -> None:
        """Zeigt VFS-Template Menü."""
        while True:
            ui.clear()
            ui.banner(subtitle="📦 VFS TEMPLATES - Forensic Environments")
            print()

            ui.rule("🧬 EMBEDDED FORENSIC LABS", ui.BCYAN)
            print()
            print("  Komplett offline forensische Umgebungen!")
            print("  Im VFS versteckt, Kernel-geschützt")
            print()

            entries = [
                ("1", "🤖 LLM-Template (200MB, lokales KI-Modell)"),
                ("2", "🐍 Python-Server Template (Flask REST API)"),
                ("3", "📱 eSIM-Forensics Template (SIM-Daten)"),
                ("4", "⚙️  Analysis-Engine Template (CPU-intensiv)"),
                ("5", "💾 Cache-DB Template (SQLite Forensic DB)"),
                ("6", "📊 Reporting-Engine Template (PDF/Report Gen)"),
                ("7", "📋 Template-Details anzeigen"),
                ("8", "🚀 Alle Templates installieren"),
                ("9", "🗑️  Template löschen"),
            ]

            ch = ui.menu("Template-Optionen", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.install_template(TemplateType.LLM)
            elif ch == "2":
                self.install_template(TemplateType.PYTHON_SERVER)
            elif ch == "3":
                self.install_template(TemplateType.ESIM_FORENSICS)
            elif ch == "4":
                self.install_template(TemplateType.ANALYSIS_ENGINE)
            elif ch == "5":
                self.install_template(TemplateType.CACHE_DB)
            elif ch == "6":
                self.install_template(TemplateType.REPORTING)
            elif ch == "7":
                self.show_template_details()
            elif ch == "8":
                self.install_all_templates()
            elif ch == "9":
                self.uninstall_template()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def install_template(self, template_type: TemplateType) -> None:
        """Installiert ein Template im VFS."""
        ui.clear()

        # Finde Template
        template = next((t for t in self.templates if t.template_type == template_type), None)
        if not template:
            ui.err("Template nicht gefunden")
            ui.pause()
            return

        ui.rule(f"📦 INSTALLIERE: {template.name}", ui.BCYAN)
        print()

        print(f"  Template: {template.name}")
        print(f"  Beschreibung: {template.description}")
        print(f"  Größe: {template.size_mb}MB")
        print(f"  Dependencies: {', '.join(template.dependencies)}")
        print()

        if not ui.confirm("Im VFS installieren?", True):
            return

        try:
            # Erstelle VFS-Verzeichnis
            vfs_path = f"/forensic/vfs/templates/{template_type.value}"
            self.adb.shell(f"mkdir -p {vfs_path}")

            ui.rule("Installation läuft...", ui.BCYAN)

            # Installiere Template-Dateien
            progress = 0
            for filename, content in template.files.items():
                progress += 1
                ui.progress(progress, len(template.files), f"Installiere {filename}")

                file_path = f"{vfs_path}/{filename}"
                self.adb.push_string(content, file_path)

            # Startup-Script
            startup_path = f"{vfs_path}/startup.sh"
            self.adb.push_string(template.startup_cmd, startup_path)
            self.adb.shell(f"chmod +x {startup_path}")

            self.installed_templates.append(template_type.value)

            ui.ok(f"Template installiert: {vfs_path}")
            ui.kv("Status", "✓ Ready")
            ui.kv("Startup", template.startup_cmd)

        except Exception as e:
            ui.err(f"Installation Fehler: {e}")

        print()
        ui.pause()

    def install_all_templates(self) -> None:
        """Installiert ALLE Templates."""
        ui.clear()
        ui.rule("🚀 INSTALLIERE ALLE TEMPLATES", ui.BCYAN)
        print()

        if not ui.confirm("Alle 6 Templates installieren (~2GB)?", False):
            return

        for template in self.templates:
            self.install_template(template.template_type)

        ui.ok("Alle Templates installiert!")
        ui.pause()

    def show_template_details(self) -> None:
        """Zeigt Template-Details."""
        ui.clear()
        ui.rule("📋 TEMPLATE DETAILS", ui.BCYAN)
        print()

        for template in self.templates:
            status = "✓ Installiert" if template.template_type.value in self.installed_templates else "✗ Nicht installiert"
            print(f"  {status}  {template.name}")
            print(f"    Size: {template.size_mb}MB")
            print(f"    Desc: {template.description}")
            if template.api_port:
                print(f"    Port: {template.api_port}")
            print()

        ui.pause()

    def uninstall_template(self) -> None:
        """Deinstalliert ein Template."""
        ui.clear()
        ui.rule("🗑️  TEMPLATE LÖSCHEN", ui.BCYAN)
        print()

        if not self.installed_templates:
            ui.warn("Keine Templates installiert")
            ui.pause()
            return

        print("  Installierte Templates:")
        for i, t in enumerate(self.installed_templates, 1):
            print(f"    {i}. {t}")

        choice = ui.ask("Zu löschend (Nummer)", "1")

        try:
            idx = int(choice) - 1
            template_name = self.installed_templates[idx]

            if ui.confirm(f"Wirklich {template_name} löschen?", False):
                vfs_path = f"/forensic/vfs/templates/{template_name}"
                self.adb.shell(f"rm -rf {vfs_path}")
                self.installed_templates.pop(idx)

                ui.ok("Template gelöscht")

        except Exception as e:
            ui.err(f"Lösch-Fehler: {e}")

        print()
        ui.pause()

    def _load_templates(self) -> List[TemplateConfig]:
        """Lädt alle vordefinierten Templates."""
        return [
            self._template_llm(),
            self._template_python_server(),
            self._template_esim(),
            self._template_analysis(),
            self._template_cache_db(),
            self._template_reporting(),
        ]

    def _template_llm(self) -> TemplateConfig:
        """200MB lokales LLM-Modell."""
        return TemplateConfig(
            template_type=TemplateType.LLM,
            name="LLM-Template (Ollama)",
            description="Lokales 200MB quantisiertes LLM-Modell für offline Analysis",
            size_mb=250,
            dependencies=["ollama", "llama.cpp"],
            startup_cmd="ollama serve --addr 127.0.0.1:11434 &",
            api_port=11434,
            files={
                "ollama_model.gguf": self._generate_llm_model(),
                "modelfile": """FROM ./ollama_model.gguf
PARAMETER temperature 0.1
PARAMETER num_ctx 512
SYSTEM You are a forensic AI analyst. Analyze the provided data and give concise findings.""",
                "analyze.py": """#!/usr/bin/env python3
import requests
import json

def analyze_with_llm(data: str, prompt_type: str = "general"):
    response = requests.post(
        'http://127.0.0.1:11434/api/generate',
        json={
            'model': 'forensic-analyst',
            'prompt': f'Analyze this forensic data:\\n{data}',
            'stream': False
        }
    )
    return response.json()['response']

if __name__ == '__main__':
    # Example usage
    test_data = "Browser history: pornhub.com, xxxvideos.com"
    result = analyze_with_llm(test_data)
    print(result)
""",
                "config.json": json.dumps({
                    "model": "forensic-analyst",
                    "memory_limit_mb": 200,
                    "max_context": 512,
                    "temperature": 0.1,
                    "analysis_types": ["forensic", "pattern", "anomaly"]
                }, indent=2),
            }
        )

    def _template_python_server(self) -> TemplateConfig:
        """Flask REST API Server."""
        return TemplateConfig(
            template_type=TemplateType.PYTHON_SERVER,
            name="Python-Server Template (Flask)",
            description="Lokaler Flask REST API Server für forensische Analysis-Operationen",
            size_mb=50,
            dependencies=["python3", "flask"],
            startup_cmd="python3 /forensic/vfs/templates/python_server/server.py",
            api_port=5000,
            files={
                "server.py": """#!/usr/bin/env python3
from flask import Flask, request, jsonify
import json
import time

app = Flask(__name__)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    return jsonify({
        'status': 'success',
        'analysis': {
            'type': data.get('type'),
            'findings': [],
            'timestamp': time.time()
        }
    })

@app.route('/api/report/generate', methods=['POST'])
def generate_report():
    return jsonify({
        'report_id': 'report_' + str(int(time.time())),
        'status': 'generated',
        'url': '/reports/latest'
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'forensic-analyzer'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
""",
                "requirements.txt": """flask==2.3.0
requests==2.31.0
""",
                "api_docs.json": json.dumps({
                    "endpoints": [
                        {"method": "POST", "path": "/api/analyze", "description": "Analyze forensic data"},
                        {"method": "POST", "path": "/api/report/generate", "description": "Generate analysis report"},
                        {"method": "GET", "path": "/api/health", "description": "Health check"}
                    ]
                }, indent=2),
            }
        )

    def _template_esim(self) -> TemplateConfig:
        """eSIM Forensics Template."""
        return TemplateConfig(
            template_type=TemplateType.ESIM_FORENSICS,
            name="eSIM-Forensics Template",
            description="SIM-Kartendaten, Operator-Datenbank, IMSI-Lookup, Roaming-Analyse",
            size_mb=100,
            dependencies=["pysim", "sqlite3"],
            startup_cmd="python3 /forensic/vfs/templates/esim/esim_analyzer.py",
            files={
                "esim_analyzer.py": """#!/usr/bin/env python3
import json
import sqlite3
from dataclasses import dataclass

@dataclass
class SIMCard:
    imsi: str
    iccid: str
    mcc: str
    mnc: str
    operator: str
    country: str

OPERATOR_DB = {
    "31000": {"operator": "T-Mobile Netherlands", "country": "NL"},
    "31002": {"operator": "Vodafone Netherlands", "country": "NL"},
    "31004": {"operator": "KPN Netherlands", "country": "NL"},
    "31010": {"operator": "Centric Netherlands", "country": "NL"},
}

def analyze_imsi(imsi: str) -> dict:
    mcc = imsi[:3]
    mnc = imsi[3:5]
    key = mcc + mnc

    if key in OPERATOR_DB:
        return {
            'imsi': imsi,
            'mcc': mcc,
            'mnc': mnc,
            'operator': OPERATOR_DB[key]['operator'],
            'country': OPERATOR_DB[key]['country']
        }
    return {'imsi': imsi, 'mcc': mcc, 'mnc': mnc, 'operator': 'Unknown'}

if __name__ == '__main__':
    # Example
    result = analyze_imsi("310410123456789")
    print(json.dumps(result, indent=2))
""",
                "operator_db.json": json.dumps({
                    "operators": {
                        "31000": {"name": "T-Mobile NL", "country": "NL"},
                        "31002": {"name": "Vodafone NL", "country": "NL"},
                        "310410": {"name": "AT&T USA", "country": "US"},
                        "440020": {"name": "NTT DoCoMo JP", "country": "JP"},
                    }
                }, indent=2),
            }
        )

    def _template_analysis(self) -> TemplateConfig:
        """Analysis-Engine Template."""
        return TemplateConfig(
            template_type=TemplateType.ANALYSIS_ENGINE,
            name="Analysis-Engine Template",
            description="CPU-intensive Verarbeitung: Pattern-Matching, Correlation, Batch-Processing",
            size_mb=150,
            dependencies=["python3", "pandas", "numpy"],
            startup_cmd="python3 /forensic/vfs/templates/analysis/engine.py",
            files={
                "engine.py": """#!/usr/bin/env python3
import json
import time
from typing import List, Dict

class AnalysisEngine:
    def __init__(self):
        self.patterns = []
        self.correlations = []

    def analyze_patterns(self, data: List[str]) -> Dict:
        matches = []
        for item in data:
            # Pattern matching logic
            if any(keyword in item.lower() for keyword in ['porn', 'xxx', 'sex']):
                matches.append(item)
        return {'type': 'pattern_analysis', 'matches': len(matches)}

    def correlate_events(self, events: List[Dict]) -> Dict:
        # Correlation logic
        return {'type': 'correlation_analysis', 'events': len(events)}

    def batch_process(self, items: List) -> Dict:
        start = time.time()
        results = []
        for item in items:
            results.append(self.analyze_patterns([item]))
        return {
            'type': 'batch_processing',
            'items': len(items),
            'duration_ms': int((time.time() - start) * 1000)
        }

if __name__ == '__main__':
    engine = AnalysisEngine()
    result = engine.batch_process(['test1', 'test2', 'pornhub.com'])
    print(json.dumps(result, indent=2))
""",
            }
        )

    def _template_cache_db(self) -> TemplateConfig:
        """Cache-DB Template."""
        return TemplateConfig(
            template_type=TemplateType.CACHE_DB,
            name="Cache-DB Template (SQLite)",
            description="SQLite Forensic-Datenbank mit pre-indexierten Daten für schnelle Lookups",
            size_mb=80,
            dependencies=["sqlite3"],
            startup_cmd="sqlite3 /forensic/vfs/templates/cache_db/forensic.db '.databases'",
            files={
                "init_db.sql": """
CREATE TABLE IF NOT EXISTS adult_keywords (
    id INTEGER PRIMARY KEY,
    keyword TEXT UNIQUE,
    category TEXT,
    severity INTEGER
);

CREATE TABLE IF NOT EXISTS adult_domains (
    id INTEGER PRIMARY KEY,
    domain TEXT UNIQUE,
    category TEXT,
    last_seen TEXT
);

CREATE INDEX idx_keywords ON adult_keywords(keyword);
CREATE INDEX idx_domains ON adult_domains(domain);

INSERT OR IGNORE INTO adult_keywords VALUES
(1, 'pornhub', 'adult', 10),
(2, 'xvideos', 'adult', 10),
(3, 'sex', 'adult', 5);

INSERT OR IGNORE INTO adult_domains VALUES
(1, 'pornhub.com', 'adult', datetime('now')),
(2, 'xvideos.com', 'adult', datetime('now'));
""",
            }
        )

    def _template_reporting(self) -> TemplateConfig:
        """Reporting-Engine Template."""
        return TemplateConfig(
            template_type=TemplateType.REPORTING,
            name="Reporting-Engine Template",
            description="Report-Generator: PDF, JSON, TXT mit Charts und Statistiken",
            size_mb=120,
            dependencies=["reportlab", "jinja2"],
            startup_cmd="python3 /forensic/vfs/templates/reporting/reporter.py",
            files={
                "reporter.py": """#!/usr/bin/env python3
import json
from datetime import datetime

class ReportGenerator:
    def generate_json(self, data: dict) -> str:
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis': data,
            'summary': {
                'total_findings': len(data.get('findings', [])),
                'severity_breakdown': self._calculate_severity(data)
            }
        }
        return json.dumps(report, indent=2)

    def generate_txt(self, data: dict) -> str:
        lines = [
            '=== FORENSIC ANALYSIS REPORT ===',
            f'Generated: {datetime.now()}',
            '',
            'FINDINGS:',
        ]
        for finding in data.get('findings', []):
            lines.append(f'  - {finding}')
        return '\\n'.join(lines)

    def _calculate_severity(self, data: dict) -> dict:
        return {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

if __name__ == '__main__':
    gen = ReportGenerator()
    test_data = {'findings': ['finding1', 'finding2']}
    print(gen.generate_json(test_data))
""",
            }
        )

    def _generate_llm_model(self) -> str:
        """Placeholder für LLM-Modell."""
        return "# Quantized LLM Model (GGUF Format)\n# Size: ~200MB\n# This would be the actual model binary"


def create_vfs_template_manager(adb: ADB) -> VFSTemplateManager:
    """Erstellt neuen VFS-Template Manager."""
    return VFSTemplateManager(adb)
