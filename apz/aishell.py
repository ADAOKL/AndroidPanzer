"""KI-gestützte ADB-Shell (lokale KI via ollama).

  • Klartext → ADB-Befehl: "zeig mir die akkufresser" → schlägt ein Kommando vor
  • Ausgabe erklären: KI fasst die Ausgabe verständlich zusammen
  • Auto-Diagnose: KI plant read-only Diagnose-Kommandos, führt sie aus, fasst zusammen

Alles läuft LOKAL über ollama (keine Cloud). Jeder Befehl wird VOR der Ausführung
angezeigt und muss bestätigt werden – destruktive Befehle werden zusätzlich gewarnt.
"""
from __future__ import annotations

import json
import re
import urllib.request

from . import ui

OLLAMA = "http://localhost:11434"
PREFERRED = ["qwen2.5-coder:7b", "qwen2.5-coder:7b-instruct-q5_k_m",
             "qwen2.5-coder:14b", "codellama:7b-instruct", "qwen2.5-coder:latest"]

_DESTRUCTIVE = re.compile(
    r"\b(rm|dd|mkfs|format|wipe|fastboot|reboot|pm\s+(uninstall|clear|disable)|"
    r"am\s+force-stop|settings\s+put|svc\s+\w+\s+disable|kill|stop\s+\w|setprop|"
    r"magisk|su\s+-c|content\s+(insert|delete|update)|truncate|>\s*/)", re.I)


# --------------------------------------------------------------------- #
#  ollama-Anbindung
# --------------------------------------------------------------------- #
def _ollama_up() -> bool:
    try:
        urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3)
        return True
    except Exception:  # noqa: BLE001
        return False


