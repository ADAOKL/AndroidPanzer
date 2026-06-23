"""PORNOGRAPHY AUDIO DETECTOR: Erkennung von Porno-Audio, leise Sexgeräusche, etc!

Detektiert Pornographische Inhalte durch Audio-Patterns, nicht nur laute sondern auch
leise, subtile Sexgeräusche die im Hintergrund ablaufen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class PornAudioType(Enum):
    """Typ von Pornographische Audio."""
    LOUD_MOANING = "Lautes Stöhnen"
    WHISPER_MOANING = "Flüstern-Stöhnen (leise)"
    ORGASM_SOUNDS = "Orgasmus-Geräusche"
    HEAVY_BREATHING = "Schweres Atmen"
    LIGHT_BREATHING = "Leichte Atmung (subtil)"
    RHYTHMIC_SOUNDS = "Rhythmische Geräusche"
    PAIN_PLEASURE = "Schmerz/Lust-Laute"
    PENETRATION = "Penetrations-Geräusche"
    BACKGROUND_PORNO = "Porno im Hintergrund"
    VIDEO_AUDIO = "Porno-Video-Audio"
    PHONE_SEX = "Telefonsex-Geräusche"
    DIRTY_TALK = "Dirty Talk"
    COMMAND_OBEY = "Befehls-Gehorchungs-Laute"
    DOMINANCE = "Dominanz-Laute"
    SUBMISSION = "Unterwerfungs-Laute"


@dataclass
class PornAudioPattern:
    """Ein Pornographisches Audio-Pattern."""
    name: str
    audio_type: PornAudioType
    priority: int = 8
    frequency_range: str = ""
    confidence: float = 0.70
    aliases: List[str] = field(default_factory=list)
    volume_db: int = 0  # dB - 0=normal, -20=very quiet/whisper
    context: str = ""


class PornographyAudioDetector:
    """Porno-Audio Detektor."""

    PATTERNS: List[PornAudioPattern] = [
        # LOUD MOANING
        PornAudioPattern(
            name="Lautes Frauenstöhnen",
            audio_type=PornAudioType.LOUD_MOANING,
            priority=9,
            frequency_range="200-1000 Hz",
            volume_db=0,
            context="Durchgehend während Penetration"
        ),
        PornAudioPattern(
            name="Lautes Männerstöhnen",
            audio_type=PornAudioType.LOUD_MOANING,
            priority=9,
            frequency_range="80-400 Hz",
            volume_db=0,
            context="Kurzatmig, rhythmisch"
        ),

        # WHISPER MOANING (LEISE!)
        PornAudioPattern(
            name="Flüstern-Stöhnen Frau",
            audio_type=PornAudioType.WHISPER_MOANING,
            priority=8,
            frequency_range="300-1500 Hz",
            volume_db=-20,
            context="Leises, subtiles Stöhnen"
        ),
        PornAudioPattern(
            name="Flüstern-Stöhnen Mann",
            audio_type=PornAudioType.WHISPER_MOANING,
            priority=8,
            frequency_range="100-500 Hz",
            volume_db=-18,
            context="Gedämpftes Stöhnen"
        ),
        PornAudioPattern(
            name="Leises Ächzen",
            audio_type=PornAudioType.WHISPER_MOANING,
            priority=7,
            frequency_range="200-800 Hz",
            volume_db=-15,
            context="Subtile, kaum hörbare Laute"
        ),

        # ORGASM SOUNDS
        PornAudioPattern(
            name="Weiblicher Orgasmus",
            audio_type=PornAudioType.ORGASM_SOUNDS,
            priority=9,
            frequency_range="300-2000 Hz",
            volume_db=5,
            aliases=["female climax", "female peak"],
            context="Intensive Steigerung, dann abrupt abfallend"
        ),
        PornAudioPattern(
            name="Männlicher Orgasmus",
            audio_type=PornAudioType.ORGASM_SOUNDS,
            priority=9,
            frequency_range="100-600 Hz",
            volume_db=3,
            aliases=["male climax", "male ejaculation"],
            context="Finales Stöhnen mit Atem-Unterbrechung"
        ),
        PornAudioPattern(
            name="Leiser Orgasmus",
            audio_type=PornAudioType.ORGASM_SOUNDS,
            priority=8,
            frequency_range="100-1500 Hz",
            volume_db=-10,
            context="Unterdrückter/unterdrückter Orgasmus"
        ),

        # BREATHING
        PornAudioPattern(
            name="Schweres Atmen (Frau)",
            audio_type=PornAudioType.HEAVY_BREATHING,
            priority=8,
            frequency_range="200-3000 Hz",
            volume_db=0,
            context="Schnelles, lautes Atmen"
        ),
        PornAudioPattern(
            name="Schweres Atmen (Mann)",
            audio_type=PornAudioType.HEAVY_BREATHING,
            priority=8,
            frequency_range="100-1500 Hz",
            volume_db=-2,
            context="Angestrengtes, schnelles Atmen"
        ),
        PornAudioPattern(
            name="Leichte Atmung (Frau)",
            audio_type=PornAudioType.LIGHT_BREATHING,
            priority=7,
            frequency_range="300-2000 Hz",
            volume_db=-20,
            context="Subtiles Atmen im Hintergrund"
        ),
        PornAudioPattern(
            name="Leichte Atmung (Mann)",
            audio_type=PornAudioType.LIGHT_BREATHING,
            priority=7,
            frequency_range="100-500 Hz",
            volume_db=-18,
            context="Gedämpftes, kaum hörbares Atmen"
        ),

        # RHYTHMIC SOUNDS
        PornAudioPattern(
            name="Rhythmisches Stoßen",
            audio_type=PornAudioType.RHYTHMIC_SOUNDS,
            priority=8,
            frequency_range="20-100 Hz",
            volume_db=-5,
            context="Regelmäßiger Rhythmus, beschleunigend"
        ),
        PornAudioPattern(
            name="Stöße variierender Intensität",
            audio_type=PornAudioType.RHYTHMIC_SOUNDS,
            priority=7,
            frequency_range="15-80 Hz",
            volume_db=-8,
            context="Wechselnde Geschwindigkeiten"
        ),

        # PENETRATION SOUNDS
        PornAudioPattern(
            name="Penetrations-Geräusche",
            audio_type=PornAudioType.PENETRATION,
            priority=9,
            frequency_range="500-3000 Hz",
            volume_db=-5,
            aliases=["wet sounds", "squelch", "Schmier-Geräusche"],
            context="Feuchte, schlürfende Geräusche"
        ),
        PornAudioPattern(
            name="Leise Penetrations-Geräusche",
            audio_type=PornAudioType.PENETRATION,
            priority=8,
            frequency_range="300-2000 Hz",
            volume_db=-18,
            context="Subtile, kaum hörbbare Geräusche"
        ),

        # BACKGROUND PORNO
        PornAudioPattern(
            name="Porno im Hintergrund (Frau)",
            audio_type=PornAudioType.BACKGROUND_PORNO,
            priority=7,
            frequency_range="100-2000 Hz",
            volume_db=-15,
            context="Porno läuft als Hintergrund-Audio"
        ),
        PornAudioPattern(
            name="Porno im Hintergrund (Mann)",
            audio_type=PornAudioType.BACKGROUND_PORNO,
            priority=7,
            frequency_range="80-800 Hz",
            volume_db=-16,
            context="Pornographische Laute im Hintergrund"
        ),
        PornAudioPattern(
            name="Porno-Video-Audio",
            audio_type=PornAudioType.VIDEO_AUDIO,
            priority=8,
            frequency_range="50-3000 Hz",
            volume_db=-3,
            context="Mehrere Stimmen, Musik im Hintergrund"
        ),

        # DIRTY TALK
        PornAudioPattern(
            name="Dirty Talk (Frau)",
            audio_type=PornAudioType.DIRTY_TALK,
            priority=7,
            frequency_range="200-1500 Hz",
            volume_db=-5,
            aliases=["explicit language", "sex talk"],
            context="Sexuelle Verbalisierung"
        ),
        PornAudioPattern(
            name="Dirty Talk (Mann)",
            audio_type=PornAudioType.DIRTY_TALK,
            priority=7,
            frequency_range="100-800 Hz",
            volume_db=-3,
            context="Erotische Befehle/Vokalisierung"
        ),

        # COMMAND/OBEY
        PornAudioPattern(
            name="Dominanz-Befehle",
            audio_type=PornAudioType.COMMAND_OBEY,
            priority=8,
            frequency_range="100-500 Hz",
            volume_db=0,
            context="Befehle während sex"
        ),
        PornAudioPattern(
            name="Unterwerfung/Gehorsam",
            audio_type=PornAudioType.SUBMISSION,
            priority=7,
            frequency_range="200-1000 Hz",
            volume_db=-5,
            context="Bestätigung/Gehorchens-Laute"
        ),

        # PHONE SEX
        PornAudioPattern(
            name="Telefonsex (Frau)",
            audio_type=PornAudioType.PHONE_SEX,
            priority=7,
            frequency_range="200-1500 Hz",
            volume_db=-8,
            context="Einzelne Stimme, sexuelle Laute"
        ),
        PornAudioPattern(
            name="Telefonsex (Mann)",
            audio_type=PornAudioType.PHONE_SEX,
            priority=7,
            frequency_range="100-800 Hz",
            volume_db=-6,
            context="Einzelne Stimme, lustvolle Laute"
        ),

        # PAIN/PLEASURE HYBRIDS
        PornAudioPattern(
            name="Schmerz-Lust Laute",
            audio_type=PornAudioType.PAIN_PLEASURE,
            priority=8,
            frequency_range="150-1500 Hz",
            volume_db=-3,
            context="Gemischte Schmerzlust-Signale"
        ),
    ]

    @classmethod
    def get_all_patterns(cls) -> List[PornAudioPattern]:
        """Alle Patterns."""
        return cls.PATTERNS

    @classmethod
    def get_by_type(cls, audio_type: PornAudioType) -> List[PornAudioPattern]:
        """Nach Typ filtern."""
        return [p for p in cls.PATTERNS if p.audio_type == audio_type]

    @classmethod
    def get_quiet_patterns(cls) -> List[PornAudioPattern]:
        """Nur leise Patterns (<-10dB)."""
        return [p for p in cls.PATTERNS if p.volume_db < -10]

    @classmethod
    def get_background_only(cls) -> List[PornAudioPattern]:
        """Nur Hintergrund-Porno Patterns."""
        return [
            p for p in cls.PATTERNS
            if p.audio_type in [
                PornAudioType.BACKGROUND_PORNO,
                PornAudioType.VIDEO_AUDIO,
                PornAudioType.WHISPER_MOANING,
                PornAudioType.LIGHT_BREATHING,
            ]
        ]


def get_porn_audio_profile():
    """Porno-Audio Profil für Keyword Recorder."""
    return {
        "profile_id": "porn_audio",
        "name": "Pornographische Audio-Inhalte",
        "description": "Erkennung von Porno-Audio (laut & leise, inkl. Hintergrund)",
        "keywords": [
            {
                "text": pattern.name,
                "priority": pattern.priority,
                "category": pattern.audio_type.value,
                "volume_db": pattern.volume_db,
                "frequency_range": pattern.frequency_range,
                "confidence": pattern.confidence,
            }
            for pattern in PornographyAudioDetector.PATTERNS
        ],
        "total_keywords": len(PornographyAudioDetector.PATTERNS),
        "stats": {
            "quiet_patterns": len(PornographyAudioDetector.get_quiet_patterns()),
            "background_only": len(PornographyAudioDetector.get_background_only()),
            "high_priority": len([p for p in PornographyAudioDetector.PATTERNS if p.priority >= 8]),
        }
    }
