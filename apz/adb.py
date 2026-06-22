"""ADB-Kern: Geräteverwaltung, Shell-Wrapper, Root-Erkennung, Properties."""
from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass, field


class AdbError(Exception):
    pass


def adb_path() -> str:
    p = shutil.which("adb")
    if not p:
        raise AdbError("adb wurde nicht im PATH gefunden. Bitte Android platform-tools installieren.")
    return p


@dataclass
class Device:
    serial: str
    state: str = "device"           # device | unauthorized | offline | recovery | sideload | fastboot | …
    transport: str = "usb"          # usb | tcp
    model: str = ""
    is_root: bool | None = None     # None = noch nicht geprüft
    props: dict = field(default_factory=dict)
    # erweiterte Modus-Erkennung (jeder USB-Modus)
    mode: str = "adb"               # adb | recovery | sideload | unauthorized | offline |
                                    # fastboot | edl | mtk-brom | mtk-preloader | odin | nodebug | usb
    channel: str = "adb"            # adb | fastboot | usb  (über welches Tool erreichbar)
    vidpid: str = ""                # z.B. 05c6:9008
    desc: str = ""                  # lsusb-Beschreibung
    tool: str = ""                  # externes Tool für diesen Modus (edl/mtk/heimdall)

    @property
    def adb_capable(self) -> bool:
        return self.mode in ("adb", "recovery", "sideload")

    @property
    def label(self) -> str:
        m = self.model or self.desc or "Android-Gerät"
        ident = self.serial or self.vidpid or "?"
        return f"{m} ({ident}) [{self.transport}]"


