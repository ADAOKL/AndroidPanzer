"""KEYWORD DISPLAY: Zeige alle Keywords im Menü auf der rechten Seite!

Schönes 2-spalten Layout: Links Profil-Info, Rechts alle Keywords.
"""
from __future__ import annotations

from typing import List, Optional
from . import ui


class KeywordDisplay:
    """Professionelle Keyword-Anzeige mit Layout."""

    @staticmethod
    def show_profile_with_keywords(
        profile_name: str,
        profile_description: str,
        recording_mode: str,
        keywords: List[str],
        keyword_priorities: dict = None,
        total_keywords: int = None
    ) -> None:
        """Zeige Profil links, Keywords rechts."""
        ui.clear()

        # Terminal width anpassen
        term_width = 200
        left_width = 50
        right_width = 140

        # HEADER
        print(f"\n{ui.BOLD}{ui.BCYAN}{'═' * term_width}{ui.RESET}\n")
        print(f"  {ui.BOLD}▶️  KEYWORD-RECORDING STARTEN{ui.RESET}\n")
        print(f"{ui.BCYAN}{'═' * term_width}{ui.RESET}\n")

        # LINKE SEITE - PROFIL INFO
        print(f"{ui.BOLD}PROFIL-INFORMATION:{ui.RESET}\n")
        print(f"  📋 Name:          {profile_name}")
        if profile_description:
            print(f"  📝 Beschreibung:  {profile_description[:40]}...")
        print(f"  🎙️  Modus:         {recording_mode}")
        print(f"  📊 Keywords:      {total_keywords if total_keywords else len(keywords)}")
        print()

        # RECHTE SEITE - ALLE KEYWORDS
        if keywords:
            print(f"{ui.BOLD}KEYWORDS ({len(keywords)}):{ui.RESET}\n")

            # Spalten-Layout: 3 Spalten für bessere Nutzung
            col_width = 35
            cols = 3

            for i in range(0, len(keywords), cols):
                row_keywords = keywords[i:i+cols]

                # Baue Zeile
                line = "  "
                for j, kw in enumerate(row_keywords):
                    priority = ""
                    if keyword_priorities and kw in keyword_priorities:
                        pri = keyword_priorities[kw]
                        if pri >= 8:
                            priority = f" {ui.BRED}●{ui.RESET}"  # High priority
                        elif pri >= 6:
                            priority = f" {ui.BYELLOW}●{ui.RESET}"  # Medium
                        else:
                            priority = f" {ui.BGREEN}●{ui.RESET}"  # Low

                    # Kürzen wenn zu lang
                    kw_display = kw[:col_width-3] if len(kw) > col_width-3 else kw

                    line += f"{kw_display:<{col_width}}{priority}"

                print(line)

        print()
        print(f"{ui.BCYAN}{'═' * term_width}{ui.RESET}\n")

    @staticmethod
    def show_profile_grid(
        profile_name: str,
        keywords: List[str],
        keyword_info: dict = None
    ) -> None:
        """Zeige Profil als Gitter mit detaillierten Infos."""
        ui.clear()

        print(f"\n{ui.BOLD}{ui.BCYAN}🎙️  {profile_name}{ui.RESET}\n")
        print(f"{ui.BGREEN}{'─' * 200}{ui.RESET}\n")

        # Header
        col1_width = 30
        col2_width = 20
        col3_width = 25
        col4_width = 30

        print(f"  {ui.BOLD}{'KEYWORD':30} {'PRIORITY':20} {'KATEGORIE':25} {'ALIASES':30}{ui.RESET}")
        print(f"  {ui.BGREEN}{'─' * (col1_width + col2_width + col3_width + col4_width + 8)}{ui.RESET}\n")

        # Rows
        for i, keyword in enumerate(keywords[:30], 1):
            priority_str = ""
            category_str = ""
            aliases_str = ""

            if keyword_info and keyword in keyword_info:
                info = keyword_info[keyword]
                priority = info.get("priority", 5)

                # Priority visualization
                if priority >= 8:
                    priority_str = f"{ui.BRED}{'●' * priority}{ui.RESET} ({priority}/10)"
                elif priority >= 6:
                    priority_str = f"{ui.BYELLOW}{'●' * priority}{ui.RESET} ({priority}/10)"
                else:
                    priority_str = f"{ui.BGREEN}{'●' * priority}{ui.RESET} ({priority}/10)"

                category_str = info.get("category", "")[:23]
                aliases = info.get("aliases", [])
                aliases_str = ", ".join(aliases[:2]) if aliases else ""

            print(f"  {i:2d}. {keyword:<27} {priority_str:<20} {category_str:<25} {aliases_str:<30}")

        if len(keywords) > 30:
            print(f"\n  ... und {len(keywords) - 30} weitere Keywords\n")

        print(f"\n{ui.BGREEN}{'─' * 200}{ui.RESET}\n")

    @staticmethod
    def show_keyword_selector(keywords: List[str]) -> Optional[str]:
        """Wähle ein Keyword zum Bearbeiten."""
        ui.clear()

        print(f"\n{ui.BOLD}🎯 KEYWORD AUSWÄHLEN{ui.RESET}\n")

        # Zeige in 4 Spalten
        cols = 4
        col_width = 30

        for i in range(0, len(keywords), cols):
            row_keywords = keywords[i:i+cols]
            for j, kw in enumerate(row_keywords):
                idx = i + j + 1
                kw_display = kw[:col_width-5]
                print(f"  {idx:3d}. {kw_display:<{col_width-5}}", end="  ")
            print()

        print()
        choice = input(f"  {ui.BOLD}☠ ❯ Keyword-Nummer (1-{len(keywords)}, Q=zurück): {ui.RESET}").strip()

        if choice.upper() == "Q":
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(keywords):
                return keywords[idx]
        except ValueError:
            pass

        ui.warn("Ungültige Eingabe")
        return None

    @staticmethod
    def show_recording_ready(
        profile_name: str,
        keyword_count: int,
        recording_mode: str,
        duration_max_sec: int = 3600
    ) -> bool:
        """Zeige Recording-Bestätigungsscreen."""
        ui.clear()

        print(f"\n{ui.BOLD}{ui.BGREEN}▶️  RECORDING BEREIT{ui.RESET}\n")
        print(f"{ui.BGREEN}{'═' * 80}{ui.RESET}\n")

        print(f"  📋 Profil:              {profile_name}")
        print(f"  🎤 Keywords im Profil:  {keyword_count}")
        print(f"  🎙️  Recording-Modus:    {recording_mode}")
        print(f"  ⏱️  Max. Dauer:         {duration_max_sec}s ({duration_max_sec//60}m)")
        print()
        print(f"  {ui.BRED}WARNUNG:{ui.RESET} Audio-Daten werden aufgezeichnet!")
        print(f"  Alle erkannten Keywords werden gespeichert.")
        print()
        print(f"{ui.BGREEN}{'═' * 80}{ui.RESET}\n")

        answer = input(f"  {ui.BOLD}☠ ❯ Aufzeichnung starten? (j/N): {ui.RESET}").strip().upper()
        return answer == "J"

    @staticmethod
    def show_recording_progress(
        detected_count: int,
        elapsed_seconds: int,
        last_keywords: List[str] = None
    ) -> None:
        """Zeige Recording-Fortschritt."""
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60

        print(f"\r  ⏱️  Verbrauchte Zeit: {minutes:02d}:{seconds:02d} | Keywords erkannt: {detected_count}", end="")

        if last_keywords:
            print(f" | Letzte: {', '.join(last_keywords[-2:])}")
        else:
            print()

    @staticmethod
    def show_recording_summary(
        total_duration_sec: int,
        keywords_detected: int,
        recordings_saved: int,
        detected_keywords_list: List[tuple] = None
    ) -> None:
        """Zeige Recording-Zusammenfassung."""
        ui.clear()

        print(f"\n{ui.BOLD}{ui.BGREEN}✓ RECORDING ABGESCHLOSSEN{ui.RESET}\n")
        print(f"{ui.BGREEN}{'═' * 80}{ui.RESET}\n")

        minutes = total_duration_sec // 60
        seconds = total_duration_sec % 60

        print(f"  ⏱️  Gesamtdauer:        {minutes}m {seconds}s")
        print(f"  🎤 Keywords erkannt:   {keywords_detected}")
        print(f"  💾 Aufnahmen gespeichert: {recordings_saved}")
        print()

        if detected_keywords_list:
            print(f"  {ui.BOLD}ERKANNTE KEYWORDS:{ui.RESET}\n")
            for kw, count, last_time in detected_keywords_list[:15]:
                print(f"    • {kw:30} ({count}x, zuletzt: {last_time}s)")

            if len(detected_keywords_list) > 15:
                print(f"\n    ... und {len(detected_keywords_list) - 15} weitere")

        print()
        print(f"{ui.BGREEN}{'═' * 80}{ui.RESET}\n")
        ui.pause()


def create_keyword_display() -> KeywordDisplay:
    """Factory: Erstellt Keyword Display."""
    return KeywordDisplay()
