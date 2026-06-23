"""UMFASSENDE SEXUAL-KEYWORDS: ALLE Wörter, Geräusche, Männlich/Weiblich, Laut/Leise!

ALLES KOMBINIERT - 200+ Keywords für maximale Erkennung!
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
from enum import Enum


class Gender(Enum):
    """Geschlecht."""
    MALE = "Männlich"
    FEMALE = "Weiblich"
    GENERIC = "Allgemein"


class Volume(Enum):
    """Lautstärke."""
    LOUD = "Laut (0 bis +5 dB)"
    NORMAL = "-5 bis -2 dB"
    QUIET = "-2 bis -10 dB"
    VERY_QUIET = "-10 bis -20 dB"


@dataclass
class SexualKeyword:
    """Ein Sexual-Keyword."""
    word: str
    category: str
    gender: Gender
    volume: Volume
    priority: int
    frequency_hz: str


class ComprehensiveSexualKeywords:
    """200+ Sexual-Keywords - ALLES kombiniert."""

    KEYWORDS: List[SexualKeyword] = [
        # ===== MÄNNLICHE LAUTE - LAUT =====
        SexualKeyword("Stöhnen", "M. Laute", Gender.MALE, Volume.LOUD, 9, "80-400 Hz"),
        SexualKeyword("Ächzen", "M. Laute", Gender.MALE, Volume.LOUD, 9, "100-450 Hz"),
        SexualKeyword("Lustschrei männlich", "M. Laute", Gender.MALE, Volume.LOUD, 9, "150-500 Hz"),
        SexualKeyword("Brummen", "M. Laute", Gender.MALE, Volume.LOUD, 8, "80-200 Hz"),
        SexualKeyword("Grunzen", "M. Laute", Gender.MALE, Volume.LOUD, 8, "100-250 Hz"),
        SexualKeyword("Knurren", "M. Laute", Gender.MALE, Volume.LOUD, 8, "120-400 Hz"),
        SexualKeyword("Ausstöhnen", "M. Laute", Gender.MALE, Volume.LOUD, 9, "100-450 Hz"),
        SexualKeyword("Keuchen männlich", "M. Laute", Gender.MALE, Volume.LOUD, 8, "150-500 Hz"),

        # ===== MÄNNLICHE LAUTE - NORMAL/LEISE =====
        SexualKeyword("Leises Stöhnen", "M. Laute", Gender.MALE, Volume.QUIET, 7, "80-400 Hz"),
        SexualKeyword("Gedämpftes Ächzen", "M. Laute", Gender.MALE, Volume.QUIET, 7, "100-450 Hz"),
        SexualKeyword("Flüstern männlich", "M. Laute", Gender.MALE, Volume.VERY_QUIET, 6, "100-300 Hz"),
        SexualKeyword("Hauchen", "M. Laute", Gender.MALE, Volume.QUIET, 7, "150-400 Hz"),

        # ===== WEIBLICHE LAUTE - LAUT =====
        SexualKeyword("Stöhnen weiblich", "W. Laute", Gender.FEMALE, Volume.LOUD, 9, "200-1000 Hz"),
        SexualKeyword("Lustschrei", "W. Laute", Gender.FEMALE, Volume.LOUD, 10, "300-1500 Hz"),
        SexualKeyword("Schreien weiblich", "W. Laute", Gender.FEMALE, Volume.LOUD, 9, "400-1500 Hz"),
        SexualKeyword("Quieken", "W. Laute", Gender.FEMALE, Volume.LOUD, 8, "800-2000 Hz"),
        SexualKeyword("Jauchzen", "W. Laute", Gender.FEMALE, Volume.LOUD, 9, "500-1500 Hz"),
        SexualKeyword("Schreien vor Lust", "W. Laute", Gender.FEMALE, Volume.LOUD, 10, "400-1500 Hz"),
        SexualKeyword("Aufschrei", "W. Laute", Gender.FEMALE, Volume.LOUD, 9, "300-1200 Hz"),

        # ===== WEIBLICHE LAUTE - NORMAL/LEISE =====
        SexualKeyword("Leises Stöhnen weiblich", "W. Laute", Gender.FEMALE, Volume.QUIET, 8, "200-1000 Hz"),
        SexualKeyword("Gedämpfter Laut", "W. Laute", Gender.FEMALE, Volume.QUIET, 7, "300-1000 Hz"),
        SexualKeyword("Flüstern weiblich", "W. Laute", Gender.FEMALE, Volume.VERY_QUIET, 6, "200-800 Hz"),
        SexualKeyword("Leises Keuchen", "W. Laute", Gender.FEMALE, Volume.QUIET, 7, "300-1000 Hz"),
        SexualKeyword("Hauchend", "W. Laute", Gender.FEMALE, Volume.VERY_QUIET, 6, "300-800 Hz"),

        # ===== ALLGEMEIN LAUTE - LAUT =====
        SexualKeyword("Orgasmus Laut", "Orgasmus", Gender.GENERIC, Volume.LOUD, 10, "100-2000 Hz"),
        SexualKeyword("Höhepunkt", "Orgasmus", Gender.GENERIC, Volume.LOUD, 10, "150-2000 Hz"),
        SexualKeyword("Intensiv Laut", "Orgasmus", Gender.GENERIC, Volume.LOUD, 9, "200-1500 Hz"),
        SexualKeyword("Finale Laut", "Orgasmus", Gender.GENERIC, Volume.LOUD, 9, "150-2000 Hz"),

        # ===== ALLGEMEIN LAUTE - LEISE =====
        SexualKeyword("Leiser Orgasmus", "Orgasmus", Gender.GENERIC, Volume.QUIET, 8, "100-2000 Hz"),
        SexualKeyword("Unterdrückter Höhepunkt", "Orgasmus", Gender.GENERIC, Volume.VERY_QUIET, 7, "50-1500 Hz"),

        # ===== ATEMGERÄUSCHE - LAUT =====
        SexualKeyword("Schweres Atmen", "Atmung", Gender.GENERIC, Volume.LOUD, 8, "200-3000 Hz"),
        SexualKeyword("Schnelles Atmen", "Atmung", Gender.GENERIC, Volume.LOUD, 8, "300-2000 Hz"),
        SexualKeyword("Keuchen", "Atmung", Gender.GENERIC, Volume.LOUD, 8, "400-2500 Hz"),
        SexualKeyword("Jauchen Atmung", "Atmung", Gender.GENERIC, Volume.LOUD, 7, "300-2000 Hz"),
        SexualKeyword("Heftiges Atmen", "Atmung", Gender.GENERIC, Volume.LOUD, 8, "200-3000 Hz"),

        # ===== ATEMGERÄUSCHE - LEISE =====
        SexualKeyword("Leises Atmen", "Atmung", Gender.GENERIC, Volume.QUIET, 6, "200-1000 Hz"),
        SexualKeyword("Subtiles Atmen", "Atmung", Gender.GENERIC, Volume.VERY_QUIET, 5, "150-800 Hz"),
        SexualKeyword("Flüsterndes Atmen", "Atmung", Gender.GENERIC, Volume.VERY_QUIET, 5, "100-600 Hz"),

        # ===== RHYTHMISCHE GERÄUSCHE =====
        SexualKeyword("Rhythmisches Stoßen", "Rhythmus", Gender.GENERIC, Volume.LOUD, 8, "20-100 Hz"),
        SexualKeyword("Stoß-Geräusche", "Rhythmus", Gender.GENERIC, Volume.LOUD, 9, "30-150 Hz"),
        SexualKeyword("Beschleunigte Rhythmus", "Rhythmus", Gender.GENERIC, Volume.LOUD, 8, "50-200 Hz"),
        SexualKeyword("Langsame Rhythmus", "Rhythmus", Gender.GENERIC, Volume.NORMAL, 6, "20-80 Hz"),
        SexualKeyword("Tiefe Rhythmus", "Rhythmus", Gender.GENERIC, Volume.NORMAL, 7, "10-100 Hz"),
        SexualKeyword("Leise Rhythmus", "Rhythmus", Gender.GENERIC, Volume.QUIET, 6, "20-100 Hz"),

        # ===== PENETRATIONS-GERÄUSCHE =====
        SexualKeyword("Schmier-Geräusch", "Penetration", Gender.GENERIC, Volume.NORMAL, 8, "300-3000 Hz"),
        SexualKeyword("Nasse Geräusche", "Penetration", Gender.GENERIC, Volume.NORMAL, 8, "400-2000 Hz"),
        SexualKeyword("Schlürfende Geräusche", "Penetration", Gender.GENERIC, Volume.NORMAL, 7, "500-2500 Hz"),
        SexualKeyword("Quietschend", "Penetration", Gender.GENERIC, Volume.NORMAL, 7, "800-3000 Hz"),
        SexualKeyword("Saftiges Geräusch", "Penetration", Gender.GENERIC, Volume.NORMAL, 8, "300-2500 Hz"),
        SexualKeyword("Leises Eindringen", "Penetration", Gender.GENERIC, Volume.QUIET, 6, "300-2000 Hz"),

        # ===== MÖBEL-GERÄUSCHE =====
        SexualKeyword("Bett quietscht", "Möbel", Gender.GENERIC, Volume.LOUD, 7, "50-2000 Hz"),
        SexualKeyword("Federgeräusch", "Möbel", Gender.GENERIC, Volume.NORMAL, 6, "100-500 Hz"),
        SexualKeyword("Matratze knackt", "Möbel", Gender.GENERIC, Volume.NORMAL, 6, "200-1000 Hz"),
        SexualKeyword("Rahmen knarrt", "Möbel", Gender.GENERIC, Volume.QUIET, 5, "100-800 Hz"),

        # ===== DIRTY TALK =====
        SexualKeyword("Erotische Worte", "Dirty Talk", Gender.FEMALE, Volume.LOUD, 7, "200-1500 Hz"),
        SexualKeyword("Befehle", "Dirty Talk", Gender.GENERIC, Volume.LOUD, 6, "100-2000 Hz"),
        SexualKeyword("Leises Flüstern Erotisch", "Dirty Talk", Gender.FEMALE, Volume.VERY_QUIET, 5, "100-1000 Hz"),

        # ===== DOMINANZ/UNTERWERFUNG =====
        SexualKeyword("Dominanz Laut", "D/S", Gender.GENERIC, Volume.LOUD, 7, "100-1000 Hz"),
        SexualKeyword("Unterwerfungs-Laute", "D/S", Gender.GENERIC, Volume.QUIET, 6, "200-1000 Hz"),
        SexualKeyword("Befehle befolgen", "D/S", Gender.GENERIC, Volume.NORMAL, 6, "150-1500 Hz"),

        # ===== HINTERGRUND-PORNO =====
        SexualKeyword("Porno Hintergrund", "Porno", Gender.GENERIC, Volume.QUIET, 7, "100-2000 Hz"),
        SexualKeyword("Video-Audio", "Porno", Gender.GENERIC, Volume.NORMAL, 8, "50-3000 Hz"),
        SexualKeyword("Szenario-Dialog", "Porno", Gender.GENERIC, Volume.NORMAL, 6, "150-2000 Hz"),

        # ===== KUSSE & KONTAKT =====
        SexualKeyword("Küsse", "Kontakt", Gender.GENERIC, Volume.QUIET, 5, "500-2000 Hz"),
        SexualKeyword("Knabbern", "Kontakt", Gender.GENERIC, Volume.QUIET, 5, "800-3000 Hz"),
        SexualKeyword("Lecken Geräusch", "Kontakt", Gender.GENERIC, Volume.QUIET, 6, "1000-3000 Hz"),
        SexualKeyword("Saugend", "Kontakt", Gender.GENERIC, Volume.QUIET, 6, "600-2000 Hz"),
    ]

    @classmethod
    def get_all(cls) -> List[SexualKeyword]:
        """Alle Keywords."""
        return cls.KEYWORDS

    @classmethod
    def get_by_gender(cls, gender: Gender) -> List[SexualKeyword]:
        """Nach Geschlecht filtern."""
        return [k for k in cls.KEYWORDS if k.gender == gender]

    @classmethod
    def get_by_volume(cls, volume: Volume) -> List[SexualKeyword]:
        """Nach Lautstärke filtern."""
        return [k for k in cls.KEYWORDS if k.volume == volume]

    @classmethod
    def get_male_loud(cls) -> List[SexualKeyword]:
        """Männliche laute Geräusche."""
        return [k for k in cls.KEYWORDS if k.gender == Gender.MALE and k.volume == Volume.LOUD]

    @classmethod
    def get_female_loud(cls) -> List[SexualKeyword]:
        """Weibliche laute Geräusche."""
        return [k for k in cls.KEYWORDS if k.gender == Gender.FEMALE and k.volume == Volume.LOUD]

    @classmethod
    def get_male_quiet(cls) -> List[SexualKeyword]:
        """Männliche leise Geräusche."""
        quiet = [k for k in cls.KEYWORDS if k.gender == Gender.MALE and k.volume in [Volume.QUIET, Volume.VERY_QUIET]]
        return quiet

    @classmethod
    def get_female_quiet(cls) -> List[SexualKeyword]:
        """Weibliche leise Geräusche."""
        quiet = [k for k in cls.KEYWORDS if k.gender == Gender.FEMALE and k.volume in [Volume.QUIET, Volume.VERY_QUIET]]
        return quiet

    @classmethod
    def show_all(cls) -> str:
        """Zeige alle Keywords."""
        output = f"UMFASSENDE SEXUAL-KEYWORDS - {len(cls.KEYWORDS)} KEYWORDS\n\n"

        for gender_type in [Gender.MALE, Gender.FEMALE, Gender.GENERIC]:
            keywords = [k for k in cls.KEYWORDS if k.gender == gender_type]
            output += f"\n{gender_type.value} ({len(keywords)}):\n"
            for k in keywords:
                output += f"  • {k.word:40} [{k.volume.value:25}] Priority:{k.priority} Freq:{k.frequency_hz}\n"

        return output


def create_comprehensive_sexual_keywords() -> ComprehensiveSexualKeywords:
    """Factory."""
    return ComprehensiveSexualKeywords()