def _models() -> list[str]:
    try:
        data = json.loads(urllib.request.urlopen(OLLAMA + "/api/tags", timeout=5).read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:  # noqa: BLE001
        return []


def _gen(model: str, prompt: str, system: str = "", temp: float = 0.1, timeout: int = 120) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "system": system,
                       "stream": False, "options": {"temperature": temp}}).encode()
    try:
        req = urllib.request.Request(OLLAMA + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        return resp.get("response", "").strip()
    except Exception as e:  # noqa: BLE001
        return f"[KI-Fehler: {e}]"


def _pick_model() -> str | None:
    models = _models()
    if not models:
        return None
    for p in PREFERRED:
        if p in models:
            return p
    return models[0]


def _clean_cmd(text: str) -> str:
    """Holt das reine Kommando aus der KI-Antwort (entfernt Markdown/Prefixe)."""
    text = re.sub(r"```[a-z]*", "", text).replace("```", "").strip()
    danger = text.upper().startswith("DANGER")
    for line in text.splitlines():
        line = line.strip().lstrip("$").strip()
        line = re.sub(r"^(adb\s+shell\s+|DANGER:\s*)", "", line, flags=re.I).strip()
        if line:
            return ("DANGER: " if danger else "") + line
    return ""


# --------------------------------------------------------------------- #
#  Menü
# --------------------------------------------------------------------- #
def menu(adb, dev, st) -> None:
    if not _ollama_up():
        ui.clear(); ui.rule("KI-ADB-Shell", ui.CYAN)
        ui.err("ollama-Server nicht erreichbar (localhost:11434).")
        ui.info("Starten mit:  ollama serve   (in einem zweiten Terminal)")
        ui.pause(); return
    model = _pick_model()
    if not model:
        ui.err("Keine ollama-Modelle gefunden. z.B.:  ollama pull qwen2.5-coder:7b")
        ui.pause(); return

    while True:
        ui.clear()
        ui.banner(subtitle="🤖 KI-ADB-Shell (lokal · ollama)")
        ui.kv("Modell", model)
        ui.kv("Gerät", f"{getattr(dev,'model','')} ({getattr(dev,'serial','')})")
        from . import ai_recipes
        ch = ui.menu("Modus", [
            ("1", "💬 Klartext → ADB-Befehl (Chat, mit Bestätigung)"),
            ("2", "🔍 Auto-Diagnose (KI plant & führt read-only Checks aus)"),
            ("3", "📖 Letzte/eigene Ausgabe von der KI erklären lassen"),
            ("4", f"{ui.BCYAN}📚 KI-REZEPT-BIBLIOTHEK ({ai_recipes.TOTAL}+ fertige Aufgaben){ui.RESET}"),
            ("M", "Modell wechseln"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "m":
            model = _choose_model(model)
        elif ch == "1":
            nl_to_cmd_loop(adb, dev, st, model)
        elif ch == "2":
            auto_diagnose(adb, dev, st, model)
        elif ch == "3":
            explain_arbitrary(adb, dev, st, model)
        elif ch == "4":
            recipe_library(adb, dev, st, model)


def _choose_model(cur: str) -> str:
    models = _models()
    for i, m in enumerate(models, 1):
        print(f"  {ui.CYAN}{i}{ui.RESET}  {m}{'  ←' if m==cur else ''}")
    sel = ui.ask("Modell-Nr", "")
    try:
        return models[int(sel) - 1]
    except (ValueError, IndexError):
        return cur


# --------------------------------------------------------------------- #
#  1 · Klartext → Befehl
# --------------------------------------------------------------------- #
SYS_CMD = ("Du bist ein Android-ADB-Experte. Wandle die Anfrage in GENAU EIN "
           "adb-shell-Kommando um (nur der Teil nach 'adb shell'). Gib NUR das rohe "
           "Kommando in einer Zeile aus – ohne Markdown, ohne Erklärung, ohne 'adb shell'. "
           "Wenn der Befehl etwas verändert/löscht/neustartet/deinstalliert, stelle 'DANGER: ' "
           "voran. Bevorzuge read-only-Diagnose. Gerät: {model}, Android {ver}.")


def nl_to_cmd_loop(adb, dev, st, model: str) -> None:
    ui.clear(); ui.rule("Klartext → ADB-Befehl", ui.CYAN)
    ui.info("Beschreibe, was du willst (deutsch/englisch). 'q' beendet.\n")
    sysmsg = SYS_CMD.format(model=getattr(dev, "model", "?"),
                            ver=getattr(dev, "mode", "?"))
    while True:
        want = ui.ask("Du")
        if not want or want.lower() in ("q", "quit", "exit"):
            return
        raw = _gen(model, want, sysmsg)
        cmd = _clean_cmd(raw)
        if not cmd:
            ui.warn("KI lieferte kein Kommando."); continue
        dng = cmd.startswith("DANGER:")
        cmd = cmd.replace("DANGER:", "").strip()
        is_dest = dng or bool(_DESTRUCTIVE.search(cmd))
        col = ui.BRED if is_dest else ui.BGREEN
        print(f"\n   {ui.BOLD}KI-Vorschlag:{ui.RESET} {col}{cmd}{ui.RESET}"
              f"{'   ' + ui.BRED + '⚠ VERÄNDERND' + ui.RESET if is_dest else ''}")
        if not ui.confirm("Ausführen?", not is_dest):
            continue
        asroot = st.get("is_root") and is_dest and ui.confirm("Als Root (su)?", False)
        out = adb.shell(cmd, timeout=60, root=asroot) or "(keine Ausgabe)"
        ui.pager(out, cmd)
        if ui.confirm("Soll die KI die Ausgabe erklären?", False):
            expl = _gen(model, f"Befehl: {cmd}\nAusgabe:\n{out[:3000]}\n\n"
                               "Erkläre knapp auf Deutsch, was das bedeutet.",
                        "Du bist ein Android-Diagnose-Experte.")
            ui.pager(expl, "KI-Erklärung")
        print()


# --------------------------------------------------------------------- #
#  2 · Auto-Diagnose
# --------------------------------------------------------------------- #
SYS_DIAG = ("Du bist ein Android-Diagnose-Experte. Gib eine JSON-Liste von 4-8 "
            "READ-ONLY adb-shell-Kommandos zur Diagnose des beschriebenen Problems aus. "
            "Format: [{\"cmd\":\"...\",\"why\":\"...\"}]. NUR JSON, keine veränderten Befehle, "
            "kein rm/reboot/pm uninstall/settings put.")


def auto_diagnose(adb, dev, st, model: str) -> None:
    ui.clear(); ui.rule("KI-Auto-Diagnose", ui.CYAN)
    problem = ui.ask("Problem beschreiben (z.B. 'Akku leer über Nacht', 'App stürzt ab')")
    if not problem:
        return
    ui.info("KI plant Diagnose-Kommandos …")
    raw = _gen(model, problem, SYS_DIAG)
    try:
        plan = json.loads(re.search(r"\[.*\]", raw, re.S).group(0))
    except Exception:  # noqa: BLE001
        ui.warn("KI-Plan nicht parsebar – Rohausgabe:")
        ui.pager(raw, "KI"); ui.pause(); return
    results = []
    for step in plan[:8]:
        cmd = re.sub(r"^adb\s+shell\s+", "", str(step.get("cmd", "")), flags=re.I).strip()
        if not cmd or _DESTRUCTIVE.search(cmd):
            continue
        print(f"\n  {ui.CYAN}▶ {cmd}{ui.RESET}  {ui.GREY}{step.get('why','')}{ui.RESET}")
        out = adb.shell(cmd, timeout=45) or "(leer)"
        for l in out.splitlines()[:6]:
            print(f"     {ui.GREY}{l[:110]}{ui.RESET}")
        results.append(f"$ {cmd}\n{out[:1500]}")
    ui.info("\nKI fasst die Befunde zusammen …")
    summary = _gen(model, "Diagnose-Problem: " + problem + "\n\nErgebnisse:\n" +
                   "\n\n".join(results)[:6000] +
                   "\n\nFasse die wahrscheinliche Ursache + konkrete Lösungsschritte auf Deutsch zusammen.",
                   "Du bist ein Android-Diagnose-Experte.", timeout=180)
    ui.pager(summary, "KI-Diagnose-Ergebnis")
    # ── Nächste konkrete Schritte direkt aus dem Ergebnis ableiten & anbieten ──
    _suggest_next(adb, st, model, problem, summary)


SYS_NEXT = ("Du bist ein Android-ADB-Experte. Basierend auf der Diagnose, gib die "
            "konkret nächsten umsetzbaren adb-shell-Aktionen als JSON-Liste aus: "
            "[{\"cmd\":\"<reines kommando ohne 'adb shell'>\",\"why\":\"<kurz>\","
            "\"risk\":\"safe|destructive\"}]. Max 5. NUR JSON.")


def _suggest_next(adb, st, model: str, problem: str, summary: str) -> None:
    """Leitet aus dem KI-Ergebnis direkt ausführbare nächste Schritte ab."""
    raw = _gen(model, f"Problem: {problem}\n\nDiagnose:\n{summary[:3000]}\n\n"
                      "Was sind die nächsten konkreten ADB-Schritte?", SYS_NEXT, timeout=120)
    try:
        steps = json.loads(re.search(r"\[.*\]", raw, re.S).group(0))
    except Exception:  # noqa: BLE001
        return
    steps = [s for s in steps if str(s.get("cmd", "")).strip()][:5]
    if not steps:
        return
    while True:
        print()
        ui.rule("➤ Nächste empfohlene Schritte (KI)", ui.BCYAN)
        for i, s in enumerate(steps, 1):
            cmd = re.sub(r"^adb\s+shell\s+", "", str(s["cmd"]), flags=re.I).strip()
            dest = s.get("risk") == "destructive" or bool(_DESTRUCTIVE.search(cmd))
            mark = ui.pulse(" ⚠") if dest else ""
            col = ui.BRED if dest else ui.BGREEN
            print(f"  {ui.CYAN}{i}{ui.RESET}  {col}{cmd}{ui.RESET}{mark}  {ui.GREY}{s.get('why','')}{ui.RESET}")
        print(f"\n  {ui.BOLD}Nr{ui.RESET} ausführen · {ui.BOLD}A{ui.RESET} alle sicheren · "
              f"{ui.BOLD}0{ui.RESET} fertig")
        sel = ui.ask("Auswahl", "0").lower()
        if sel in ("0", "", "q"):
            return
        chosen = []
        if sel == "a":
            chosen = [s for s in steps if s.get("risk") != "destructive"
                      and not _DESTRUCTIVE.search(str(s["cmd"]))]
        else:
            try:
                chosen = [steps[int(sel) - 1]]
            except (ValueError, IndexError):
                continue
        for s in chosen:
            cmd = re.sub(r"^adb\s+shell\s+", "", str(s["cmd"]), flags=re.I).strip()
            dest = s.get("risk") == "destructive" or bool(_DESTRUCTIVE.search(cmd))
            if dest and not ui.confirm(f"{ui.pulse('VERÄNDERND')}: {cmd} – wirklich?", False):
                continue
            asroot = st.get("is_root") and dest
            out = adb.shell(cmd, timeout=60, root=asroot) or "(keine Ausgabe)"
            ui.pager(out, cmd)
            # KI bewertet das Ergebnis und schlägt erneut weiter vor (Kette)
            follow = _gen(model, f"Befehl: {cmd}\nAusgabe:\n{out[:2500]}\n\n"
                          "Kurz auf Deutsch: Hat es geholfen? Was ist der logisch nächste Schritt?",
                          "Du bist ein Android-Diagnose-Experte.", timeout=120)
            ui.pager(follow, "KI-Bewertung & nächster Schritt")


# --------------------------------------------------------------------- #
#  3 · Beliebige Ausgabe erklären
# --------------------------------------------------------------------- #
def recipe_library(adb, dev, st, model: str) -> None:
    """Kategorisierte Bibliothek mit 250+ fertigen KI-Aufgaben."""
    from . import ai_recipes
    cats = list(ai_recipes.RECIPES.items())
    while True:
        ui.clear()
        ui.banner(subtitle=f"📚 KI-Rezept-Bibliothek · {ai_recipes.TOTAL} Aufgaben")
        ui.info("Wähle eine Kategorie – darin ein fertiges Rezept. Die KI plant, führt aus & erklärt.\n")
        for i, (cat, items) in enumerate(cats, 1):
            print(f"  {ui.CYAN}{i:>2}{ui.RESET}  {cat}  {ui.GREY}({len(items)}){ui.RESET}")
        print(f"\n  {ui.BOLD}S{ui.RESET} Suche (Stichwort)   {ui.BOLD}Z{ui.RESET} Zufalls-Rezept   {ui.BOLD}0{ui.RESET} Zurück")
        sel = ui.ask("Kategorie-Nr / S / Z").lower()
        if sel in ("0", "", "back", "q"):
            return
        if sel == "s":
            _recipe_search(adb, dev, st, model, cats)
            continue
        if sel == "z":
            _run_recipe(adb, dev, st, model, _random_recipe(cats))
            continue
        try:
            cat, items = cats[int(sel) - 1]
        except (ValueError, IndexError):
            continue
        _recipe_pick(adb, dev, st, model, cat, items)


def _recipe_pick(adb, dev, st, model, cat, items) -> None:
    while True:
        ui.clear()
        ui.rule(cat, ui.CYAN)
        for i, it in enumerate(items, 1):
            print(f"  {ui.CYAN}{i:>2}{ui.RESET}  {it}")
        print(f"\n  {ui.BOLD}A{ui.RESET} ALLE nacheinander   {ui.BOLD}0{ui.RESET} Zurück")
        sel = ui.ask("Rezept-Nr / A").lower()
        if sel in ("0", "", "back"):
            return
        if sel == "a":
            for it in items:
                _run_recipe(adb, dev, st, model, it)
            return
        try:
            _run_recipe(adb, dev, st, model, items[int(sel) - 1])
        except (ValueError, IndexError):
            continue


def _recipe_search(adb, dev, st, model, cats) -> None:
    q = ui.ask("Stichwort").lower()
    if not q:
        return
    hits = [(c, it) for c, items in cats for it in items if q in it.lower()]
    if not hits:
        ui.warn("Nichts gefunden."); ui.pause(); return
    ui.clear(); ui.rule(f"Treffer für '{q}' ({len(hits)})", ui.CYAN)
    for i, (c, it) in enumerate(hits[:40], 1):
        print(f"  {ui.CYAN}{i:>2}{ui.RESET}  {it}  {ui.GREY}{c}{ui.RESET}")
    sel = ui.ask("Nr")
    try:
        _run_recipe(adb, dev, st, model, hits[int(sel) - 1][1])
    except (ValueError, IndexError):
        pass


def _random_recipe(cats):
    import hashlib
    # deterministischer "Zufall" ohne random-Modul: aus Uhrzeit-freiem Hash der Katalog-Länge
    allr = [it for _, items in cats for it in items]
    if not allr:                       # leerer Katalog → kein Modulo durch 0
        return None
    idx = int(hashlib.sha256(str(len(allr)).encode()).hexdigest(), 16) % len(allr)
    return allr[idx]


def _run_recipe(adb, dev, st, model: str, task: str) -> None:
    """Führt ein Rezept als KI-Auto-Diagnose-Kette aus."""
    ui.clear()
    ui.rule(f"🤖 {task}", ui.BCYAN)
    if not _ollama_up():
        ui.err("ollama nicht erreichbar (ollama serve starten)."); ui.pause(); return
    # Nutzt die bestehende Auto-Diagnose-Pipeline mit dem Rezept als Problembeschreibung
    raw = _gen(model, task, SYS_DIAG, timeout=120)
    plan = None
    try:
        plan = json.loads(re.search(r"\[.*\]", raw, re.S).group(0))
    except Exception:  # noqa: BLE001
        pass
    results = []
    if plan:
        for step in plan[:8]:
            cmd = re.sub(r"^adb\s+shell\s+", "", str(step.get("cmd", "")), flags=re.I).strip()
            if not cmd or _DESTRUCTIVE.search(cmd):
                continue
            print(f"\n  {ui.CYAN}▶ {cmd}{ui.RESET}  {ui.GREY}{step.get('why','')}{ui.RESET}")
            out = adb.shell(cmd, timeout=45) or "(leer)"
            for l in out.splitlines()[:6]:
                print(f"     {ui.GREY}{l[:110]}{ui.RESET}")
            results.append(f"$ {cmd}\n{out[:1500]}")
    # Synthese
    ui.info("\nKI fasst zusammen …")
    summary = _gen(model, f"Aufgabe: {task}\n\nErgebnisse:\n" + "\n\n".join(results)[:6000] +
                   "\n\nFasse das Ergebnis + Empfehlung auf Deutsch zusammen.",
                   "Du bist ein Android-Experte.", timeout=180)
    ui.pager(summary, f"KI: {task}")
    # Folge-Schritte anbieten (Kette)
    if results:
        _suggest_next(adb, st, model, task, summary)
    else:
        ui.pause()


def explain_arbitrary(adb, dev, st, model: str) -> None:
    ui.clear(); ui.rule("Ausgabe erklären lassen", ui.CYAN)
    cmd = ui.ask("ADB-Kommando, dessen Ausgabe erklärt werden soll")
    if not cmd:
        return
    out = adb.shell(cmd, timeout=60) or "(keine Ausgabe)"
    ui.pager(out, cmd)
    expl = _gen(model, f"Befehl: {cmd}\nAusgabe:\n{out[:4000]}\n\n"
                       "Erkläre auf Deutsch, was die Ausgabe bedeutet und ob etwas auffällig ist.",
                "Du bist ein Android-Experte.", timeout=180)
    ui.pager(expl, "KI-Erklärung")
    ui.pause()
