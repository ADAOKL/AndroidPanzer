"""KEYWORD AUTOCOMPLETE: Intelligente Vorschläge beim Hinzufügen von Keywords!"""
from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass

from . import ui


@dataclass
class Keyword:
    """Ein Keyword mit Metadaten."""
    name: str
    category: str
    priority: int
    frequency: int = 0  # Wie oft wurde es benutzt


class KeywordAutoComplete:
    """Intelligente Keyword-Vorschläge."""

    # Vordefinierte Keywords aus allen Profilen
    AVAILABLE_KEYWORDS: Dict[str, List[Keyword]] = {
        "SEXUEL": [
            Keyword("Stöhnen männlich", "M. Laute", 9, 45),
            Keyword("Stöhnen weiblich", "W. Laute", 9, 52),
            Keyword("Lustschrei", "W. Laute", 9, 38),
            Keyword("Orgasmus", "Orgasmus", 10, 120),
            Keyword("Rhythmische Bewegung", "Rhythmus", 8, 35),
            Keyword("Atemzüge", "Atmung", 7, 28),
            Keyword("Beddruckung", "Möbel", 6, 15),
            Keyword("Schmiergeräusche", "Schmier", 7, 22),
            Keyword("Flüstern", "Leise", 6, 18),
            Keyword("Penetration", "Eindringen", 9, 65),
        ],
        "DROGEN": [
            Keyword("Kokain", "Konsum", 9, 42),
            Keyword("Heroin", "Konsum", 10, 58),
            Keyword("Cannabis", "Konsum", 8, 35),
            Keyword("MDMA", "Konsum", 8, 22),
            Keyword("Methamphetamin", "Konsum", 9, 48),
            Keyword("LSD", "Konsum", 7, 18),
            Keyword("Crack", "Konsum", 9, 52),
            Keyword("Drogenhandel", "Dealing", 9, 38),
            Keyword("Kurier", "Dealing", 8, 25),
            Keyword("Drogenlabor", "Herstellung", 10, 40),
        ],
        "STRAFTATEN": [
            Keyword("Mord", "Gewalt", 10, 95),
            Keyword("Körperverletzung", "Gewalt", 9, 68),
            Keyword("Raub", "Eigentumsdelikte", 9, 55),
            Keyword("Diebstahl", "Eigentumsdelikte", 8, 42),
            Keyword("Betrug", "Wirtschaft", 8, 38),
            Keyword("Entführung", "Gewalt", 10, 72),
            Keyword("Bombe", "Waffen", 10, 88),
            Keyword("Schusswaffe", "Waffen", 9, 65),
            Keyword("Messer", "Waffen", 8, 35),
            Keyword("Sprengstoff", "Waffen", 10, 92),
        ],
        "ALLGEMEIN": [
            Keyword("Verdächtig", "Verhalten", 6, 28),
            Keyword("Geheim", "Sicherheit", 7, 32),
            Keyword("Versteckt", "Sicherheit", 7, 25),
            Keyword("Anonymität", "Sicherheit", 6, 18),
            Keyword("VPN", "Technologie", 5, 12),
            Keyword("Verschlüsselung", "Technologie", 6, 22),
        ],
    }

    @classmethod
    def get_suggestions(cls, profile: str, partial_input: str = "") -> List[Keyword]:
        """Gebe Vorschläge für ein Profil."""
        keywords = cls.AVAILABLE_KEYWORDS.get(profile, [])

        if not partial_input:
            # Sortiere nach Häufigkeit (meistgenutzte zuerst)
            return sorted(keywords, key=lambda k: k.frequency, reverse=True)

        # Filtere und sortiere
        filtered = [k for k in keywords if partial_input.lower() in k.name.lower()]
        return sorted(filtered, key=lambda k: k.frequency, reverse=True)

    @classmethod
    def show_suggestions(cls, profile: str, partial_input: str = "") -> Keyword:
        """Zeige interaktive Vorschläge und lasse wählen."""
        suggestions = cls.get_suggestions(profile, partial_input)

        if not suggestions:
            ui.warn(f"Keine Vorschläge für '{partial_input}' gefunden")
            return None

        ui.clear()
        ui.rule(f"💡 KEYWORD-VORSCHLÄGE - {profile}", ui.BCYAN)
        print()

        print(f"  Eingabe: '{partial_input}'\n")
        print(f"  {ui.BOLD}VERFÜGBARE KEYWORDS:{ui.RESET}\n")

        for i, kw in enumerate(suggestions, 1):
            priority_bar = "●" * kw.priority
            usage = f"({kw.frequency}x verwendet)"
            print(f"  {i:2d}. {kw.name:35} [{kw.category:20}] {priority_bar:10} {usage}")

        print()
        print(f"  0. Neues Keyword eingeben")
        print(f"  Q. Abbrechen")
        print()

        choice = ui.ask("Auswahl", "0")

        if choice.upper() == "Q":
            return None
        if choice == "0":
            new_name = ui.ask("Neues Keyword eingeben", "")
            return Keyword(new_name, "Custom", 5, 0) if new_name else None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                return suggestions[idx]
        except ValueError:
            pass

        return None

    @classmethod
    def add_custom_keyword(cls, profile: str, keyword: Keyword) -> bool:
        """Füge benutzerdefiniertes Keyword hinzu."""
        if profile not in cls.AVAILABLE_KEYWORDS:
            cls.AVAILABLE_KEYWORDS[profile] = []

        cls.AVAILABLE_KEYWORDS[profile].append(keyword)
        return True


def create_autocomplete() -> KeywordAutoComplete:
    """Factory: Erstellt KeywordAutoComplete."""
    return KeywordAutoComplete()
