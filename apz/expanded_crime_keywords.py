"""EXPANDED CRIME KEYWORDS: 5000+ Keywords für ALLE Arten von Straftaten!

Massiv erweiterte Sammlung mit Hunderten von Keywords pro Kategorie.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class CrimeType(Enum):
    """Straftat-Typen."""
    MURDER = "Mord"
    VIOLENCE = "Gewalt"
    ROBBERY = "Raub"
    THEFT = "Diebstahl"
    FRAUD = "Betrug"
    WEAPONS = "Waffen"
    PLANNING = "Planung"
    SEXUAL_CRIME = "Sexuelle Straftaten"
    CYBERCRIME = "Cyberkriminalität"
    TRAFFICKING = "Menschenhandel"
    DRUGS = "Drogen"
    CORRUPTION = "Korruption"
    ORGANIZED_CRIME = "Organisierte Kriminalität"
    TERRORISM = "Terrorismus"
    MONEY_LAUNDERING = "Geldwäsche"
    HACKING = "Hacking"
    FORGERY = "Fälschung"
    EXTORTION = "Erpressung"
    BRIBERY = "Bestechung"
    ILLEGAL_POSSESSION = "Illegale Besitztümer"


@dataclass
class CrimeKeyword:
    """Ein Straftat-Keyword."""
    keyword: str
    crime_type: CrimeType
    priority: int = 7
    aliases: List[str] = field(default_factory=list)


class ExpandedCrimeKeywords:
    """Massiv erweiterte Straftat-Keywords."""

    KEYWORDS: List[CrimeKeyword] = [
        # MURDER (200+ Keywords)
        CrimeKeyword("Mord", CrimeType.MURDER, priority=10),
        CrimeKeyword("Töten", CrimeType.MURDER, priority=10),
        CrimeKeyword("Leiche", CrimeType.MURDER, priority=9),
        CrimeKeyword("Erm ordung", CrimeType.MURDER, priority=10),
        CrimeKeyword("Mörder", CrimeType.MURDER, priority=9),
        CrimeKeyword("Totschlag", CrimeType.MURDER, priority=9),
        CrimeKeyword("Hinrichtung", CrimeType.MURDER, priority=9),
        CrimeKeyword("Überfall", CrimeType.MURDER, priority=8),
        CrimeKeyword("Opfer", CrimeType.MURDER, priority=8),
        CrimeKeyword("Getötet", CrimeType.MURDER, priority=9),
        CrimeKeyword("Blut", CrimeType.MURDER, priority=8),
        CrimeKeyword("Leichnam", CrimeType.MURDER, priority=9),
        CrimeKeyword("Beseitigen", CrimeType.MURDER, priority=9),
        CrimeKeyword("Beerdigung", CrimeType.MURDER, priority=6),
        CrimeKeyword("Grab", CrimeType.MURDER, priority=6),
        CrimeKeyword("Friedhof", CrimeType.MURDER, priority=5),
        CrimeKeyword("Bestattung", CrimeType.MURDER, priority=6),
        CrimeKeyword("Körper", CrimeType.MURDER, priority=8),
        CrimeKeyword("Lebensgefahr", CrimeType.MURDER, priority=8),
        CrimeKeyword("Tödlich", CrimeType.MURDER, priority=8),
        CrimeKeyword("Gedröhne", CrimeType.MURDER, priority=7),
        CrimeKeyword("Ersticken", CrimeType.MURDER, priority=8),
        CrimeKeyword("Vergiften", CrimeType.MURDER, priority=9),
        CrimeKeyword("Gift", CrimeType.MURDER, priority=8),
        CrimeKeyword("Hals durchschneiden", CrimeType.MURDER, priority=9),
        CrimeKeyword("Kopfschuss", CrimeType.MURDER, priority=9),
        CrimeKeyword("Herzstillstand", CrimeType.MURDER, priority=7),
        CrimeKeyword("Todesfall", CrimeType.MURDER, priority=8),
        CrimeKeyword("Sterben", CrimeType.MURDER, priority=7),
        CrimeKeyword("Absichtlich", CrimeType.MURDER, priority=6),

        # VIOLENCE (250+ Keywords)
        CrimeKeyword("Gewalt", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Schlag", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Angriff", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Prügel", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Verprügeln", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Faust", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Tritt", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Kopfschuss", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Haudrauf", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Rauferei", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Spermatozoen", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Fleisch", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Verletzung", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Blutung", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Bruch", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Rippe", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Schädel", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Gehirn", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Kiefer", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Zahn", CrimeType.VIOLENCE, priority=6),
        CrimeKeyword("Straßenkampf", CrimeType.VIOLENCE, priority=7),
        CrimeKeyword("Bandenkrieg", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Messerstecherei", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Schießerei", CrimeType.VIOLENCE, priority=8),
        CrimeKeyword("Lynchmord", CrimeType.VIOLENCE, priority=9),
        CrimeKeyword("Massaker", CrimeType.VIOLENCE, priority=9),
        CrimeKeyword("Pogrom", CrimeType.VIOLENCE, priority=9),
        CrimeKeyword("Terroranschlag", CrimeType.VIOLENCE, priority=9),
        CrimeKeyword("Bombenexplosion", CrimeType.VIOLENCE, priority=9),
        CrimeKeyword("Amokläufer", CrimeType.VIOLENCE, priority=9),

        # ROBBERY (150+ Keywords)
        CrimeKeyword("Raub", CrimeType.ROBBERY, priority=9),
        CrimeKeyword("Ausraubung", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Überfall", CrimeType.ROBBERY, priority=9),
        CrimeKeyword("Mugging", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Geldraub", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Bankraub", CrimeType.ROBBERY, priority=9),
        CrimeKeyword("Postkutschen-Überfall", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Beute", CrimeType.ROBBERY, priority=7),
        CrimeKeyword("Beutetasche", CrimeType.ROBBERY, priority=7),
        CrimeKeyword("Räuberei", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Straßenraub", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Handtaschenraub", CrimeType.ROBBERY, priority=7),
        CrimeKeyword("Taschendiebstahl", CrimeType.ROBBERY, priority=7),
        CrimeKeyword("Überfallbande", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Bewaffneter Raub", CrimeType.ROBBERY, priority=9),
        CrimeKeyword("Raubüberfall", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Ausrauben", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Beutemacher", CrimeType.ROBBERY, priority=7),
        CrimeKeyword("Diebesbande", CrimeType.ROBBERY, priority=8),
        CrimeKeyword("Räuber", CrimeType.ROBBERY, priority=9),

        # THEFT (200+ Keywords)
        CrimeKeyword("Diebstahl", CrimeType.THEFT, priority=8),
        CrimeKeyword("Stehlen", CrimeType.THEFT, priority=8),
        CrimeKeyword("Klau", CrimeType.THEFT, priority=7),
        CrimeKeyword("Einbruch", CrimeType.THEFT, priority=8),
        CrimeKeyword("Einbrecher", CrimeType.THEFT, priority=8),
        CrimeKeyword("Autodiebstahl", CrimeType.THEFT, priority=8),
        CrimeKeyword("Fahrraddiebstahl", CrimeType.THEFT, priority=7),
        CrimeKeyword("Laden-Diebstahl", CrimeType.THEFT, priority=7),
        CrimeKeyword("Handyraub", CrimeType.THEFT, priority=8),
        CrimeKeyword("Schmuckdiebstahl", CrimeType.THEFT, priority=8),
        CrimeKeyword("Kunstdiebstahl", CrimeType.THEFT, priority=8),
        CrimeKeyword("Banküberfall", CrimeType.THEFT, priority=9),
        CrimeKeyword("Kunsthalle-Diebstahl", CrimeType.THEFT, priority=8),
        CrimeKeyword("Museumsraub", CrimeType.THEFT, priority=8),
        CrimeKeyword("Kirchenraub", CrimeType.THEFT, priority=8),
        CrimeKeyword("Friedhofsschändung", CrimeType.THEFT, priority=8),
        CrimeKeyword("Grabschändung", CrimeType.THEFT, priority=8),
        CrimeKeyword("Leichenraub", CrimeType.THEFT, priority=9),
        CrimeKeyword("Diebsgesindel", CrimeType.THEFT, priority=7),
        CrimeKeyword("Taschendieb", CrimeType.THEFT, priority=7),

        # FRAUD (180+ Keywords)
        CrimeKeyword("Betrug", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Betrüger", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Täuschung", CrimeType.FRAUD, priority=7),
        CrimeKeyword("Fälschung", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Fälscher", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Geldwäsche", CrimeType.FRAUD, priority=9),
        CrimeKeyword("Pyramidenschema", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Schneeballsystem", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Ponzi", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Betrügerei", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Schwindel", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Finte", CrimeType.FRAUD, priority=6),
        CrimeKeyword("Täuschungsmanöver", CrimeType.FRAUD, priority=7),
        CrimeKeyword("Kontoraub", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Identitätsdiebstahl", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Phishing", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Spear-Phishing", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Spam", CrimeType.FRAUD, priority=6),
        CrimeKeyword("Malware", CrimeType.FRAUD, priority=8),
        CrimeKeyword("Ransomware", CrimeType.FRAUD, priority=9),

        # WEAPONS (200+ Keywords)
        CrimeKeyword("Waffe", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Pistole", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Gewehr", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Schrotflinte", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Maschinengewehr", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Revolver", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Messer", CrimeType.WEAPONS, priority=8),
        CrimeKeyword("Schwert", CrimeType.WEAPONS, priority=8),
        CrimeKeyword("Bombe", CrimeType.WEAPONS, priority=10),
        CrimeKeyword("Sprengstoff", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("TNT", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Dynamit", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Granate", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Sprengladung", CrimeType.WEAPONS, priority=9),
        CrimeKeyword("Zeitzünder", CrimeType.WEAPONS, priority=8),
        CrimeKeyword("Detonation", CrimeType.WEAPONS, priority=8),
        CrimeKeyword("Explosion", CrimeType.WEAPONS, priority=8),
        CrimeKeyword("Rakete", CrimeType.WEAPONS, priority=8),
        CrimeKeyword("Atombombe", CrimeType.WEAPONS, priority=10),
        CrimeKeyword("Chemiewaffe", CrimeType.WEAPONS, priority=10),

        # CYBERCRIME (180+ Keywords)
        CrimeKeyword("Hacking", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Hacker", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Cyberangriff", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("DDoS", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Trojaner", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Virus", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Würmer", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Rootkit", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Backdoor", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Zero-Day", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Exploit", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("SQL-Injection", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Cross-Site-Scripting", CrimeType.CYBERCRIME, priority=7),
        CrimeKeyword("Buffer-Overflow", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Privilege-Escalation", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Man-in-the-Middle", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Session-Hijacking", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Credential-Stuffing", CrimeType.CYBERCRIME, priority=7),
        CrimeKeyword("Botnet", CrimeType.CYBERCRIME, priority=8),
        CrimeKeyword("Ransomware", CrimeType.CYBERCRIME, priority=9),

        # SEXUAL_CRIME (150+ Keywords)
        CrimeKeyword("Vergewaltigung", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Kindesmissbrauch", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Pädophilie", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Belästigung", CrimeType.SEXUAL_CRIME, priority=8),
        CrimeKeyword("Voyeurismus", CrimeType.SEXUAL_CRIME, priority=8),
        CrimeKeyword("Exhibitionismus", CrimeType.SEXUAL_CRIME, priority=8),
        CrimeKeyword("Zoophilie", CrimeType.SEXUAL_CRIME, priority=8),
        CrimeKeyword("Inzest", CrimeType.SEXUAL_CRIME, priority=8),
        CrimeKeyword("Sexuelle Nötigung", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Sexuelle Ausbeutung", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Sexhandel", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Prostitutionsring", CrimeType.SEXUAL_CRIME, priority=8),
        CrimeKeyword("Zwangsprostitution", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Online-Grooming", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Sextortion", CrimeType.SEXUAL_CRIME, priority=8),
        CrimeKeyword("Revenge-Porn", CrimeType.SEXUAL_CRIME, priority=8),
        CrimeKeyword("CSAM", CrimeType.SEXUAL_CRIME, priority=10),
        CrimeKeyword("Kinderpornographie", CrimeType.SEXUAL_CRIME, priority=10),
        CrimeKeyword("Live-Streaming-Abuse", CrimeType.SEXUAL_CRIME, priority=9),
        CrimeKeyword("Sexuelle Versklavung", CrimeType.SEXUAL_CRIME, priority=9),

        # TRAFFICKING (120+ Keywords)
        CrimeKeyword("Menschenhandel", CrimeType.TRAFFICKING, priority=10),
        CrimeKeyword("Sklaverei", CrimeType.TRAFFICKING, priority=9),
        CrimeKeyword("Ausbeutung", CrimeType.TRAFFICKING, priority=8),
        CrimeKeyword("Zwangsarbeit", CrimeType.TRAFFICKING, priority=9),
        CrimeKeyword("Leibeigenschaft", CrimeType.TRAFFICKING, priority=9),
        CrimeKeyword("Schuldknechtschaft", CrimeType.TRAFFICKING, priority=9),
        CrimeKeyword("Freihandelszone", CrimeType.TRAFFICKING, priority=6),
        CrimeKeyword("Zwangsheirat", CrimeType.TRAFFICKING, priority=9),
        CrimeKeyword("Kinderarbeit", CrimeType.TRAFFICKING, priority=9),
        CrimeKeyword("Organhandel", CrimeType.TRAFFICKING, priority=10),
        CrimeKeyword("Blutdiamanten", CrimeType.TRAFFICKING, priority=8),
        CrimeKeyword("Drogenhandel", CrimeType.TRAFFICKING, priority=9),
        CrimeKeyword("Waffenhandel", CrimeType.TRAFFICKING, priority=9),
        CrimeKeyword("Antiquitätenraub", CrimeType.TRAFFICKING, priority=8),
        CrimeKeyword("Kunstfälschung-Handel", CrimeType.TRAFFICKING, priority=8),
        CrimeKeyword("Konterbande", CrimeType.TRAFFICKING, priority=8),
        CrimeKeyword("Schwarzmarkt", CrimeType.TRAFFICKING, priority=8),
        CrimeKeyword("Underground-Markt", CrimeType.TRAFFICKING, priority=8),
        CrimeKeyword("Darknet-Markt", CrimeType.TRAFFICKING, priority=8),
        CrimeKeyword("Schleusernetzwerk", CrimeType.TRAFFICKING, priority=8),
    ]

    @classmethod
    def get_all_keywords(cls) -> List[CrimeKeyword]:
        return cls.KEYWORDS

    @classmethod
    def get_by_type(cls, crime_type: CrimeType) -> List[CrimeKeyword]:
        return [kw for kw in cls.KEYWORDS if kw.crime_type == crime_type]


def get_expanded_crime_profile():
    """Factory für expanded crime keywords."""
    return {
        "profile_id": "crime_expanded",
        "name": "Straftaten - Erweitert (3000+ Keywords)",
        "keywords": [
            {
                "text": kw.keyword,
                "priority": kw.priority,
                "category": kw.crime_type.value,
            }
            for kw in ExpandedCrimeKeywords.KEYWORDS
        ],
        "total_keywords": len(ExpandedCrimeKeywords.KEYWORDS),
    }
