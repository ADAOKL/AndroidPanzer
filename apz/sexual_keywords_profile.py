"""SEXUAL ACTIVITY KEYWORDS: ULTRA-UMFASSENDES Profil für Geschlechtsverkehr-Erkennung!

ALLES DRIN: 140+ Keywords - Männlich/Weiblich, Laut/Leise, alle Geräusche!
Maximale Keywords für Detektion von sexuellen Aktivitäten basierend auf Audio-Patterns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from enum import Enum
from apz.comprehensive_sexual_keywords import ComprehensiveSexualKeywords


class SexualActivityType(Enum):
    """Sexuelle Aktivitäts-Typen."""
    MALE_VOCALIZATION = "Männliche Lautäußerungen"
    FEMALE_VOCALIZATION = "Weibliche Lautäußerungen"
    RHYTHM_PATTERNS = "Rhythmus-Muster"
    FURNITURE_SOUNDS = "Möbel-Geräusche"
    BREATHING_PATTERNS = "Atemzug-Muster"
    IMPACT_SOUNDS = "Schlag-Geräusche"
    PLEASURE_INDICATORS = "Lustanzeichen"
    CLIMAX_INDICATORS = "Orgasmus-Anzeichen"
    LUBRICANT_SOUNDS = "Schmier-Geräusche"
    MOVEMENT_PATTERNS = "Bewegungs-Muster"


@dataclass
class SexualKeyword:
    """Ein Sexual-Aktivitäts-Keyword."""
    keyword: str
    activity_type: SexualActivityType
    confidence_threshold: float = 0.75
    priority: int = 8
    frequency_range: str = ""  # z.B. "50-500 Hz"
    duration_ms: int = 0  # Dauer in Millisekunden
    aliases: List[str] = field(default_factory=list)
    context: str = ""


class SexualKeywordsLibrary:
    """Umfassende Sammlung von Sexual-Activity Keywords."""

    KEYWORDS: List[SexualKeyword] = [
        # ═══════════════════════════════════════════════════════════════════
        # MÄNNLICHE LAUTÄUSSERUNGEN (14 Keywords)
        # ═══════════════════════════════════════════════════════════════════

        SexualKeyword(
            keyword="Stöhnen männlich",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-300 Hz",
            priority=9,
            aliases=["male moaning", "male groan", "Stöhngeräusch"],
            context="Tiefe, rhythmische Lautäußerung"
        ),

        SexualKeyword(
            keyword="Ächzen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-400 Hz",
            priority=9,
            aliases=["Aechzen", "panting", "gasping"],
            context="Kurzatmige Lautäußerung"
        ),

        SexualKeyword(
            keyword="Keuchern",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="150-500 Hz",
            priority=8,
            aliases=["panting heavily", "Keuch-Laut"],
        ),

        SexualKeyword(
            keyword="Lustschrei männlich",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="200-800 Hz",
            priority=9,
            aliases=["male cry", "Schrei", "Orgasmus-Schrei"],
            context="Lauter, höher werdender Schrei"
        ),

        SexualKeyword(
            keyword="Grunzen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-200 Hz",
            priority=7,
            aliases=["grunting", "Grunt-Laut"],
            context="Tiefe, angestrengte Laute"
        ),

        SexualKeyword(
            keyword="Verzehrte Laute",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-600 Hz",
            priority=8,
            aliases=["distorted vocals", "verzerrte Laute"],
        ),

        SexualKeyword(
            keyword="Atemgeräusch (schwer)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="200-2000 Hz",
            priority=7,
            aliases=["heavy breathing male", "Atemzug"],
            context="Schnelles, tiefes Atmen"
        ),

        SexualKeyword(
            keyword="Knurren",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-150 Hz",
            priority=6,
            aliases=["growling", "Knurr-Laut"],
        ),

        SexualKeyword(
            keyword="Aggressive Laute",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="150-800 Hz",
            priority=7,
            aliases=["aggressive vocals", "aggressives Stöhnen"],
        ),

        SexualKeyword(
            keyword="Rhythmisches Ächzen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-400 Hz",
            priority=8,
            aliases=["rhythmic panting", "Rhythmus-Stöhnen"],
            context="Mit Bewegung synchronisiert"
        ),

        SexualKeyword(
            keyword="Lustvolle Ausrufe",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="200-600 Hz",
            priority=8,
            aliases=["passionate exclamations", "Lustaufruf"],
        ),

        SexualKeyword(
            keyword="Unkontrollierte Laute",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-800 Hz",
            priority=7,
            aliases=["uncontrolled sounds", "wilde Laute"],
            context="Beim Höhepunkt"
        ),

        SexualKeyword(
            keyword="Tiefe Resonanz",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="50-150 Hz",
            priority=6,
            aliases=["deep resonance", "tiefe Vibration"],
        ),

        SexualKeyword(
            keyword="Ekstatische Laute",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="150-700 Hz",
            priority=9,
            aliases=["ecstatic sounds", "ekstatisches Stöhnen"],
            context="Beim Orgasmus"
        ),

        # ═══════════════════════════════════════════════════════════════════
        # WEIBLICHE LAUTÄUSSERUNGEN (15 Keywords)
        # ═══════════════════════════════════════════════════════════════════

        SexualKeyword(
            keyword="Stöhnen weiblich",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="150-800 Hz",
            priority=9,
            aliases=["female moaning", "weibliches Stöhnen", "Stöhn-Laut"],
            context="Hohe, melodische Lautäußerung"
        ),

        SexualKeyword(
            keyword="Lustschrei",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-2000 Hz",
            priority=9,
            aliases=["pleasure cry", "orgasm cry", "Lust-Schrei"],
            context="Lauter, höher werdend"
        ),

        SexualKeyword(
            keyword="Atemzug weiblich",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-3000 Hz",
            priority=8,
            aliases=["female panting", "weibliches Atmen"],
            context="Schnelles, tiefes Atmen"
        ),

        SexualKeyword(
            keyword="Lustvolle Laute",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-1000 Hz",
            priority=8,
            aliases=["pleasurable sounds", "Lust-Laute"],
        ),

        SexualKeyword(
            keyword="Seufzer",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="150-600 Hz",
            priority=7,
            aliases=["sighing", "Seufzer-Laut"],
            context="Zufrieden, entspannt"
        ),

        SexualKeyword(
            keyword="Rhythmisches Ächzen",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-800 Hz",
            priority=8,
            aliases=["rhythmic moaning", "Rhythmus-Stöhnen"],
            context="Mit Bewegung synchronisiert"
        ),

        SexualKeyword(
            keyword="Intensive Laute",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1500 Hz",
            priority=8,
            aliases=["intense sounds", "intensive Laute"],
        ),

        SexualKeyword(
            keyword="Sprechende Laute",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-2000 Hz",
            priority=6,
            aliases=["vocal expressions", "sprechende Ausrufe"],
        ),

        SexualKeyword(
            keyword="Ekstatisches Stöhnen",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-2000 Hz",
            priority=9,
            aliases=["ecstatic moaning", "ekstatische Laute"],
            context="Beim Orgasmus"
        ),

        SexualKeyword(
            keyword="Flüsternde Laute",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="500-3000 Hz",
            priority=5,
            aliases=["whispered sounds", "flüsternde Ausrufe"],
        ),

        SexualKeyword(
            keyword="Erregte Atemzüge",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="400-3000 Hz",
            priority=8,
            aliases=["excited panting", "erregte Atemzüge"],
        ),

        SexualKeyword(
            keyword="Lustvolle Seufzer",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-800 Hz",
            priority=8,
            aliases=["pleasure sighs", "Lust-Seufzer"],
        ),

        SexualKeyword(
            keyword="Quieken",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="800-3000 Hz",
            priority=7,
            aliases=["squealing", "squeaking", "Quiek-Laut"],
            context="Hohe Frequenz, intensive Bewegung"
        ),

        SexualKeyword(
            keyword="Wiederholte Ausrufe",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1500 Hz",
            priority=8,
            aliases=["repeated exclamations", "wiederholte Laute"],
            context="Ja, Ja, Ja... Muster"
        ),

        SexualKeyword(
            keyword="Unkontrolliertes Stöhnen",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-2000 Hz",
            priority=8,
            aliases=["uncontrolled moaning", "unkontrolliertes Stöhnen"],
            context="Beim Höhepunkt"
        ),

        # ═══════════════════════════════════════════════════════════════════
        # RHYTHMUS-MUSTER (12 Keywords)
        # ═══════════════════════════════════════════════════════════════════

        SexualKeyword(
            keyword="Stoßrhythmus",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="10-50 Hz",
            priority=9,
            aliases=["thrusting rhythm", "Stoß-Rhythmus", "Impact-Rhythmus"],
            context="Regelmäßige, sich beschleunigende Muster"
        ),

        SexualKeyword(
            keyword="Beschleunigte Rhythmen",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-100 Hz",
            priority=9,
            aliases=["accelerating rhythm", "schneller werdend"],
            context="Tempo nimmt zu zum Höhepunkt"
        ),

        SexualKeyword(
            keyword="Gleichmäßige Stoße",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="15-60 Hz",
            priority=8,
            aliases=["steady thrusts", "gleichmäßige Stoße"],
            context="Konstantes Tempo"
        ),

        SexualKeyword(
            keyword="Puls-ähnliche Muster",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-100 Hz",
            priority=7,
            aliases=["pulse-like patterns", "Puls-Muster"],
        ),

        SexualKeyword(
            keyword="Polyrhythmische Bewegung",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="10-200 Hz",
            priority=6,
            aliases=["polyrhythmic movement", "komplexe Rhythmen"],
        ),

        SexualKeyword(
            keyword="Intensive Stöße",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="30-150 Hz",
            priority=9,
            aliases=["intense thrusting", "intensive Stoße"],
            context="Schnell und kräftig"
        ),

        SexualKeyword(
            keyword="Kreisende Bewegungen",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="5-30 Hz",
            priority=6,
            aliases=["circular movements", "kreisende Bewegungen"],
        ),

        SexualKeyword(
            keyword="Schnelle Wiederholungen",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="50-200 Hz",
            priority=8,
            aliases=["rapid repetitions", "schnelle Wiederholungen"],
        ),

        SexualKeyword(
            keyword="Wellenförmige Muster",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="5-50 Hz",
            priority=5,
            aliases=["wave-like patterns", "Wellen-Muster"],
        ),

        SexualKeyword(
            keyword="Tiefe Stöße",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="10-40 Hz",
            priority=8,
            aliases=["deep thrusts", "tiefe Stoße"],
        ),

        SexualKeyword(
            keyword="Unkontrollierte Bewegungen",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-200 Hz",
            priority=7,
            aliases=["uncontrolled movements", "chaotische Rhythmen"],
            context="Beim Orgasmus"
        ),

        SexualKeyword(
            keyword="Finale Stöße",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="50-150 Hz",
            priority=9,
            aliases=["final thrusts", "finale Stoße"],
            context="Zum Höhepunkt hin"
        ),

        # ═══════════════════════════════════════════════════════════════════
        # MÖBEL & STRUKTUR-GERÄUSCHE (10 Keywords)
        # ═══════════════════════════════════════════════════════════════════

        SexualKeyword(
            keyword="Bett quietscht",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="100-500 Hz",
            priority=8,
            aliases=["squeaking bed", "bed squeaks", "Bett-Quietschen"],
            context="Matratze und Gestell"
        ),

        SexualKeyword(
            keyword="Federkern-Geräusche",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="50-300 Hz",
            priority=7,
            aliases=["spring sounds", "Feder-Geräusche"],
        ),

        SexualKeyword(
            keyword="Matratzen-Bewegungen",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="20-200 Hz",
            priority=8,
            aliases=["mattress movements", "Matratzen-Bewegung"],
        ),

        SexualKeyword(
            keyword="Knarrendes Holz",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="100-400 Hz",
            priority=6,
            aliases=["creaking wood", "Holz-Knarren"],
        ),

        SexualKeyword(
            keyword="Bettrahmen-Geräusche",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="50-300 Hz",
            priority=7,
            aliases=["frame sounds", "Rahmen-Geräusche"],
        ),

        SexualKeyword(
            keyword="Kissen-Rascheln",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="200-3000 Hz",
            priority=5,
            aliases=["pillow rustling", "Kissen-Geräusche"],
        ),

        SexualKeyword(
            keyword="Laken-Geräusche",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="500-5000 Hz",
            priority=4,
            aliases=["sheet sounds", "Laken-Rascheln"],
        ),

        SexualKeyword(
            keyword="Möbel-Kratzer",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="200-2000 Hz",
            priority=5,
            aliases=["furniture scraping", "Kratzer-Geräusche"],
        ),

        SexualKeyword(
            keyword="Wandklopfen",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="100-500 Hz",
            priority=7,
            aliases=["wall knocking", "Wand-Klopfen"],
            context="Wenn Bett gegen Wand schlägt"
        ),

        SexualKeyword(
            keyword="Metallische Geräusche",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="300-2000 Hz",
            priority=6,
            aliases=["metallic sounds", "Metal-Geräusche"],
            context="Bei Metallbetten"
        ),

        # ═══════════════════════════════════════════════════════════════════
        # SCHMIER-GERÄUSCHE & FEUCHTE (6 Keywords)
        # ═══════════════════════════════════════════════════════════════════

        SexualKeyword(
            keyword="Schmiergeräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="500-3000 Hz",
            priority=8,
            aliases=["lubricant sounds", "Schmier-Geräusche", "Nasse Geräusche"],
            context="Feuchte Haut-zu-Haut Kontakt"
        ),

        SexualKeyword(
            keyword="Nasse Bewegungen",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="200-2000 Hz",
            priority=8,
            aliases=["wet movements", "nasse Bewegungen"],
        ),

        SexualKeyword(
            keyword="Schlürfgeräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="300-3000 Hz",
            priority=7,
            aliases=["sucking sounds", "Schlürf-Geräusche"],
        ),

        SexualKeyword(
            keyword="Sekretion-Sounds",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="100-1000 Hz",
            priority=7,
            aliases=["secretion sounds", "natürliche Feuchte"],
        ),

        SexualKeyword(
            keyword="Tropfen-Geräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="500-5000 Hz",
            priority=5,
            aliases=["dripping sounds", "Tropfen-Laute"],
        ),

        SexualKeyword(
            keyword="Squelch-Geräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="300-2000 Hz",
            priority=8,
            aliases=["squelching", "Quetschen-Laut"],
            context="Typisches feuchtes Eindringen-Geräusch"
        ),

        # ═══════════════════════════════════════════════════════════════════
        # ATEMZUG-MUSTER (8 Keywords)
        # ═══════════════════════════════════════════════════════════════════

        SexualKeyword(
            keyword="Vertieftes Atmen",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="100-1000 Hz",
            priority=8,
            aliases=["deep breathing", "tiefes Atmen"],
            context="Langsam, tief, rhythmisch"
        ),

        SexualKeyword(
            keyword="Schnelles Atmen",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="200-2000 Hz",
            priority=8,
            aliases=["rapid breathing", "schnelles Atmen"],
            context="Hyperventilation, Erregung"
        ),

        SexualKeyword(
            keyword="Keuchender Atem",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="150-1500 Hz",
            priority=8,
            aliases=["gasping breath", "Keuch-Atem"],
        ),

        SexualKeyword(
            keyword="Unterbrochener Atem",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="100-2000 Hz",
            priority=7,
            aliases=["interrupted breathing", "unterbrochener Atem"],
            context="Staccato-ähnliches Atmen"
        ),

        SexualKeyword(
            keyword="Wispy-Atmung",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="500-3000 Hz",
            priority=6,
            aliases=["wispy breathing", "Hauch-Atmen"],
        ),

        SexualKeyword(
            keyword="Nase-Atemzüge",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="200-1500 Hz",
            priority=5,
            aliases=["nasal breathing", "Nasen-Atem"],
        ),

        SexualKeyword(
            keyword="Mund-Atmung",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="100-3000 Hz",
            priority=7,
            aliases=["mouth breathing", "Mund-Atem"],
        ),

        SexualKeyword(
            keyword="Synchronisiertes Atmen",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="50-2000 Hz",
            priority=7,
            aliases=["synchronized breathing", "synchrones Atmen"],
            context="Beider Partner atmen zusammen"
        ),

        # ═══════════════════════════════════════════════════════════════════
        # UMFASSENDE SEXUAL-KEYWORDS ERWEITERUNG - 67 ZUSÄTZLICHE KEYWORDS
        # (Aus comprehensive_sexual_keywords.py - ALLE Varianten!)
        # ═══════════════════════════════════════════════════════════════════

        # ===== MÄNNLICHE LAUTE - LAUT =====
        SexualKeyword(
            keyword="Stöhnen (Männlich, Laut)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-400 Hz",
            priority=9,
            aliases=["moaning male loud", "Stöhnen laut"],
            context="Tiefe, laute Lautäußerung"
        ),
        SexualKeyword(
            keyword="Ächzen (Laut)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-450 Hz",
            priority=9,
            aliases=["gasping loud", "Ächzen-Laut"],
        ),
        SexualKeyword(
            keyword="Lustschrei männlich (Laut)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="150-500 Hz",
            priority=9,
            aliases=["male orgasm cry loud"],
        ),
        SexualKeyword(
            keyword="Brummen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-200 Hz",
            priority=8,
            aliases=["humming", "Brumm-Laut"],
        ),
        SexualKeyword(
            keyword="Grunzen (Laut)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-250 Hz",
            priority=8,
            aliases=["grunting loud"],
        ),
        SexualKeyword(
            keyword="Knurren (Laut)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="120-400 Hz",
            priority=8,
            aliases=["growling loud"],
        ),
        SexualKeyword(
            keyword="Ausstöhnen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-450 Hz",
            priority=9,
            aliases=["groaning loudly"],
        ),
        SexualKeyword(
            keyword="Keuchen männlich (Laut)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="150-500 Hz",
            priority=8,
            aliases=["panting male loud"],
        ),

        # ===== MÄNNLICHE LAUTE - LEISE =====
        SexualKeyword(
            keyword="Leises Stöhnen (Männlich)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-400 Hz",
            priority=7,
            aliases=["quiet moaning male"],
        ),
        SexualKeyword(
            keyword="Gedämpftes Ächzen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-450 Hz",
            priority=7,
            aliases=["muffled gasping"],
        ),
        SexualKeyword(
            keyword="Flüstern männlich (Laut)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-300 Hz",
            priority=6,
            aliases=["male whispering"],
        ),
        SexualKeyword(
            keyword="Hauchen (Männlich)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="150-400 Hz",
            priority=7,
            aliases=["breathy sounds male"],
        ),

        # ===== WEIBLICHE LAUTE - LAUT (ERWEITERT) =====
        SexualKeyword(
            keyword="Stöhnen weiblich (Laut-Erweitert)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-1000 Hz",
            priority=9,
            aliases=["loud female moaning"],
        ),
        SexualKeyword(
            keyword="Lustschrei (Sehr laut)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1500 Hz",
            priority=10,
            aliases=["intense orgasm cry"],
        ),
        SexualKeyword(
            keyword="Schreien weiblich (Lust)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="400-1500 Hz",
            priority=9,
            aliases=["screaming pleasure"],
        ),
        SexualKeyword(
            keyword="Quieken (Weiblich)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="800-2000 Hz",
            priority=8,
            aliases=["squealing female"],
        ),
        SexualKeyword(
            keyword="Jauchzen",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="500-1500 Hz",
            priority=9,
            aliases=["jubilant cries"],
        ),
        SexualKeyword(
            keyword="Schreien vor Lust (Extrem)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="400-1500 Hz",
            priority=10,
            aliases=["screaming orgasm"],
        ),
        SexualKeyword(
            keyword="Aufschrei (Weiblich)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1200 Hz",
            priority=9,
            aliases=["sharp cry female"],
        ),

        # ===== WEIBLICHE LAUTE - LEISE =====
        SexualKeyword(
            keyword="Leises Stöhnen weiblich (Extra-Leise)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-1000 Hz",
            priority=8,
            aliases=["whisper moaning"],
        ),
        SexualKeyword(
            keyword="Gedämpfter Laut (Weiblich)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1000 Hz",
            priority=7,
            aliases=["muffled female sounds"],
        ),
        SexualKeyword(
            keyword="Flüstern weiblich (Extra-Leise)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-800 Hz",
            priority=6,
            aliases=["female whispering soft"],
        ),
        SexualKeyword(
            keyword="Leises Keuchen (Weiblich)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1000 Hz",
            priority=7,
            aliases=["quiet panting female"],
        ),
        SexualKeyword(
            keyword="Hauchend (Weiblich, Leise)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-800 Hz",
            priority=6,
            aliases=["breathy female soft"],
        ),

        # ===== ORGASMUS-SPEZIFISCHE LAUTE =====
        SexualKeyword(
            keyword="Orgasmus Laut (Sehr laut)",
            activity_type=SexualActivityType.CLIMAX_INDICATORS,
            frequency_range="100-2000 Hz",
            priority=10,
            aliases=["loud orgasm"],
        ),
        SexualKeyword(
            keyword="Höhepunkt (Ekstase)",
            activity_type=SexualActivityType.CLIMAX_INDICATORS,
            frequency_range="150-2000 Hz",
            priority=10,
            aliases=["ecstatic climax"],
        ),
        SexualKeyword(
            keyword="Intensiv Laut (Orgasmus)",
            activity_type=SexualActivityType.CLIMAX_INDICATORS,
            frequency_range="200-1500 Hz",
            priority=9,
            aliases=["intense climax"],
        ),
        SexualKeyword(
            keyword="Finale Laut (Höhepunkt)",
            activity_type=SexualActivityType.CLIMAX_INDICATORS,
            frequency_range="150-2000 Hz",
            priority=9,
            aliases=["final orgasm cry"],
        ),
        SexualKeyword(
            keyword="Leiser Orgasmus",
            activity_type=SexualActivityType.CLIMAX_INDICATORS,
            frequency_range="100-2000 Hz",
            priority=8,
            aliases=["quiet orgasm"],
        ),
        SexualKeyword(
            keyword="Unterdrückter Höhepunkt",
            activity_type=SexualActivityType.CLIMAX_INDICATORS,
            frequency_range="50-1500 Hz",
            priority=7,
            aliases=["suppressed climax"],
        ),

        # ===== ATEMGERÄUSCHE - LAUT =====
        SexualKeyword(
            keyword="Schweres Atmen (Extra)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="200-3000 Hz",
            priority=8,
            aliases=["heavy breathing intense"],
        ),
        SexualKeyword(
            keyword="Schnelles Atmen (Extrem)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="300-2000 Hz",
            priority=8,
            aliases=["rapid heavy breathing"],
        ),
        SexualKeyword(
            keyword="Keuchen (Intensiv)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="400-2500 Hz",
            priority=8,
            aliases=["intense gasping"],
        ),
        SexualKeyword(
            keyword="Jauchen Atmung",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="300-2000 Hz",
            priority=7,
            aliases=["vocalized breathing"],
        ),
        SexualKeyword(
            keyword="Heftiges Atmen",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="200-3000 Hz",
            priority=8,
            aliases=["vigorous breathing"],
        ),

        # ===== ATEMGERÄUSCHE - LEISE =====
        SexualKeyword(
            keyword="Leises Atmen (Subtil)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="200-1000 Hz",
            priority=6,
            aliases=["soft quiet breathing"],
        ),
        SexualKeyword(
            keyword="Subtiles Atmen",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="150-800 Hz",
            priority=5,
            aliases=["subtle gentle breathing"],
        ),
        SexualKeyword(
            keyword="Flüsterndes Atmen",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="100-600 Hz",
            priority=5,
            aliases=["whispered breathing"],
        ),

        # ===== RHYTHMISCHE GERÄUSCHE - ERWEITERT =====
        SexualKeyword(
            keyword="Rhythmisches Stoßen (Detailliert)",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-100 Hz",
            priority=8,
            aliases=["rhythmic impact"],
        ),
        SexualKeyword(
            keyword="Stoß-Geräusche (Laut)",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="30-150 Hz",
            priority=9,
            aliases=["loud impact sounds"],
        ),
        SexualKeyword(
            keyword="Beschleunigte Rhythmus",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="50-200 Hz",
            priority=8,
            aliases=["accelerating impacts"],
        ),
        SexualKeyword(
            keyword="Langsame Rhythmus",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-80 Hz",
            priority=6,
            aliases=["slow rhythm"],
        ),
        SexualKeyword(
            keyword="Tiefe Rhythmus",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="10-100 Hz",
            priority=7,
            aliases=["deep low frequency"],
        ),
        SexualKeyword(
            keyword="Leise Rhythmus",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-100 Hz",
            priority=6,
            aliases=["quiet rhythm"],
        ),

        # ===== PENETRATIONS-GERÄUSCHE - ERWEITERT =====
        SexualKeyword(
            keyword="Schmier-Geräusch (Detailliert)",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="300-3000 Hz",
            priority=8,
            aliases=["lubrication sounds"],
        ),
        SexualKeyword(
            keyword="Nasse Geräusche (Intensiv)",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="400-2000 Hz",
            priority=8,
            aliases=["wet liquid sounds"],
        ),
        SexualKeyword(
            keyword="Schlürfende Geräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="500-2500 Hz",
            priority=7,
            aliases=["slurping sounds"],
        ),
        SexualKeyword(
            keyword="Quietschend (Penetration)",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="800-3000 Hz",
            priority=7,
            aliases=["squeaking penetration"],
        ),
        SexualKeyword(
            keyword="Saftiges Geräusch",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="300-2500 Hz",
            priority=8,
            aliases=["juicy sounds"],
        ),
        SexualKeyword(
            keyword="Leises Eindringen",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="300-2000 Hz",
            priority=6,
            aliases=["quiet penetration"],
        ),

        # ===== MÖBEL-GERÄUSCHE - ERWEITERT =====
        SexualKeyword(
            keyword="Bett quietscht (Intensiv)",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="50-2000 Hz",
            priority=7,
            aliases=["loud squeaking bed"],
        ),
        SexualKeyword(
            keyword="Federgeräusch (Detailliert)",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="100-500 Hz",
            priority=6,
            aliases=["spring resonance"],
        ),
        SexualKeyword(
            keyword="Matratze knackt",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="200-1000 Hz",
            priority=6,
            aliases=["mattress cracking"],
        ),
        SexualKeyword(
            keyword="Rahmen knarrt",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="100-800 Hz",
            priority=5,
            aliases=["frame creaking"],
        ),

        # ===== DIRTY TALK & VOKALISIERUNG =====
        SexualKeyword(
            keyword="Erotische Worte",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-1500 Hz",
            priority=7,
            aliases=["dirty talk female"],
        ),
        SexualKeyword(
            keyword="Befehle (Vokalisiert)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-2000 Hz",
            priority=6,
            aliases=["command vocals"],
        ),
        SexualKeyword(
            keyword="Leises Flüstern Erotisch",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="100-1000 Hz",
            priority=5,
            aliases=["erotic whispering"],
        ),

        # ===== DOMINANZ/UNTERWERFUNG =====
        SexualKeyword(
            keyword="Dominanz Laut",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-1000 Hz",
            priority=7,
            aliases=["dominant vocalization"],
        ),
        SexualKeyword(
            keyword="Unterwerfungs-Laute",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-1000 Hz",
            priority=6,
            aliases=["submissive sounds"],
        ),
        SexualKeyword(
            keyword="Befehle befolgen",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="150-1500 Hz",
            priority=6,
            aliases=["compliance sounds"],
        ),

        # ===== KUSSE & KONTAKT =====
        SexualKeyword(
            keyword="Küsse (Nass)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="500-2000 Hz",
            priority=5,
            aliases=["kissing wet"],
        ),
        SexualKeyword(
            keyword="Knabbern",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="800-3000 Hz",
            priority=5,
            aliases=["nibbling sounds"],
        ),
        SexualKeyword(
            keyword="Lecken Geräusch",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="1000-3000 Hz",
            priority=6,
            aliases=["licking sounds"],
        ),
        SexualKeyword(
            keyword="Saugend (Mundkontakt)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="600-2000 Hz",
            priority=6,
            aliases=["sucking sounds"],
        ),

        # ═══════════════════════════════════════════════════════════════════
        # MEGA-EXPANSION: ZUSÄTZLICHE 50+ KEYWORDS FÜR MAXIMALE ABDECKUNG
        # ═══════════════════════════════════════════════════════════════════

        # ===== SEHR SPEZIFISCHE WEIBLICHE VARIANTEN =====
        SexualKeyword(
            keyword="Schreiendes Stöhnen (Weiblich)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="400-2000 Hz",
            priority=9,
            aliases=["screaming moaning female"],
        ),
        SexualKeyword(
            keyword="Wiederholtes Ja-Ja-Ja",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1500 Hz",
            priority=8,
            aliases=["repeated yes yes yes"],
        ),
        SexualKeyword(
            keyword="Zischende Laute (Weiblich)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="2000-5000 Hz",
            priority=6,
            aliases=["hissing sounds female"],
        ),
        SexualKeyword(
            keyword="Stammelnde Worte (Orgasmus)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-2000 Hz",
            priority=7,
            aliases=["stammering climax"],
        ),
        SexualKeyword(
            keyword="Wimmernde Laute",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="400-2000 Hz",
            priority=7,
            aliases=["whimpering sounds"],
        ),
        SexualKeyword(
            keyword="Schluchzende Atemzüge",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1500 Hz",
            priority=7,
            aliases=["sobbing breaths"],
        ),
        SexualKeyword(
            keyword="Zitternde Stimme (Orgasmus)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-1000 Hz",
            priority=8,
            aliases=["trembling voice climax"],
        ),
        SexualKeyword(
            keyword="Heiseres Stöhnen",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="150-800 Hz",
            priority=8,
            aliases=["hoarse moaning"],
        ),

        # ===== SEHR SPEZIFISCHE MÄNNLICHE VARIANTEN =====
        SexualKeyword(
            keyword="Kehliges Stöhnen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-300 Hz",
            priority=8,
            aliases=["guttural moaning"],
        ),
        SexualKeyword(
            keyword="Brummender Orgasmus",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="50-200 Hz",
            priority=9,
            aliases=["deep humming climax"],
        ),
        SexualKeyword(
            keyword="Zischender Laut (Männlich)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="1500-3000 Hz",
            priority=5,
            aliases=["hissing male"],
        ),
        SexualKeyword(
            keyword="Heiseres Keuchen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-500 Hz",
            priority=7,
            aliases=["hoarse panting"],
        ),
        SexualKeyword(
            keyword="Knurrendes Stöhnen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-250 Hz",
            priority=8,
            aliases=["growling moaning"],
        ),

        # ===== PENETRATIONS-VARIATION ERWEITERT =====
        SexualKeyword(
            keyword="Schlüpfende Geräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="400-3000 Hz",
            priority=8,
            aliases=["slipping sounds"],
        ),
        SexualKeyword(
            keyword="Klatschende Schläge",
            activity_type=SexualActivityType.IMPACT_SOUNDS,
            frequency_range="100-1000 Hz",
            priority=9,
            aliases=["slapping sounds"],
        ),
        SexualKeyword(
            keyword="Peitschende Schläge",
            activity_type=SexualActivityType.IMPACT_SOUNDS,
            frequency_range="200-2000 Hz",
            priority=7,
            aliases=["whipping sounds"],
        ),
        SexualKeyword(
            keyword="Sauggeräusche (Vakuum)",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="500-2000 Hz",
            priority=8,
            aliases=["suction sounds"],
        ),
        SexualKeyword(
            keyword="Quetschgeräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="300-2500 Hz",
            priority=7,
            aliases=["squeezing sounds"],
        ),
        SexualKeyword(
            keyword="Glucksende Geräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="400-3000 Hz",
            priority=6,
            aliases=["gurgling sounds"],
        ),

        # ===== RHYTHMUS-VARIATIONEN ERWEITERT =====
        SexualKeyword(
            keyword="Stoß-Stoß-Stoß (Schnell)",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="50-200 Hz",
            priority=9,
            aliases=["rapid thrust thrust"],
        ),
        SexualKeyword(
            keyword="Langsam-Schnell-Langsam",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="10-150 Hz",
            priority=7,
            aliases=["slow fast slow rhythm"],
        ),
        SexualKeyword(
            keyword="Pulsierende Rhythmen",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="30-100 Hz",
            priority=7,
            aliases=["pulsating rhythm"],
        ),
        SexualKeyword(
            keyword="Zuckende Bewegungen",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="50-200 Hz",
            priority=7,
            aliases=["jerking movements"],
        ),
        SexualKeyword(
            keyword="Wirbelnde Rhythmen",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-100 Hz",
            priority=6,
            aliases=["swirling rhythm"],
        ),

        # ===== FURNITURE/ENVIRONMENTAL ERWEITERT =====
        SexualKeyword(
            keyword="Kopfbrett schlägt Wand",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="100-500 Hz",
            priority=8,
            aliases=["headboard wall impact"],
        ),
        SexualKeyword(
            keyword="Bett kollabiert Geräusch",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="50-300 Hz",
            priority=7,
            aliases=["bed collapse sound"],
        ),
        SexualKeyword(
            keyword="Metallgerassel",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="300-2000 Hz",
            priority=6,
            aliases=["metal rattling"],
        ),
        SexualKeyword(
            keyword="Holz-Knacken (Fortlaufend)",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="100-600 Hz",
            priority=6,
            aliases=["wood cracking continuous"],
        ),

        # ===== KOMBINIERTE PATTERNS =====
        SexualKeyword(
            keyword="Rhythmus + Stöhnen (Synchron)",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-500 Hz",
            priority=9,
            aliases=["synchronized moaning rhythm"],
        ),
        SexualKeyword(
            keyword="Atmen + Stoßen (Versetzt)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="50-2000 Hz",
            priority=8,
            aliases=["breathing thrusting offset"],
        ),
        SexualKeyword(
            keyword="Doppelte Lautäußerung (Paar)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-1500 Hz",
            priority=8,
            aliases=["dual vocalization pair"],
        ),
        SexualKeyword(
            keyword="Echo/Resonanz (Raum)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="50-3000 Hz",
            priority=5,
            aliases=["room resonance echo"],
        ),

        # ===== EXTREME/SPEZIALE SZENEN =====
        SexualKeyword(
            keyword="Aggressive Stoße (Keuchen)",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="80-300 Hz",
            priority=9,
            aliases=["aggressive panting thrusts"],
        ),
        SexualKeyword(
            keyword="Unterwerfungs-Jaulen",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-2000 Hz",
            priority=7,
            aliases=["submission wailing"],
        ),
        SexualKeyword(
            keyword="Dominanz-Brummen",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="80-200 Hz",
            priority=7,
            aliases=["dominant rumbling"],
        ),
        SexualKeyword(
            keyword="Fesslung-Geräusche",
            activity_type=SexualActivityType.FURNITURE_SOUNDS,
            frequency_range="200-1500 Hz",
            priority=6,
            aliases=["restraint sounds"],
        ),
        SexualKeyword(
            keyword="Spanking-Sound + Schrei",
            activity_type=SexualActivityType.IMPACT_SOUNDS,
            frequency_range="200-2000 Hz",
            priority=8,
            aliases=["spanking cry"],
        ),

        # ===== AFTEREFFECTS/ENDING =====
        SexualKeyword(
            keyword="Nachglühen-Atemzüge",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="50-1000 Hz",
            priority=5,
            aliases=["afterglow breathing"],
        ),
        SexualKeyword(
            keyword="Ruhiges Atmen (Post)",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="100-500 Hz",
            priority=4,
            aliases=["calming breathing post"],
        ),
        SexualKeyword(
            keyword="Zufriedenes Seufzer",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="150-600 Hz",
            priority=5,
            aliases=["satisfied sigh"],
        ),
        SexualKeyword(
            keyword="Kichern (Nach-Lust)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="400-2000 Hz",
            priority=4,
            aliases=["giggling post-pleasure"],
        ),

        # ===== ULTRA-SPECIFIQUE GERMAN VARIANTS =====
        SexualKeyword(
            keyword="Lustiger Schrei (Deutsch)",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1500 Hz",
            priority=9,
            aliases=["German pleasure cry"],
        ),
        SexualKeyword(
            keyword="Akzentuiertes Stöhnen (Deutsch)",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-400 Hz",
            priority=8,
            aliases=["German moaning accented"],
        ),
        SexualKeyword(
            keyword="Ja-Ja-Nein Mix",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="300-1500 Hz",
            priority=7,
            aliases=["yes yes no mix German"],
        ),

        # ═══════════════════════════════════════════════════════════════════
        # PORNO-VIDEO + AUDIO-HINTERGRUND MUSTER (15+ Keywords)
        # ═══════════════════════════════════════════════════════════════════

        SexualKeyword(
            keyword="Porno-Video-Hintergrund-Sound",
            activity_type=SexualActivityType.PLEASURE_INDICATORS,
            frequency_range="50-3000 Hz",
            priority=7,
            aliases=["pornography background audio"],
        ),
        SexualKeyword(
            keyword="Studio-Lichter-Buzz",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="60 Hz",
            priority=3,
            aliases=["studio lights hum"],
        ),
        SexualKeyword(
            keyword="Kameraschutter-Click",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="200-1000 Hz",
            priority=2,
            aliases=["camera shutter"],
        ),
        SexualKeyword(
            keyword="Szenario-Setup Dialogue",
            activity_type=SexualActivityType.FEMALE_VOCALIZATION,
            frequency_range="200-2000 Hz",
            priority=5,
            aliases=["setup dialogue scenario"],
        ),
        SexualKeyword(
            keyword="Pizza-Delivery Intro",
            activity_type=SexualActivityType.MALE_VOCALIZATION,
            frequency_range="100-1500 Hz",
            priority=4,
            aliases=["pizza delivery scenario"],
        ),
        SexualKeyword(
            keyword="Porno-Musik Hintergrund",
            activity_type=SexualActivityType.PLEASURE_INDICATORS,
            frequency_range="100-500 Hz",
            priority=6,
            aliases=["porn music background"],
        ),
        SexualKeyword(
            keyword="Spritzende Flüssigkeit",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="500-3000 Hz",
            priority=8,
            aliases=["squirting sounds"],
        ),
        SexualKeyword(
            keyword="Tief-Kehle-Würg-Geräusche",
            activity_type=SexualActivityType.BREATHING_PATTERNS,
            frequency_range="200-1000 Hz",
            priority=8,
            aliases=["deepthroat gagging"],
        ),
        SexualKeyword(
            keyword="Anal-Eindring-Geräusche",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="300-2000 Hz",
            priority=7,
            aliases=["anal penetration sounds"],
        ),
        SexualKeyword(
            keyword="Cumshot-Geräusch",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="500-2000 Hz",
            priority=8,
            aliases=["cum shot sound"],
        ),
        SexualKeyword(
            keyword="Abspritzen (Weiblich)",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="1000-3000 Hz",
            priority=9,
            aliases=["female squirting"],
        ),
        SexualKeyword(
            keyword="Sperma-Geräusch",
            activity_type=SexualActivityType.LUBRICANT_SOUNDS,
            frequency_range="500-3000 Hz",
            priority=7,
            aliases=["semen sounds"],
        ),
        SexualKeyword(
            keyword="Doppelpenetration-Geräusche",
            activity_type=SexualActivityType.RHYTHM_PATTERNS,
            frequency_range="20-300 Hz",
            priority=8,
            aliases=["double penetration sounds"],
        ),
        SexualKeyword(
            keyword="Gruppe-Sex-Hintergrund",
            activity_type=SexualActivityType.PLEASURE_INDICATORS,
            frequency_range="100-2000 Hz",
            priority=7,
            aliases=["group sex background"],
        ),
        SexualKeyword(
            keyword="Credits-Roll (Porno)",
            activity_type=SexualActivityType.PLEASURE_INDICATORS,
            frequency_range="100-500 Hz",
            priority=2,
            aliases=["porn credits rolling"],
        ),
    ]

    @classmethod
    def get_all_keywords(cls) -> List[SexualKeyword]:
        """Gibt alle Keywords zurück."""
        return cls.KEYWORDS

    @classmethod
    def get_by_type(cls, activity_type: SexualActivityType) -> List[SexualKeyword]:
        """Gibt Keywords nach Typ."""
        return [kw for kw in cls.KEYWORDS if kw.activity_type == activity_type]

    @classmethod
    def get_high_priority(cls, min_priority: int = 8) -> List[SexualKeyword]:
        """Gibt High-Priority Keywords."""
        return [kw for kw in cls.KEYWORDS if kw.priority >= min_priority]

    @classmethod
    def generate_keyword_profile_dict(cls) -> dict:
        """Generiere ein komplettes Keyword-Profil."""
        return {
            "profile_id": "sexual_activity",
            "name": "Sexuelle Aktivität - Maximale Erkennung",
            "description": "Umfassendes Profil für Detektion von Geschlechtsverkehr (74+ Keywords)",
            "keywords": [
                {
                    "text": kw.keyword,
                    "priority": kw.priority,
                    "confidence_threshold": kw.confidence_threshold,
                    "category": kw.activity_type.value,
                    "frequency_range": kw.frequency_range,
                    "duration_ms": kw.duration_ms,
                    "aliases": kw.aliases,
                    "context": kw.context,
                }
                for kw in cls.KEYWORDS
            ],
            "recording_mode": "Kontinuierlich mit Highlights",
            "pre_trigger_seconds": 10,
            "post_trigger_seconds": 15,
            "min_keyword_gap_seconds": 1,
            "max_recording_duration": 3600,
            "confidence_threshold": 0.70,
            "total_keywords": len(cls.KEYWORDS),
            "description_extended": "🔥 ULTRA-UMFASSEND: 140+ Keywords - Männlich/Weiblich, Laut/Leise, Alle Audio-Muster!"
        }


def get_sexual_activity_profile():
    """Factory für Sexual Activity Profil."""
    return SexualKeywordsLibrary.generate_keyword_profile_dict()
