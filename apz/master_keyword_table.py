"""MASTER KEYWORD TABLE: Sortierte Tabelle mit ALLEN Keywords!

Zeigt ALLE Keywords von ALLEN Profilen in einer organisierten Tabelle.
"""
from __future__ import annotations

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from . import ui
from .sexual_keywords_profile import SexualKeywordsLibrary
from .drug_keywords_profile import DrugKeywordsLibrary
from .crime_keywords_profile import CrimeKeywordsLibrary


@dataclass
class KeywordEntry:
    """Ein Keyword-Eintrag."""
    keyword: str
    category: str
    profile: str
    priority: int
    aliases: List[str]
    context: str = ""

    def priority_indicator(self) -> str:
        """Priority als visueller Indikator."""
        if self.priority >= 9:
            return f"{ui.BRED}●●●{ui.RESET}"
        elif self.priority >= 7:
            return f"{ui.BYELLOW}●●{ui.RESET}"
        else:
            return f"{ui.BGREEN}●{ui.RESET}"


class MasterKeywordTable:
    """Master-Tabelle mit allen Keywords."""

    def __init__(self):
        """Initialisiere Master Table."""
        self.keywords: List[KeywordEntry] = []
        self._load_all_keywords()

    def _load_all_keywords(self) -> None:
        """Lade alle Keywords von allen Profilen."""
        # Sexual Keywords
        for kw in SexualKeywordsLibrary.KEYWORDS:
            self.keywords.append(KeywordEntry(
                keyword=kw.keyword,
                category=kw.activity_type.value,
                profile="Sexual Activity",
                priority=kw.priority,
                aliases=kw.aliases,
                context=kw.context
            ))

        # Drug Keywords
        for kw in DrugKeywordsLibrary.KEYWORDS:
            self.keywords.append(KeywordEntry(
                keyword=kw.keyword,
                category=kw.activity_type.value,
                profile="Drogen-Aktivitäten",
                priority=kw.priority,
                aliases=kw.aliases,
                context=kw.context
            ))

        # Crime Keywords
        for kw in CrimeKeywordsLibrary.KEYWORDS:
            self.keywords.append(KeywordEntry(
                keyword=kw.keyword,
                category=kw.crime_type.value,
                profile="Straftaten",
                priority=kw.priority,
                aliases=kw.aliases,
                context=kw.context
            ))

    def show_full_table(self, sort_by: str = "priority") -> None:
        """Zeige komplette sortierte Tabelle."""
        ui.clear()
        ui.banner(subtitle=f"📋 MASTER KEYWORD TABELLE - ALLE {len(self.keywords)} KEYWORDS")
        print()

        # Sortiere
        if sort_by == "priority":
            sorted_kws = sorted(self.keywords, key=lambda k: (-k.priority, k.keyword))
        elif sort_by == "profile":
            sorted_kws = sorted(self.keywords, key=lambda k: (k.profile, -k.priority, k.keyword))
        elif sort_by == "category":
            sorted_kws = sorted(self.keywords, key=lambda k: (k.category, -k.priority, k.keyword))
        else:
            sorted_kws = sorted(self.keywords, key=lambda k: k.keyword)

        # Header
        print(f"{ui.BOLD}")
        print(f"{'#':4} {'KEYWORD':25} {'KATEGORIE':20} {'PROFIL':20} {'PRIO':10} {'ALIASES':30}")
        print(f"{ui.BGREEN}{'─' * 135}{ui.RESET}\n")

        # Rows
        for i, kw in enumerate(sorted_kws, 1):
            aliases_str = ", ".join(kw.aliases[:2]) if kw.aliases else "-"
            priority_ind = kw.priority_indicator()

            print(f"{i:3d}. {kw.keyword:<25} {kw.category:<20} {kw.profile:<20} {kw.priority:1d}/10 {priority_ind:<10} {aliases_str:<30}")

        print()
        print(f"{ui.BGREEN}{'─' * 135}{ui.RESET}\n")

    def show_by_profile(self) -> None:
        """Zeige Keywords gruppiert nach Profil."""
        ui.clear()
        ui.banner(subtitle="📋 KEYWORDS NACH PROFIL GRUPPIERT")
        print()

        # Gruppiere nach Profil
        by_profile: Dict[str, List[KeywordEntry]] = {}
        for kw in self.keywords:
            if kw.profile not in by_profile:
                by_profile[kw.profile] = []
            by_profile[kw.profile].append(kw)

        # Zeige jedes Profil
        for profile_name in sorted(by_profile.keys()):
            kws = sorted(by_profile[profile_name], key=lambda k: (-k.priority, k.keyword))

            print(f"{ui.BOLD}{ui.BCYAN}{'=' * 140}{ui.RESET}")
            print(f"{ui.BOLD}📋 {profile_name} ({len(kws)} Keywords){ui.RESET}\n")

            # Header
            print(f"  {'#':3} {'KEYWORD':25} {'KATEGORIE':20} {'PRIO':8} {'ALIASES':40}")
            print(f"  {ui.BGREEN}{'─' * 135}{ui.RESET}\n")

            # Rows
            for idx, kw in enumerate(kws, 1):
                aliases_str = ", ".join(kw.aliases[:2]) if kw.aliases else "-"
                priority_ind = kw.priority_indicator()

                print(f"  {idx:2d}. {kw.keyword:<25} {kw.category:<20} {kw.priority:1d}/10 {priority_ind:<8} {aliases_str:<40}")

            print()

    def show_by_category(self) -> None:
        """Zeige Keywords gruppiert nach Kategorie."""
        ui.clear()
        ui.banner(subtitle="📋 KEYWORDS NACH KATEGORIE GRUPPIERT")
        print()

        # Gruppiere nach Kategorie
        by_category: Dict[str, List[KeywordEntry]] = {}
        for kw in self.keywords:
            if kw.category not in by_category:
                by_category[kw.category] = []
            by_category[kw.category].append(kw)

        # Zeige jede Kategorie
        for category_name in sorted(by_category.keys()):
            kws = sorted(by_category[category_name], key=lambda k: (-k.priority, k.keyword))

            print(f"{ui.BOLD}{ui.BGREEN}{'=' * 140}{ui.RESET}")
            print(f"{ui.BOLD}🎯 {category_name} ({len(kws)} Keywords){ui.RESET}\n")

            # Header
            print(f"  {'#':3} {'KEYWORD':25} {'PROFIL':20} {'PRIO':8} {'ALIASES':40}")
            print(f"  {ui.BGREEN}{'─' * 135}{ui.RESET}\n")

            # Rows
            for idx, kw in enumerate(kws, 1):
                aliases_str = ", ".join(kw.aliases[:2]) if kw.aliases else "-"
                priority_ind = kw.priority_indicator()

                print(f"  {idx:2d}. {kw.keyword:<25} {kw.profile:<20} {kw.priority:1d}/10 {priority_ind:<8} {aliases_str:<40}")

            print()

    def show_high_priority_only(self) -> None:
        """Zeige nur High-Priority Keywords (8+)."""
        ui.clear()
        ui.banner(subtitle="📋 HIGH-PRIORITY KEYWORDS (Priorität >= 8)")
        print()

        high_priority = sorted(
            [kw for kw in self.keywords if kw.priority >= 8],
            key=lambda k: (-k.priority, k.keyword)
        )

        print(f"{ui.BOLD}")
        print(f"{'#':4} {'KEYWORD':25} {'KATEGORIE':20} {'PROFIL':20} {'PRIO':8}")
        print(f"{ui.BRED}{'─' * 100}{ui.RESET}\n")

        for i, kw in enumerate(high_priority, 1):
            priority_ind = kw.priority_indicator()
            print(f"{i:3d}. {kw.keyword:<25} {kw.category:<20} {kw.profile:<20} {priority_ind}")

        print()
        print(f"{ui.BRED}{'─' * 100}{ui.RESET}\n")
        print(f"Insgesamt: {len(high_priority)}/{len(self.keywords)} High-Priority Keywords")
        print()

    def search_keyword(self, search_term: str) -> None:
        """Suche nach Keyword."""
        ui.clear()
        ui.banner(subtitle=f"🔍 SUCHE: {search_term}")
        print()

        results = [
            kw for kw in self.keywords
            if search_term.lower() in kw.keyword.lower() or
               any(search_term.lower() in alias.lower() for alias in kw.aliases)
        ]

        if not results:
            ui.warn(f"Keine Keywords gefunden für: {search_term}")
            ui.pause()
            return

        results = sorted(results, key=lambda k: (-k.priority, k.keyword))

        print(f"Gefunden: {len(results)} Keywords\n")
        print(f"{ui.BOLD}")
        print(f"{'#':3} {'KEYWORD':25} {'KATEGORIE':20} {'PROFIL':20} {'PRIO':8} {'ALIASES':40}")
        print(f"{ui.BGREEN}{'─' * 140}{ui.RESET}\n")

        for i, kw in enumerate(results, 1):
            aliases_str = ", ".join(kw.aliases[:2]) if kw.aliases else "-"
            priority_ind = kw.priority_indicator()
            print(f"{i:2d}. {kw.keyword:<25} {kw.category:<20} {kw.profile:<20} {kw.priority:1d}/10 {priority_ind:<8} {aliases_str:<40}")

        print()
        ui.pause()

    def show_statistics(self) -> None:
        """Zeige Statistiken."""
        ui.clear()
        ui.banner(subtitle="📊 KEYWORD STATISTIKEN")
        print()

        # Count by profile
        by_profile = {}
        for kw in self.keywords:
            by_profile[kw.profile] = by_profile.get(kw.profile, 0) + 1

        # Count by category
        by_category = {}
        for kw in self.keywords:
            by_category[kw.category] = by_category.get(kw.category, 0) + 1

        # Count by priority
        by_priority = {}
        for kw in self.keywords:
            by_priority[kw.priority] = by_priority.get(kw.priority, 0) + 1

        print(f"{ui.BOLD}GESAMT-STATISTIK:{ui.RESET}\n")
        print(f"  Gesamte Keywords:   {len(self.keywords)}")
        print(f"  Einzigartige Profile:  {len(by_profile)}")
        print(f"  Einzigartige Kategorien: {len(by_category)}\n")

        print(f"{ui.BOLD}NACH PROFIL:{ui.RESET}\n")
        for profile in sorted(by_profile.keys()):
            count = by_profile[profile]
            print(f"  • {profile:<30} {count:3d} Keywords")

        print()
        print(f"{ui.BOLD}NACH PRIORITÄT:{ui.RESET}\n")
        for priority in sorted(by_priority.keys(), reverse=True):
            count = by_priority[priority]
            bar = "●" * priority
            print(f"  {priority}/10: {bar:<10} {count:3d} Keywords")

        print()


def create_master_keyword_table() -> MasterKeywordTable:
    """Factory: Erstellt Master Keyword Table."""
    return MasterKeywordTable()
