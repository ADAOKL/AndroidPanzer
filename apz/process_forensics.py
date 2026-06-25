"""PROCESS FORENSICS: 50-Tool Profi-Konsole für verdächtige Prozesse.

Wird von rootkit.py aufgerufen wenn ein Injection-/Spyware-Prozess gefunden wird.
Stellt 50 forensische Werkzeuge in 7 Kategorien bereit.
"""
from __future__ import annotations

import re
import subprocess
import time
from shlex import quote as shq
from typing import TYPE_CHECKING

from . import ui

if TYPE_CHECKING:
    from .adb import ADB


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sh(adb: "ADB", cmd: str, timeout: int = 10) -> str:
    try:
        return adb.shell(cmd, timeout=timeout).strip()
    except Exception:
        return ""

def _head(text: str, n: int = 30) -> str:
    lines = text.splitlines()
    if len(lines) > n:
        return "\n".join(lines[:n]) + f"\n  {ui.GREY}… {len(lines)-n} weitere Zeilen{ui.RESET}"
    return text

def _show(title: str, text: str, color: str = ui.CYAN) -> None:
    ui.rule(title, color)
    if text.strip():
        for line in text.splitlines()[:40]:
            print(f"  {line}")
    else:
        print(f"  {ui.GREY}(keine Ausgabe){ui.RESET}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  A · PROZESS-IDENTITÄT  (1–10)
# ══════════════════════════════════════════════════════════════════════════════

def t01_prozessinfo(adb, pid, pkg):
    _show("1 · Vollständige Prozess-Info", _sh(adb,
        f"cat /proc/{pid}/status 2>/dev/null; "
        f"echo '---'; ls -la /proc/{pid}/exe 2>/dev/null; "
        f"echo 'SELinux:'; cat /proc/{pid}/attr/current 2>/dev/null"))

def t02_cmdline(adb, pid, pkg):
    raw = _sh(adb, f"cat /proc/{pid}/cmdline 2>/dev/null | tr '\\0' ' '")
    _show("2 · Kommandozeile", raw or _sh(adb, f"ps -p {pid} -o cmd 2>/dev/null"))

def t03_environment(adb, pid, pkg):
    _show("3 · Umgebungsvariablen", _sh(adb,
        f"cat /proc/{pid}/environ 2>/dev/null | tr '\\0' '\\n' | grep -v '^$'"))

def t04_workdir(adb, pid, pkg):
    _show("4 · Arbeitsverzeichnis + Startzeit",
          _sh(adb, f"ls -la /proc/{pid}/cwd 2>/dev/null; "
                   f"stat /proc/{pid} 2>/dev/null | grep -E 'Access|Modify'"))

def t05_open_fds(adb, pid, pkg):
    _show("5 · Offene File Descriptors (Anzahl + Typen)",
          _sh(adb, f"ls -la /proc/{pid}/fd 2>/dev/null | head -50; "
                   f"echo; echo 'Anzahl FDs:'; ls /proc/{pid}/fd 2>/dev/null | wc -l"))

def t06_libraries(adb, pid, pkg):
    _show("6 · Geladene Bibliotheken",
          _sh(adb, f"grep '\\.so' /proc/{pid}/maps 2>/dev/null | awk '{{print $6}}' | sort -u"))

def t07_threads(adb, pid, pkg):
    _show("7 · Alle Threads",
          _sh(adb, f"ls /proc/{pid}/task 2>/dev/null | xargs -I{{}} sh -c "
                   f"'echo -n \"TID {{}}: \"; cat /proc/{pid}/task/{{}}/status 2>/dev/null | grep Name'"))

def t08_capabilities(adb, pid, pkg):
    raw = _sh(adb, f"cat /proc/{pid}/status 2>/dev/null | grep -E 'Cap'")
    _show("8 · Linux Capabilities", raw)
    # Dekodiere CapEff
    for line in raw.splitlines():
        if "CapEff" in line:
            try:
                val = int(line.split(":")[1].strip(), 16)
                caps = []
                cap_names = {0:"CHOWN",1:"DAC_OVERRIDE",2:"DAC_READ",3:"FOWNER",
                             4:"FSETID",5:"KILL",6:"SETGID",7:"SETUID",8:"SETPCAP",
                             9:"LINUX_IMMUTABLE",10:"NET_BIND",11:"NET_BROADCAST",
                             12:"NET_ADMIN",13:"NET_RAW",14:"IPC_LOCK",21:"SYS_ADMIN",
                             22:"SYS_BOOT",27:"MKNOD",38:"CAP_AUDIT_WRITE"}
                for bit, name in cap_names.items():
                    if val & (1 << bit):
                        caps.append(name)
                if caps:
                    print(f"  {ui.BYELLOW}Aktive Caps: {', '.join(caps)}{ui.RESET}")
            except Exception:
                pass

def t09_namespaces(adb, pid, pkg):
    _show("9 · Namespace-Info",
          _sh(adb, f"ls -la /proc/{pid}/ns/ 2>/dev/null"))

def t10_cgroups(adb, pid, pkg):
    _show("10 · Cgroups-Zugehörigkeit",
          _sh(adb, f"cat /proc/{pid}/cgroup 2>/dev/null"))


# ══════════════════════════════════════════════════════════════════════════════
#  B · MEMORY FORENSICS  (11–18)
# ══════════════════════════════════════════════════════════════════════════════

def t11_memory_map(adb, pid, pkg):
    _show("11 · Vollständige Memory-Map",
          _sh(adb, f"cat /proc/{pid}/maps 2>/dev/null", timeout=15))

def t12_memory_usage(adb, pid, pkg):
    _show("12 · Speichernutzung (VSS/RSS/PSS/USS)",
          _sh(adb, f"cat /proc/{pid}/smaps_rollup 2>/dev/null || "
                   f"cat /proc/{pid}/status 2>/dev/null | grep -E 'VmRSS|VmSize|VmPeak|VmStk'"))

def t13_stack_region(adb, pid, pkg):
    _show("13 · Stack-Region",
          _sh(adb, f"grep '\\[stack\\]' /proc/{pid}/maps 2>/dev/null"))

def t14_heap_region(adb, pid, pkg):
    _show("14 · Heap-Region analysieren",
          _sh(adb, f"grep '\\[heap\\]' /proc/{pid}/maps 2>/dev/null; "
                   f"cat /proc/{pid}/smaps 2>/dev/null | grep -A6 'heap'"))

def t15_anonymous_mem(adb, pid, pkg):
    txt = _sh(adb, f"grep -E 'rwxp|r-xp' /proc/{pid}/maps 2>/dev/null | grep -v '\\.so\\|/system\\|/apex\\|/oat'")
    _show("15 · Anonyme RWX-Memory (Shellcode-Verdacht)", txt, ui.BRED if txt.strip() else ui.CYAN)
    if txt.strip():
        print(f"  {ui.BRED}⚠ Anonyme ausführbare Speicherbereiche gefunden!{ui.RESET}")

def t16_mapped_files(adb, pid, pkg):
    _show("16 · Memory-mapped Files",
          _sh(adb, f"grep -v '^$' /proc/{pid}/maps 2>/dev/null | awk '{{print $6}}' | grep '/' | sort -u"))

def t17_shared_memory(adb, pid, pkg):
    _show("17 · Shared Memory (ashmem/memfd)",
          _sh(adb, f"grep -E 'ashmem|memfd|/dev/shm' /proc/{pid}/maps 2>/dev/null"))

def t18_memory_dump(adb, pid, pkg):
    ui.rule("18 · Memory-Dump (ausgewählter Range)", ui.BRED)
    maps = _sh(adb, f"grep 'rw-p' /proc/{pid}/maps 2>/dev/null | head -10")
    if not maps.strip():
        print(f"  {ui.GREY}Keine rw-Bereiche gefunden{ui.RESET}")
        ui.pause(); return
    print(f"  {ui.BOLD}Verfügbare rw-Regionen:{ui.RESET}")
    regions = []
    for i, line in enumerate(maps.splitlines()[:10]):
        parts = line.split()
        if parts:
            print(f"  {ui.CYAN}{i+1}{ui.RESET}  {line[:80]}")
            regions.append(parts[0])
    print()
    choice = ui.ask("Region Nr für Dump (0=Abbrechen)", "0")
    if choice == "0" or not choice.isdigit():
        return
    idx = int(choice) - 1
    if 0 <= idx < len(regions):
        start, end = regions[idx].split("-")
        start_int = int(start, 16)
        size = int(end, 16) - start_int
        dump_path = f"/sdcard/memdump_{pid}_{start}.bin"
        print(f"  {ui.GREY}Dumpe {size//1024} KB nach {dump_path} …{ui.RESET}")
        out = _sh(adb, f"dd if=/proc/{pid}/mem bs=4096 skip={start_int//4096} count={size//4096} of={dump_path} 2>&1", timeout=30)
        if out:
            print(f"  {out}")
        ui.ok(f"Dump: {dump_path}  ({size//1024} KB)")
    ui.pause()


# ══════════════════════════════════════════════════════════════════════════════
#  C · NETZWERK & SOCKETS  (19–25)
# ══════════════════════════════════════════════════════════════════════════════

def t19_network_connections(adb, pid, pkg):
    _show("19 · TCP/UDP-Verbindungen des Prozesses",
          _sh(adb, f"cat /proc/{pid}/net/tcp /proc/{pid}/net/tcp6 "
                   f"/proc/{pid}/net/udp /proc/{pid}/net/udp6 2>/dev/null | head -30; "
                   f"ss -tnup 2>/dev/null | grep {pid}"))

def t20_unix_sockets(adb, pid, pkg):
    _show("20 · Unix Domain Sockets",
          _sh(adb, f"cat /proc/{pid}/net/unix 2>/dev/null | head -20"))

def t21_dns_sniff(adb, pid, pkg):
    ui.rule("21 · DNS-Anfragen live (10 Sekunden)", ui.CYAN)
    ui.info("Sniffe DNS-Traffic für 10s (tcpdump erforderlich)…")
    out = _sh(adb, "tcpdump -i any -n port 53 -c 20 2>&1", timeout=15)
    _show("DNS-Pakete", out)

def t22_geoip(adb, pid, pkg):
    ui.rule("22 · Remote-IPs geolocaten", ui.CYAN)
    conns = _sh(adb, f"ss -tnp 2>/dev/null | grep {pid}")
    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', conns)
    ips = [ip for ip in set(ips) if not ip.startswith(('127.','10.','192.168.','172.'))]
    if not ips:
        print(f"  {ui.GREY}Keine externen IPs aktiv{ui.RESET}")
    for ip in ips[:10]:
        try:
            r = subprocess.run(["curl","-s",f"https://ipapi.co/{ip}/json/"],
                               capture_output=True, text=True, timeout=5)
            import json
            d = json.loads(r.stdout)
            print(f"  {ui.BRED}{ip}{ui.RESET}  {d.get('country_name','')}  {d.get('city','')}  AS: {d.get('org','')}")
        except Exception:
            print(f"  {ip}  (Geo-Lookup fehlgeschlagen)")
    print()

def t23_traffic_volume(adb, pid, pkg):
    _show("23 · Traffic-Volumen des Prozesses",
          _sh(adb, f"cat /proc/{pid}/net/dev 2>/dev/null; "
                   f"cat /proc/net/xt_qtaguid/stats 2>/dev/null | grep '{pid}' | head -10"))

def t24_open_ports(adb, pid, pkg):
    _show("24 · Offene Ports (LISTEN)",
          _sh(adb, f"ss -tlnp 2>/dev/null | grep {pid}; "
                   f"netstat -tlnp 2>/dev/null | grep {pid}"))

def t25_tls_certs(adb, pid, pkg):
    _show("25 · TLS-Verbindungen + Zertifikate",
          _sh(adb, f"openssl s_client -connect 127.0.0.1:443 2>/dev/null | head -20; "
                   f"ss -tnp state established 2>/dev/null | grep {pid}"))


# ══════════════════════════════════════════════════════════════════════════════
#  D · DATEI & I/O  (26–33)
# ══════════════════════════════════════════════════════════════════════════════

def t26_fd_detail(adb, pid, pkg):
    _show("26 · Open FDs Detail (Dateien/Sockets/Pipes)",
          _sh(adb, f"ls -la /proc/{pid}/fd 2>/dev/null"))

def t27_file_access(adb, pid, pkg):
    _show("27 · Kürzliche Dateizugriffe (via lsof)",
          _sh(adb, f"lsof -p {pid} 2>/dev/null | head -40"))

def t28_db_access(adb, pid, pkg):
    _show("28 · SQLite-Datenbank-Zugriffe",
          _sh(adb, f"ls -la /proc/{pid}/fd 2>/dev/null | grep -E '\\.db|\\.sqlite'"))

def t29_shared_prefs(adb, pid, pkg):
    if pkg:
        _show("29 · Shared Preferences",
              _sh(adb, f"ls /data/data/{shq(pkg)}/shared_prefs/ 2>/dev/null"))
    else:
        print(f"  {ui.GREY}Kein Package bekannt{ui.RESET}")

def t30_external_storage(adb, pid, pkg):
    _show("30 · Externe Storage-Zugriffe",
          _sh(adb, f"ls -la /proc/{pid}/fd 2>/dev/null | grep -E 'sdcard|storage|Download|DCIM'"))

def t31_audio_video_fds(adb, pid, pkg):
    _show("31 · Kamera/Mikrofon/Audio File Descriptors",
          _sh(adb, f"ls -la /proc/{pid}/fd 2>/dev/null | grep -E 'video|audio|camera|media|v4l'"))

def t32_inotify(adb, pid, pkg):
    _show("32 · inotify-Watches (überwachte Dateipfade)",
          _sh(adb, f"cat /proc/{pid}/fdinfo/* 2>/dev/null | grep inotify | head -20"))

def t33_pipes(adb, pid, pkg):
    _show("33 · Pipe-Verbindungen zu anderen Prozessen",
          _sh(adb, f"ls -la /proc/{pid}/fd 2>/dev/null | grep pipe"))


# ══════════════════════════════════════════════════════════════════════════════
#  E · SYSCALLS & VERHALTEN  (34–40)
# ══════════════════════════════════════════════════════════════════════════════

def t34_strace(adb, pid, pkg):
    ui.rule("34 · Live Syscall-Trace (5 Sek., strace)", ui.BRED)
    ui.info("Tracen für 5 Sekunden…")
    out = _sh(adb, f"strace -p {pid} -c 2>&1 &sleep 5;kill %1 2>/dev/null", timeout=10)
    _show("Syscall-Zusammenfassung", out, ui.BRED)

def t35_binder(adb, pid, pkg):
    _show("35 · Binder-Transaktionen",
          _sh(adb, f"cat /sys/kernel/debug/binder/proc/{pid} 2>/dev/null || "
                   f"dumpsys binder 2>/dev/null | grep -A5 'pid={pid}'"))

def t36_logcat(adb, pid, pkg):
    _show("36 · Logcat-Einträge (letzter 200 Zeilen, nur dieser Prozess)",
          _sh(adb, f"logcat -d --pid={pid} -v time 2>/dev/null | tail -200", timeout=15))

def t37_wakelocks(adb, pid, pkg):
    _show("37 · Wake-Locks / Battery-Nutzung",
          _sh(adb, f"dumpsys batterystats 2>/dev/null | grep -i '{pkg or pid}' | head -20"))

def t38_cpu_history(adb, pid, pkg):
    ui.rule("38 · CPU-Verlauf (5 Messungen à 1s)", ui.CYAN)
    for i in range(5):
        val = _sh(adb, f"cat /proc/{pid}/stat 2>/dev/null | awk '{{print \"utime=\"$14\" stime=\"$15}}'")
        print(f"  {i+1}/5  {val}")
        time.sleep(1)
    print()

def t39_alarms(adb, pid, pkg):
    _show("39 · AlarmManager-Einträge",
          _sh(adb, f"dumpsys alarm 2>/dev/null | grep -A2 '{pkg or pid}' | head -30"))

def t40_jobscheduler(adb, pid, pkg):
    _show("40 · JobScheduler-Aufgaben",
          _sh(adb, f"dumpsys jobscheduler 2>/dev/null | grep -A5 '{pkg or pid}' | head -30"))


# ══════════════════════════════════════════════════════════════════════════════
#  F · APK & BINARY  (41–47)
# ══════════════════════════════════════════════════════════════════════════════

def t41_apk_signature(adb, pid, pkg):
    if not pkg:
        print(f"  {ui.GREY}Kein Package bekannt{ui.RESET}"); return
    _show("41 · APK-Signatur",
          _sh(adb, f"pm dump {shq(pkg)} 2>/dev/null | grep -A10 'Signatures'"))

def t42_permissions_full(adb, pid, pkg):
    if not pkg:
        print(f"  {ui.GREY}Kein Package bekannt{ui.RESET}"); return
    _show("42 · Berechtigungen vollständig",
          _sh(adb, f"dumpsys package {shq(pkg)} 2>/dev/null | grep 'permission' | head -50"))

def t43_dangerous_perms(adb, pid, pkg):
    if not pkg:
        print(f"  {ui.GREY}Kein Package bekannt{ui.RESET}"); return
    DANGEROUS = ["READ_SMS","SEND_SMS","RECORD_AUDIO","CAMERA","ACCESS_FINE_LOCATION",
                 "READ_CONTACTS","READ_CALL_LOG","PROCESS_OUTGOING_CALLS",
                 "READ_PHONE_STATE","RECEIVE_SMS","SYSTEM_ALERT_WINDOW",
                 "ACCESSIBILITY_SERVICE","DEVICE_ADMIN","BIND_NOTIFICATION"]
    raw = _sh(adb, f"dumpsys package {shq(pkg)} 2>/dev/null | grep 'granted=true'")
    ui.rule("43 · Gefährliche Berechtigungen", ui.BRED)
    found = [p for p in DANGEROUS if p in raw]
    if found:
        for p in found:
            print(f"  {ui.BRED}⚑ {p}{ui.RESET}")
    else:
        ui.ok("Keine gefährlichen Berechtigungen gefunden")
    print()

def t44_manifest(adb, pid, pkg):
    if not pkg:
        print(f"  {ui.GREY}Kein Package bekannt{u.RESET}"); return
    _show("44 · AndroidManifest (Auszug)",
          _sh(adb, f"aapt dump xmltree $(pm path {shq(pkg)} | cut -d: -f2) AndroidManifest.xml 2>/dev/null | head -60"))

def t45_native_libs(adb, pid, pkg):
    if not pkg:
        print(f"  {ui.GREY}Kein Package bekannt{ui.RESET}"); return
    _show("45 · Native Libraries",
          _sh(adb, f"ls -la /data/app/*{pkg}*/lib/ 2>/dev/null; "
                   f"grep '\\.so' /proc/{pid}/maps 2>/dev/null | grep -v '/system\\|/apex\\|/oat' | awk '{{print $6}}' | sort -u"))

def t46_strings_binary(adb, pid, pkg):
    ui.rule("46 · Strings aus Binary (sensible Patterns)", ui.CYAN)
    exe = _sh(adb, f"ls -la /proc/{pid}/exe 2>/dev/null")
    exe_path = re.search(r'-> (.+)', exe)
    if exe_path:
        path = exe_path.group(1).strip()
        out = _sh(adb,
            f"strings {shq(path)} 2>/dev/null | grep -iE "
            f"'password|passwd|token|secret|key|api_key|bearer|auth|cred|privat|encrypt' | head -30",
            timeout=20)
        _show(f"Sensible Strings in {path}", out, ui.BRED if out.strip() else ui.CYAN)
    else:
        print(f"  {ui.GREY}Binary-Pfad nicht ermittelbar{ui.RESET}")

def t47_hash_virustotal(adb, pid, pkg):
    ui.rule("47 · SHA256-Hash (VirusTotal-Check)", ui.CYAN)
    exe = _sh(adb, f"ls -la /proc/{pid}/exe 2>/dev/null")
    exe_path = re.search(r'-> (.+)', exe)
    if exe_path:
        path = exe_path.group(1).strip()
        h = _sh(adb, f"sha256sum {shq(path)} 2>/dev/null")
        print(f"  Pfad:  {path}")
        print(f"  SHA256: {h}")
        if h:
            sha = h.split()[0]
            print(f"\n  {ui.CYAN}VirusTotal:{ui.RESET}")
            print(f"  https://www.virustotal.com/gui/file/{sha}")
    else:
        print(f"  {ui.GREY}Pfad nicht ermittelbar{ui.RESET}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  G · PERSISTENZ & KONTROLLE  (48–50)
# ══════════════════════════════════════════════════════════════════════════════

def t48_autostart(adb, pid, pkg):
    _show("48 · Autostart-Einträge",
          _sh(adb, f"dumpsys package {shq(pkg or '')} 2>/dev/null | grep -E 'BOOT_COMPLETED|receiver' | head -20"))

def t49_device_admin(adb, pid, pkg):
    ui.rule("49 · DeviceAdmin-Status + DEAKTIVIEREN", ui.BRED)
    admins = _sh(adb, "dumpsys device_policy 2>/dev/null | grep -E 'admin=|ComponentInfo'")
    if not admins.strip():
        ui.ok("Keine aktiven Device-Admins")
    else:
        print(admins)
        if pkg and pkg in admins:
            print()
            if ui.confirm(f"Device-Admin für {pkg} DEAKTIVIEREN?", False):
                out = _sh(adb, f"dpm remove-active-admin {shq(pkg)}/$(dumpsys device_policy 2>/dev/null | grep {shq(pkg)} | grep -o 'ComponentInfo{{[^}}]*}}' | head -1 | tr -d '{{}}' | cut -d/ -f2) 2>&1")
                ui.ok(f"Deaktiviert: {out[:80]}")
    print()

def t50_accessibility_kill(adb, pid, pkg):
    ui.rule("50 · Accessibility-Service + KILL", ui.BRED)
    accs = _sh(adb, "settings get secure enabled_accessibility_services")
    print(f"  Aktive Accessibility-Services:\n  {accs}\n")
    if pkg and pkg in accs:
        print(f"  {ui.BRED}⚑ {pkg} ist als Accessibility-Service registriert!{ui.RESET}")
        print()
        if ui.confirm(f"Accessibility für {pkg} DEAKTIVIEREN + Prozess BEENDEN?", False):
            new_list = ":".join([s for s in accs.split(":") if pkg not in s])
            _sh(adb, f"settings put secure enabled_accessibility_services {shq(new_list)}")
            _sh(adb, f"am force-stop {shq(pkg)}")
            ui.ok(f"{pkg} deaktiviert + beendet")
    else:
        ui.ok("Prozess NICHT als Accessibility-Service registriert")
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  HAUPT-DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════

_TOOLS = {
    1: ("Vollständige Prozess-Info",            t01_prozessinfo),
    2: ("Kommandozeile",                         t02_cmdline),
    3: ("Umgebungsvariablen",                    t03_environment),
    4: ("Arbeitsverzeichnis + Startzeit",        t04_workdir),
    5: ("Offene File Descriptors",               t05_open_fds),
    6: ("Geladene Bibliotheken",                 t06_libraries),
    7: ("Alle Threads",                          t07_threads),
    8: ("Linux Capabilities",                    t08_capabilities),
    9: ("Namespace-Info",                        t09_namespaces),
   10: ("Cgroups-Zugehörigkeit",                 t10_cgroups),
   11: ("Memory-Map vollständig",                t11_memory_map),
   12: ("Speichernutzung VSS/RSS/PSS",           t12_memory_usage),
   13: ("Stack-Region",                          t13_stack_region),
   14: ("Heap-Region analysieren",               t14_heap_region),
   15: ("Anonyme RWX-Memory (Shellcode?)",       t15_anonymous_mem),
   16: ("Memory-mapped Files",                   t16_mapped_files),
   17: ("Shared Memory (ashmem/memfd)",          t17_shared_memory),
   18: ("Memory-Dump (ausgewählter Range)",      t18_memory_dump),
   19: ("TCP/UDP-Verbindungen",                  t19_network_connections),
   20: ("Unix Domain Sockets",                   t20_unix_sockets),
   21: ("DNS-Anfragen live (10s)",               t21_dns_sniff),
   22: ("Remote-IPs geolocaten",                 t22_geoip),
   23: ("Traffic-Volumen",                       t23_traffic_volume),
   24: ("Offene Ports (LISTEN)",                 t24_open_ports),
   25: ("TLS-Verbindungen + Zertifikate",        t25_tls_certs),
   26: ("Open FDs Detail",                       t26_fd_detail),
   27: ("Kürzliche Dateizugriffe (lsof)",        t27_file_access),
   28: ("SQLite-Datenbankzugriffe",              t28_db_access),
   29: ("Shared Preferences",                    t29_shared_prefs),
   30: ("Externe Storage-Zugriffe",              t30_external_storage),
   31: ("Kamera/Mikrofon-FDs",                   t31_audio_video_fds),
   32: ("inotify-Watches",                       t32_inotify),
   33: ("Pipe-Verbindungen",                     t33_pipes),
   34: ("Live Syscall-Trace (strace, 5s)",       t34_strace),
   35: ("Binder-Transaktionen",                  t35_binder),
   36: ("Logcat (nur dieser Prozess)",           t36_logcat),
   37: ("Wake-Locks / Battery",                  t37_wakelocks),
   38: ("CPU-Verlauf (5 Messungen)",             t38_cpu_history),
   39: ("AlarmManager-Einträge",                 t39_alarms),
   40: ("JobScheduler-Aufgaben",                 t40_jobscheduler),
   41: ("APK-Signatur",                          t41_apk_signature),
   42: ("Berechtigungen vollständig",            t42_permissions_full),
   43: ("Gefährliche Berechtigungen",            t43_dangerous_perms),
   44: ("Manifest analysieren",                  t44_manifest),
   45: ("Native Libraries",                      t45_native_libs),
   46: ("Strings aus Binary",                    t46_strings_binary),
   47: ("SHA256 + VirusTotal-Link",              t47_hash_virustotal),
   48: ("Autostart-Einträge",                    t48_autostart),
   49: ("DeviceAdmin DEAKTIVIEREN",              t49_device_admin),
   50: ("Accessibility-Service KILL",            t50_accessibility_kill),
}

_SECTIONS = [
    ("A · PROZESS-IDENTITÄT",     1,  10),
    ("B · MEMORY FORENSICS",      11, 18),
    ("C · NETZWERK & SOCKETS",    19, 25),
    ("D · DATEI & I/O",           26, 33),
    ("E · SYSCALLS & VERHALTEN",  34, 40),
    ("F · APK & BINARY",          41, 47),
    ("G · PERSISTENZ & KONTROLLE",48, 50),
]


def launch(adb: "ADB", process_line: str) -> None:
    """Startet die 50-Tool Forensik-Konsole für einen verdächtigen Prozess.

    process_line: rohe ps-Zeile oder Prozessbezeichnung aus dem Spyware-Scan
    """
    # PID und Package aus der ps-Zeile extrahieren
    parts = process_line.split()
    pid = ""
    pkg = ""
    for p in parts:
        if p.isdigit() and not pid:
            pid = p
    # Letztes Feld ist meist der Prozessname/Package
    if parts:
        pkg = parts[-1]
        if "/" in pkg:
            pkg = pkg.split("/")[0]
        if "." not in pkg:
            pkg = ""

    while True:
        ui.clear()
        _draw_alert_header(process_line, pid, pkg)

        # Tool-Menü ausgeben
        w = ui.width()
        col_w = (w - 6) // 2
        for sec, start, end in _SECTIONS:
            print(f"\n  {ui.BOLD}{ui.BYELLOW}── {sec} ──{ui.RESET}")
            items = [(n, name) for n, (name, _) in _TOOLS.items() if start <= n <= end]
            for i in range(0, len(items), 2):
                left_n, left_name = items[i]
                left_cell = f"  {ui.CYAN}{left_n:>2}{ui.RESET}  {left_name:<{col_w-6}}"
                if i + 1 < len(items):
                    right_n, right_name = items[i+1]
                    right_cell = f"{ui.CYAN}{right_n:>2}{ui.RESET}  {right_name}"
                    print(f"{left_cell}{right_cell}")
                else:
                    print(left_cell)

        print(f"\n  {ui.GREY}  0  Zurück    A  Alle Tools nacheinander{ui.RESET}")
        print()
        choice = ui.ask("Tool-Nr (1-50)", "0").strip().upper()

        if choice == "0":
            return
        elif choice == "A":
            _run_all(adb, pid, pkg)
        elif choice.isdigit():
            n = int(choice)
            if n in _TOOLS:
                ui.clear()
                _draw_alert_header(process_line, pid, pkg)
                try:
                    _TOOLS[n][1](adb, pid, pkg)
                except Exception as e:
                    ui.err(f"Fehler: {e}")
                ui.pause()
            else:
                ui.warn(f"Tool {n} nicht vorhanden (1-50)")
                time.sleep(0.5)
        else:
            ui.warn("Eingabe 1-50 oder 0")
            time.sleep(0.4)


def _draw_alert_header(process_line: str, pid: str, pkg: str) -> None:
    """Zeichnet den roten Alert-Header mit Prozess-Info."""
    w = ui.width()
    bar = "█" * (w - 1)
    thin = "▄" * (w - 1)
    print(f"\033[38;2;200;30;30m{bar}\033[0m")
    print(f"\033[38;2;255;60;60m{thin}\033[0m")
    print()
    print(f"  \033[1m\033[38;2;255;80;80m🚨 VERDÄCHTIGER PROZESS GEFUNDEN · FORENSIK-KONSOLE\033[0m")
    print()
    print(f"  \033[38;2;255;120;120mProzess:\033[0m  {process_line[:w-12]}")
    print(f"  \033[38;2;255;120;120mPID:\033[0m      {pid or '?'}   "
          f"\033[38;2;255;120;120mPackage:\033[0m {pkg or '(unbekannt)'}")
    print()
    print(f"\033[38;2;255;60;60m{thin}\033[0m")
    print(f"\033[38;2;200;30;30m{bar}\033[0m")
    print()
    print(f"  \033[1m\033[38;2;200;200;200m50 forensische Werkzeuge · Wähle eine Nummer:\033[0m")


def _run_all(adb: "ADB", pid: str, pkg: str) -> None:
    """Führt alle 50 Tools nacheinander aus."""
    ui.clear()
    ui.rule("VOLLSCAN · Alle 50 Tools", "\033[38;2;200;30;30m")
    for n in range(1, 51):
        name, fn = _TOOLS[n]
        print(f"\n\033[38;2;200;30;30m{'━'*60}\033[0m")
        print(f"  \033[1m[{n:>2}/50] {name}\033[0m")
        print(f"\033[38;2;200;30;30m{'━'*60}\033[0m")
        try:
            fn(adb, pid, pkg)
        except Exception as e:
            ui.err(f"Fehler: {e}")
    ui.pause()
