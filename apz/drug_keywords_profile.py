"""DRUG KEYWORDS: Keywords für Drogen-Erkennung und -Konsum!

Umfassend für Detektion von Drogen-Aktivitäten basierend auf Audio-Patterns und Gespräche.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class DrugActivityType(Enum):
    """Drogen-Aktivitäts-Typen."""
    CONSUMPTION = "Konsum"
    DEALING = "Handel"
    PRODUCTION = "Herstellung"
    EFFECTS = "Effekte"
    TOOLS = "Werkzeuge/Geräte"
    MONEY = "Geldtransfer"


@dataclass
class DrugKeyword:
    """Ein Drogen-Keyword."""
    keyword: str
    activity_type: DrugActivityType
    priority: int = 7
    confidence_threshold: float = 0.75
    aliases: List[str] = field(default_factory=list)
    context: str = ""


class DrugKeywordsLibrary:
    """Drogen-Keywords Sammlung."""

    KEYWORDS: List[DrugKeyword] = [
        # CONSUMPTION
        DrugKeyword("Kokain", DrugActivityType.CONSUMPTION, priority=9, aliases=["Koks", "Coke", "Snow"]),
        DrugKeyword("Heroin", DrugActivityType.CONSUMPTION, priority=9, aliases=["H", "Dope", "Smack"]),
        DrugKeyword("Cannabis", DrugActivityType.CONSUMPTION, priority=8, aliases=["Weed", "Gras", "Marihuana"]),
        DrugKeyword("MDMA", DrugActivityType.CONSUMPTION, priority=8, aliases=["Ecstasy", "Molly", "E"]),
        DrugKeyword("Methamphetamin", DrugActivityType.CONSUMPTION, priority=9, aliases=["Meth", "Crystal", "Speed"]),
        DrugKeyword("LSD", DrugActivityType.CONSUMPTION, priority=7, aliases=["Acid", "Trips"]),
        DrugKeyword("Crack", DrugActivityType.CONSUMPTION, priority=9, aliases=["Rock"]),
        DrugKeyword("Opium", DrugActivityType.CONSUMPTION, priority=8),
        DrugKeyword("Amphetamine", DrugActivityType.CONSUMPTION, priority=7, aliases=["Speed", "Pep"]),
        DrugKeyword("Benzodiazepine", DrugActivityType.CONSUMPTION, priority=6, aliases=["Benzos"]),

        # DEALING
        DrugKeyword("Dealer", DrugActivityType.DEALING, priority=8, aliases=["Pusher", "Supplier"]),
        DrugKeyword("Verkaufen", DrugActivityType.DEALING, priority=8, aliases=["Sell", "Dealing"]),
        DrugKeyword("Gramm", DrugActivityType.DEALING, priority=7, context="Dosierungsangabe"),
        DrugKeyword("Kilo", DrugActivityType.DEALING, priority=8, context="Große Menge"),
        DrugKeyword("Lager", DrugActivityType.DEALING, priority=7, aliases=["Stash", "Vorrat"]),
        DrugKeyword("Kunde", DrugActivityType.DEALING, priority=6),

        # PRODUCTION
        DrugKeyword("Kochen", DrugActivityType.PRODUCTION, priority=8, context="Herstellung"),
        DrugKeyword("Mischen", DrugActivityType.PRODUCTION, priority=7),
        DrugKeyword("Labor", DrugActivityType.PRODUCTION, priority=8, aliases=["Lab"]),
        DrugKeyword("Rezept", DrugActivityType.PRODUCTION, priority=7),

        # EFFECTS
        DrugKeyword("High", DrugActivityType.EFFECTS, priority=7),
        DrugKeyword("Trip", DrugActivityType.EFFECTS, priority=7),
        DrugKeyword("Rausch", DrugActivityType.EFFECTS, priority=8),
        DrugKeyword("Abhängigkeit", DrugActivityType.EFFECTS, priority=7),

        # TOOLS
        DrugKeyword("Spritze", DrugActivityType.TOOLS, priority=8, aliases=["Needle"]),
        DrugKeyword("Pfeife", DrugActivityType.TOOLS, priority=6),
        DrugKeyword("Papier", DrugActivityType.TOOLS, priority=5, context="Für Joints"),

        # MONEY
        DrugKeyword("Preis", DrugActivityType.MONEY, priority=6),
        DrugKeyword("Bezahlung", DrugActivityType.MONEY, priority=7),
    ]

    @classmethod
    def get_all_keywords(cls) -> List[DrugKeyword]:
        """Gibt alle Keywords zurück."""
        return cls.KEYWORDS


def get_drug_keywords_profile():
    """Factory für Drug Keywords."""
    return {
        "profile_id": "drug_activity",
        "name": "Drogen-Aktivitäten",
        "keywords": [
            {
                "text": kw.keyword,
                "priority": kw.priority,
                "category": kw.activity_type.value,
                "aliases": kw.aliases,
            }
            for kw in DrugKeywordsLibrary.KEYWORDS
        ],
        "total_keywords": len(DrugKeywordsLibrary.KEYWORDS),
    }