class ADB:
    """Dünner, robuster Wrapper um das adb-Binary, an ein Gerät (Serial) gebunden."""

    # Marker für transiente ADB-Fehler (Verbindung weg, Gerät kurz offline)
    _TRANSIENT = ("error: closed", "device offline", "protocol fault",
                  "error: device", "no devices", "device still authorizing",
                  "error: insufficient permissions", "cannot connect")

    def __init__(self, serial: str | None = None, default_timeout: int = 25):
        self.bin = adb_path()
        self.serial = serial
        self.timeout = default_timeout
        self.root_mode: str | None = None   # 'adb-root' | 'magisk' | 'su' | None
        self._props: dict | None = None     # Cache des kompletten getprop-Dumps

    # ---- Basis ----------------------------------------------------------
    def _base(self) -> list[str]:
        cmd = [self.bin]
        if self.serial:
            cmd += ["-s", self.serial]
        return cmd

    def raw(self, args: list[str], timeout: int | None = None, check: bool = False) -> tuple[int, str, str]:
        """Beliebiges adb-Kommando ausführen. Gibt (rc, stdout, stderr) zurück."""
        try:
            p = subprocess.run(
                self._base() + args,
                capture_output=True, text=True,
                timeout=timeout or self.timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, "", f"Timeout nach {timeout or self.timeout}s: {' '.join(args)}"
        except FileNotFoundError:
            raise AdbError("adb-Binary verschwunden.")
        if check and p.returncode != 0:
            raise AdbError(p.stderr.strip() or f"adb rc={p.returncode}")
        return p.returncode, p.stdout, p.stderr

    def _is_transient(self, text: str) -> bool:
        low = (text or "").lower()
        return any(m in low for m in self._TRANSIENT)

    def _recover(self) -> None:
        """Versucht, eine weggebrochene ADB-Verbindung wiederherzustellen."""
        try:
            self.raw(["reconnect"], timeout=8)
        except Exception:  # noqa: BLE001
            pass
        # kurz auf das Gerät warten (begrenzt, damit es nicht ewig hängt)
        self.raw(["wait-for-device"], timeout=8)

    def shell(self, cmd: str, timeout: int | None = None, root: bool = False,
              retries: int = 2) -> str:
        """adb shell <cmd> mit automatischem Reconnect-Retry bei transienten Fehlern.
        Mit root=True wird je nach erkanntem Root-Modus eskaliert (adb-root direkt, sonst su -c)."""
        if root and self.root_mode != "adb-root":
            esc = cmd.replace("'", "'\\''")
            cmd = f"su -c '{esc}'"
        last = ""
        for attempt in range(retries + 1):
            rc, out, err = self.raw(["shell", cmd], timeout=timeout)
            text = out
            if err.strip():
                text = (text + ("\n" if text else "") + err).strip()
            text = text.rstrip("\r\n") if isinstance(text, str) else text
            # transient? → reconnect + erneut versuchen
            if self._is_transient(text) and attempt < retries:
                last = text
                self._recover()
                continue
            # Roh-ADB-Fehlerzeilen nicht als „Wert" zurückgeben
            if text.strip().lower().startswith(("error:", "adb:")) and not out.strip():
                return ""
            return text
        return "" if self._is_transient(last) else last

    def shell_rc(self, cmd: str, timeout: int | None = None) -> int:
        rc, _, _ = self.raw(["shell", cmd], timeout=timeout)
        return rc

    # ---- Properties -----------------------------------------------------
    def getprop(self, key: str, fresh: bool = False) -> str:
        """Liest eine Property aus dem EINMALIG geholten getprop-Dump (Cache).
        Vermeidet dutzende Einzel-adb-Aufrufe (Ursache von 'error: closed')."""
        props = self.getprops(refresh=fresh)
        if key in props:
            return props[key]
        if props:                      # Dump war erfolgreich, Key existiert nur nicht
            return ""
        # Dump fehlgeschlagen → einmaliger Einzelfallback
        v = self.shell(f"getprop {key}").strip()
        return "" if v.lower().startswith(("error", "adb:")) else v

    def getprops(self, refresh: bool = False) -> dict:
        if self._props is not None and not refresh:
            return self._props
        out = self.shell("getprop")
        props: dict = {}
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("[") and "]: [" in line:
                k, _, v = line.partition("]: [")
                props[k[1:]] = v.rstrip("]")
        # nur cachen, wenn der Dump plausibel ist (sonst beim nächsten Mal neu versuchen)
        self._props = props if props else None
        return props or {}

    # ---- Root -----------------------------------------------------------
    def check_root(self) -> bool:
        """True, wenn auf irgendeinem Weg root erreichbar ist. Setzt self.root_mode."""
        return self.root_method()[0] != "none"

    def root_method(self) -> tuple[str, str]:
        """Erkennt den Root-Zugang. Rückgabe (modus, detail).
        modus ∈ {'adb-root','magisk','su','none'}. Setzt self.root_mode."""
        # 1) adbd läuft bereits als root (userdebug/eng, 'adb root', viele Custom-ROMs)
        direct = self.shell("id 2>/dev/null")
        if "uid=0" in direct:
            self.root_mode = "adb-root"
            return ("adb-root", "adbd läuft als root (kein su nötig)")
        # 2) versuchen, adbd zu eskalieren (nur auf userdebug erfolgreich)
        rc, _, _ = self.raw(["root"], timeout=10)
        if rc == 0:
            self.raw(["wait-for-device"], timeout=15)
            if "uid=0" in self.shell("id 2>/dev/null"):
                self.root_mode = "adb-root"
                return ("adb-root", "via 'adb root' eskaliert")
        # 3) su-Binary (Magisk/SuperSU/KernelSU)
        su = self.shell("su -c id 2>/dev/null")
        if "uid=0" in su:
            mg = self.shell("su -c 'magisk -V' 2>/dev/null").strip()
            ks = self.shell("su -c 'ksud -V' 2>/dev/null").strip()
            if mg:
                self.root_mode = "magisk"
                return ("magisk", f"Magisk v{mg}")
            if ks:
                self.root_mode = "su"
                return ("su", f"KernelSU {ks}")
            self.root_mode = "su"
            return ("su", "su-Binary vorhanden")
        self.root_mode = None
        return ("none", "")

    # ---- Klassenmethoden: Geräte ---------------------------------------
    @classmethod
    def list_devices(cls) -> list[Device]:
        bin_ = adb_path()
        try:
            p = subprocess.run([bin_, "devices", "-l"], capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired:
            return []
        devices: list[Device] = []
        for line in p.stdout.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else "unknown"
            model = ""
            for tok in parts[2:]:
                if tok.startswith("model:"):
                    model = tok.split(":", 1)[1].replace("_", " ")
            transport = "tcp" if (":" in serial and serial.count(".") == 3) else "usb"
            devices.append(Device(serial=serial, state=state, transport=transport, model=model))
        return devices

    @classmethod
    def start_server(cls) -> None:
        try:
            subprocess.run([adb_path(), "start-server"], capture_output=True, text=True, timeout=15)
        except Exception:
            pass

    @classmethod
    def wait_for_device(cls, poll: float = 1.5, on_tick=None) -> Device:
        """Blockiert, bis ein Gerät im Zustand 'device' verfügbar ist."""
        tick = 0
        while True:
            devs = cls.list_devices()
            ready = [d for d in devs if d.state == "device"]
            if ready:
                return ready[0]
            if on_tick:
                on_tick(tick, devs)
            tick += 1
            time.sleep(poll)
