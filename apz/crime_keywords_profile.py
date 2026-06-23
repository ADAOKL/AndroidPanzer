"""CRIME KEYWORDS: Keywords für Kriminalität, Mord, Straftaten jeglicher Art!

Umfassende Sammlung für Detektion von kriminellen Aktivitäten.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class CrimeType(Enum):
    """Straftat-Typen."""
    MURDER = "Mord"
    ASSAULT = "Körperverletzung"
    ROBBERY = "Raub"
    THEFT = "Diebstahl"
    FRAUD = "Betrug"
    KIDNAPPING = "Entführung"
    WEAPONS = "Waffen"
    PLANNING = "Planung"
    VIOLENCE = "Gewalt"
    TRAFFICKING = "Menschenhandel"


@dataclass
class CrimeKeyword:
    """Ein Straftat-Keyword."""
    keyword: str
    crime_type: CrimeType
    priority: int = 8
    aliases: List[str] = field(default_factory=list)
    context: str = ""


class CrimeKeywordsLibrary:
    """Straftat-Keywords Sammlung."""

    KEYWORDS: List[CrimeKeyword] = [
        # MURDER
        CrimeKeyword("Mord", CrimeType.MURDER, priority=10, aliases=["Töten", "Kill", "Murder"]),
        CrimeKeyword("Leiche", CrimeType.MURDER, priority=9, aliases=["Body", "Corpse"]),
        CrimeKeyword("Beseitigen", CrimeType.MURDER, priority=9, context="Beweis/Leiche"),
        CrimeKeyword("Opfer", CrimeType.MURDER, priority=8, aliases=["Victim"]),
        CrimeKeyword("Blut", CrimeType.MURDER, priority=8, aliases=["Blood", "Blutung"]),
        CrimeKeyword("Waffe", CrimeType.MURDER, priority=9, aliases=["Weapon", "Gun", "Messer"]),
        CrimeKeyword("Ermordung", CrimeType.MURDER, priority=9),
        CrimeKeyword("Hinrichten", CrimeType.MURDER, priority=9),

        # ASSAULT
        CrimeKeyword("Schlag", CrimeType.ASSAULT, priority=7, aliases=["Hit", "Beat", "Schläge"]),
        CrimeKeyword("Angriff", CrimeType.ASSAULT, priority=8, aliases=["Attack", "Assault"]),
        CrimeKeyword("Verprügeln", CrimeType.ASSAULT, priority=8),
        CrimeKeyword("Prügel", CrimeType.ASSAULT, priority=7),
        CrimeKeyword("Verletzung", CrimeType.ASSAULT, priority=7, aliases=["Injury"]),

        # ROBBERY
        CrimeKeyword("Raub", CrimeType.ROBBERY, priority=9, aliases=["Rob", "Robbery"]),
        CrimeKeyword("Überfall", CrimeType.ROBBERY, priority=9, aliases=["Mugging"]),
        CrimeKeyword("Geld rauben", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Beute", CrimeType.ROBBERY, priority=7, aliases=["Loot", "Spoils"]),
        CrimeKeyword("Ausrauben", CrimeType.ROBBERY, priority=8),

        # THEFT
        CrimeKeyword("Diebstahl", CrimeType.THEFT, priority=8, aliases=["Theft", "Stealing"]),
        CrimeKeyword("Stehlen", CrimeType.THEFT, priority=8, aliases=["Steal", "Nick"]),
        CrimeKeyword("Klau", CrimeType.THEFT, priority=7),
        CrimeKeyword("Beute", CrimeType.THEFT, priority=6),
        CrimeKeyword("Einbruch", CrimeType.THEFT, priority=8, aliases=["Burglary", "Break-in"]),
        CrimeKeyword("Auto-Klau", CrimeType.THEFT, priority=8, aliases=["Car theft"]),

        # FRAUD
        CrimeKeyword("Betrug", CrimeType.FRAUD, priority=8, aliases=["Fraud", "Scam"]),
        CrimeKeyword("Fälschung", CrimeType.FRAUD, priority=8, aliases=["Forgery"]),
        CrimeKeyword("Täuschung", CrimeType.FRAUD, priority=7),
        CrimeKeyword("Bluff", CrimeType.FRAUD, priority=6),
        CrimeKeyword("Fälschen", CrimeType.FRAUD, priority=8, aliases=["Forge"]),

        # KIDNAPPING
        CrimeKeyword("Entführung", CrimeType.KIDNAPPING, priority=10, aliases=["Kidnapping", "Abduction"]),
        CrimeKeyword("Entführen", CrimeType.KIDNAPPING, priority=9, aliases=["Kidnap", "Abduct"]),
        CrimeKeyword("Geisel", CrimeType.KIDNAPPING, priority=9, aliases=["Hostage"]),
        CrimeKeyword("Lösegeld", CrimeType.KIDNAPPING, priority=9, aliases=["Ransom"]),
        CrimeKeyword("Festhalten", CrimeType.KIDNAPPING, priority=8, context="Gegen Willen"),

        # WEAPONS
        CrimeKeyword("Waffe", CrimeType.WEAPONS, priority=9, aliases=["Weapon", "Gun"]),
        CrimeKeyword("Pistole", CrimeType.WEAPONS, priority=9, aliases=["Gun", "Handgun"]),
        CrimeKeyword("Gewehr", CrimeType.WEAPONS, priority=9, aliases=["Rifle"]),
        CrimeKeyword("Messer", CrimeType.WEAPONS, priority=8, aliases=["Knife"]),
        CrimeKeyword("Bombe", CrimeType.WEAPONS, priority=10, aliases=["Bomb", "Explosive"]),
        CrimeKeyword("Sprengstoff", CrimeType.WEAPONS, priority=9, aliases=["Explosive"]),
        CrimeKeyword("Munition", CrimeType.WEAPONS, priority=8, aliases=["Ammunition"]),

        # PLANNING
        CrimeKeyword("Plan", CrimeType.PLANNING, priority=7, context="Krimineller Plan"),
        CrimeKeyword("Vorbereitung", CrimeType.PLANNING, priority=8),
        CrimeKeyword("Planung", CrimeType.PLANNING, priority=8),
        CrimeKeyword("Absprache", CrimeType.PLANNING, priority=8, aliases=["Conspiring"]),
        CrimeKeyword("Verschwörung", CrimeType.PLANNING, priority=8, aliases=["Conspiracy"]),

        # VIOLENCE
        CrimeKeyword("Gewalt", CrimeType.VIOLENCE, priority=8, aliases=["Violence"]),
        CrimeKeyword("Gewalttätig", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Straße", CrimeType.VIOLENCE, priority=5, context="Street violence"),
        CrimeKeyword("Gang", CrimeType.VIOLENCE, priority=7, aliases=["Gang violence"]),

        # TRAFFICKING
        CrimeKeyword("Menschenhandel", CrimeType.TRAFFICKING, priority=10, aliases=["Human trafficking"]),
        CrimeKeyword("Sklaverei", CrimeType.TRAFFICKING, priority=9, aliases=["Slavery"]),
        CrimeKeyword("Ausbeutung", CrimeType.TRAFFICKING, priority=8, aliases=["Exploitation"]),
        CrimeKeyword("Zwang", CrimeType.TRAFFICKING, priority=7, aliases=["Coercion"]),
    ]

    @classmethod
    def get_all_keywords(cls) -> List[CrimeKeyword]:
        """Gibt alle Keywords zurück."""
        return cls.KEYWORDS


def get_crime_keywords_profile():
    """Factory für Crime Keywords."""
    return {
        "profile_id": "crime_activity",
        "name": "Straftaten - Alle Arten",
        "keywords": [
            {
                "text": kw.keyword,
                "priority": kw.priority,
                "category": kw.crime_type.value,
                "aliases": kw.aliases,
            }
            for kw in CrimeKeywordsLibrary.KEYWORDS
        ],
        "total_keywords": len(CrimeKeywordsLibrary.KEYWORDS),
    }
