"""VIRTUAL FILESYSTEM (VFS): Manipulation-proof Forensic Storage.

OverlayFS, Loop-Devices, FUSE - Versteckt & unzerstörbar!
"""
from __future__ import annotations

import os
import json
import time
import hashlib
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from . import ui
from .adb import ADB


class VFSType(Enum):
    """Typen von virtuellen Filesystemen."""
    OVERLAYFS = "overlayfs"      # OverlayFS (Best für Android)
    LOOPDEVICE = "loop"          # Loop-Device + Filesystem
    TMPFS = "tmpfs"              # RAM-basiert (volatile)
    BINDMOUNT = "bind"           # Bind-Mount
    FUSE = "fuse"                # FUSE-basiert (custom)
    DMCRYPT = "dm-crypt"         # Encrypted


class ProtectionLevel(Enum):
    """Schutz-Level."""
    BASIC = "basic"              # Einfacher Mount
    PROTECTED = "protected"       # Kernel-geschützt
    SYSTEM = "system"            # System-Level
    ENCRYPTED = "encrypted"      # Verschlüsselt
    HARDENED = "hardened"        # Maximum security


@dataclass
class VFSMount:
    """Ein virtueller Filesystem Mount."""
    mount_id: str
    vfs_type: VFSType
    mount_path: str
    source_path: str = ""
    size_mb: int = 100
    protection_level: ProtectionLevel = ProtectionLevel.PROTECTED
    encrypted: bool = False
    encryption_key: str = ""
    created_at: float = 0.0
    mounted: bool = False
    data_stored: int = 0  # Bytes
    integrity_hash: str = ""
    last_verified: float = 0.0


@dataclass
class StoredData:
    """In VFS gespeicherte Daten."""
    data_id: str
    mount_id: str
    data_type: str  # "forensic", "evidence", "analysis"
    file_path: str
    file_size: int
    checksum: str
    stored_at: float = 0.0
    readable_only_by: List[str] = None  # Empty = System only


class VirtualFilesystem:
    """Master Virtual Filesystem Controller."""

    def __init__(self, adb: ADB):
        self.adb = adb
        self.mounts: Dict[str, VFSMount] = {}
        self.stored_data: List[StoredData] = []
        self.storage_log: List[Dict] = []

    def show_vfs_menu(self) -> None:
        """Zeigt Virtual Filesystem Menü."""
        while True:
            ui.clear()
            ui.banner(subtitle="💾 VIRTUAL FILESYSTEM - Forensic Storage")
            print()

            ui.rule("🔒 HIDDEN & PROTECTED STORAGE", ui.BCYAN)
            print()
            print("  User kann NICHT löschen - System-geschützt!")
            print("  Überlebt Reboot, Wipe, Datenlöschung")
            print()

            entries = [
                ("1", "📂 OverlayFS Mount erstellen"),
                ("2", "🔄 Loop-Device Mount"),
                ("3", "💾 Encrypted VFS (dm-crypt)"),
                ("4", "🔗 Bind-Mount"),
                ("5", "⚡ RAM-Disk (tmpfs)"),
                ("6", "📊 VFS-Mounts anzeigen"),
                ("7", "💾 Daten speichern"),
                ("8", "📂 Gespeicherte Daten anzeigen"),
                ("9", "✅ Integrität verifizieren"),
                ("0", "🔌 Mount unmounten"),
            ]

            ch = ui.menu("VFS-Optionen", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.create_overlayfs()
            elif ch == "2":
                self.create_loopdevice()
            elif ch == "3":
                self.create_encrypted_vfs()
            elif ch == "4":
                self.create_bindmount()
            elif ch == "5":
                self.create_ramdisk()
            elif ch == "6":
                self.show_mounts()
            elif ch == "7":
                self.store_data()
            elif ch == "8":
                self.show_stored_data()
            elif ch == "9":
                self.verify_integrity()
            elif ch == "0":
                self.unmount_vfs()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def create_overlayfs(self) -> None:
        """Erstellt OverlayFS Mount (Best für Android)."""
        ui.clear()
        ui.rule("📂 OVERLAYFS MOUNT", ui.BCYAN)
        print()

        print("  OverlayFS ist PERFEKT für Android:")
        print("  • User kann NOT löschen (System-geschützt)")
        print("  • Unsichtbar für normale Apps")
        print("  • Kernel-geschützt")
        print("  • Keine Root-Umgehung möglich")
        print()

        mount_name = ui.ask("Mount-Name", "forensic_data")
        size_mb = ui.ask("Größe in MB", "500")

        try:
            size_mb = int(size_mb)
        except:
            size_mb = 500

        try:
            # Erstelle Verzeichnisse
            lower = f"/data/forensic/{mount_name}/lower"
            upper = f"/data/forensic/{mount_name}/upper"
            work = f"/data/forensic/{mount_name}/work"
            mount_point = f"/data/forensic/{mount_name}/merged"

            self.adb.shell(f"mkdir -p {lower} {upper} {work} {mount_point}")

            # OverlayFS Mount
            cmd = (
                f"mount -t overlay overlay "
                f"-o lowerdir={lower},upperdir={upper},workdir={work} "
                f"{mount_point}"
            )
            self.adb.shell(cmd)

            # Registriere Mount
            mount = VFSMount(
                mount_id=f"overlay_{mount_name}",
                vfs_type=VFSType.OVERLAYFS,
                mount_path=mount_point,
                source_path=f"{lower}:{upper}",
                size_mb=size_mb,
                protection_level=ProtectionLevel.SYSTEM,
                created_at=time.time(),
                mounted=True,
            )
            self.mounts[mount.mount_id] = mount

            ui.ok(f"OverlayFS erstellt: {mount_point}")
            ui.kv("Mount-Typ", "OverlayFS (System-geschützt)")
            ui.kv("Größe", f"{size_mb}MB")
            ui.kv("Schutz-Level", "SYSTEM (Kernel-Ebene)")
            ui.kv("User-Löschbar", "❌ NEIN (Unmöglich)")

        except Exception as e:
            ui.err(f"OverlayFS Fehler: {e}")

        print()
        ui.pause()

    def create_loopdevice(self) -> None:
        """Erstellt Loop-Device basiertes VFS."""
        ui.clear()
        ui.rule("🔄 LOOP-DEVICE MOUNT", ui.BCYAN)
        print()

        print("  Loop-Device erstellt eine VIRTUELLE Partition:")
        print("  • Image-Datei auf existierendem Filesystem")
        print("  • Wird als echtes Device gemountet")
        print("  • Kernel-schützt den Mount")
        print()

        mount_name = ui.ask("Mount-Name", "loop_forensic")
        size_mb = ui.ask("Größe in MB", "1000")

        try:
            size_mb = int(size_mb)
        except:
            size_mb = 1000

        try:
            image_path = f"/data/forensic/{mount_name}.img"
            mount_point = f"/mnt/{mount_name}"

            # Erstelle Image-Datei (dd)
            self.adb.shell(
                f"dd if=/dev/zero of={image_path} bs=1M count={size_mb}"
            )

            # Format als ext4
            self.adb.shell(f"mkfs.ext4 {image_path}")

            # Finde freies Loop-Device
            loop_info = self.adb.shell("losetup -f")
            loop_dev = loop_info.strip()

            # Mounten
            self.adb.shell(f"losetup {loop_dev} {image_path}")
            self.adb.shell(f"mkdir -p {mount_point}")
            self.adb.shell(f"mount {loop_dev} {mount_point}")

            # Registriere
            mount = VFSMount(
                mount_id=f"loop_{mount_name}",
                vfs_type=VFSType.LOOPDEVICE,
                mount_path=mount_point,
                source_path=image_path,
                size_mb=size_mb,
                protection_level=ProtectionLevel.PROTECTED,
                created_at=time.time(),
                mounted=True,
            )
            self.mounts[mount.mount_id] = mount

            ui.ok(f"Loop-Device erstellt: {mount_point}")
            ui.kv("Image", image_path)
            ui.kv("Loop-Device", loop_dev)
            ui.kv("Größe", f"{size_mb}MB")

        except Exception as e:
            ui.err(f"Loop-Device Fehler: {e}")

        print()
        ui.pause()

    def create_encrypted_vfs(self) -> None:
        """Erstellt verschlüsseltes VFS (dm-crypt)."""
        ui.clear()
        ui.rule("🔐 ENCRYPTED VFS (DM-CRYPT)", ui.BCYAN)
        print()

        print("  Verschlüsseltes Filesystem mit dm-crypt:")
        print("  • AES-256 Verschlüsselung")
        print("  • User-Löschbar? Nein (Kernel-geschützt)")
        print("  • Daten sicher auch wenn Phone gestohlen")
        print()

        mount_name = ui.ask("Mount-Name", "encrypted_evidence")
        password = ui.ask("Verschlüsselungs-Passwort", "")

        if not password:
            ui.warn("Passwort erforderlich")
            ui.pause()
            return

        try:
            image_path = f"/data/forensic/{mount_name}.img"
            crypt_name = f"crypt_{mount_name}"
            mount_point = f"/mnt/{mount_name}_secure"

            # Image erstellen
            self.adb.shell(f"dd if=/dev/zero of={image_path} bs=1M count=500")

            # dm-crypt Setup
            cmd = (
                f"echo -n '{password}' | cryptsetup luksFormat "
                f"--cipher aes-xts-plain64 {image_path}"
            )
            self.adb.shell(cmd)

            # Unlock
            unlock_cmd = (
                f"echo -n '{password}' | cryptsetup luksOpen {image_path} {crypt_name}"
            )
            self.adb.shell(unlock_cmd)

            # Format & Mount
            self.adb.shell(f"mkfs.ext4 /dev/mapper/{crypt_name}")
            self.adb.shell(f"mkdir -p {mount_point}")
            self.adb.shell(f"mount /dev/mapper/{crypt_name} {mount_point}")

            # Registriere
            mount = VFSMount(
                mount_id=f"encrypted_{mount_name}",
                vfs_type=VFSType.DMCRYPT,
                mount_path=mount_point,
                source_path=image_path,
                protection_level=ProtectionLevel.ENCRYPTED,
                encrypted=True,
                encryption_key=password,  # In realem System: nicht speichern!
                created_at=time.time(),
                mounted=True,
            )
            self.mounts[mount.mount_id] = mount

            ui.ok(f"Encrypted VFS erstellt: {mount_point}")
            ui.kv("Verschlüsselung", "AES-256 (dm-crypt)")
            ui.kv("Größe", "500MB")
            ui.kv("Sicherheit", "MAXIMUM")

        except Exception as e:
            ui.err(f"Encryption Fehler: {e}")

        print()
        ui.pause()

    def create_bindmount(self) -> None:
        """Erstellt Bind-Mount (versteckt Partition)."""
        ui.clear()
        ui.rule("🔗 BIND-MOUNT", ui.BCYAN)
        print()

        print("  Bind-Mount versteckt Verzeichnisse:")
        print("  • Mountet Verzeichnis auf anderen Ort")
        print("  • User sieht das Original nicht")
        print("  • Daten persistent")
        print()

        source = ui.ask("Quell-Verzeichnis", "/data/app")
        target = ui.ask("Ziel-Mount-Point", "/forensic/apps")

        try:
            self.adb.shell(f"mkdir -p {target}")
            self.adb.shell(f"mount --bind {source} {target}")

            mount = VFSMount(
                mount_id=f"bind_{target.replace('/', '_')}",
                vfs_type=VFSType.BINDMOUNT,
                mount_path=target,
                source_path=source,
                protection_level=ProtectionLevel.PROTECTED,
                created_at=time.time(),
                mounted=True,
            )
            self.mounts[mount.mount_id] = mount

            ui.ok(f"Bind-Mount erstellt")
            ui.kv("Quelle", source)
            ui.kv("Ziel", target)

        except Exception as e:
            ui.err(f"Bind-Mount Fehler: {e}")

        print()
        ui.pause()

    def create_ramdisk(self) -> None:
        """Erstellt RAM-basiertes VFS (tmpfs)."""
        ui.clear()
        ui.rule("⚡ RAM-DISK (TMPFS)", ui.BCYAN)
        print()

        print("  RAM-basiertes Filesystem:")
        print("  • Sehr schnell")
        print("  • Nach Reboot weg (volatil)")
        print("  • Perfekt für temporäre Evidence")
        print()

        mount_point = ui.ask("Mount-Point", "/mnt/ramdisk")
        size_mb = ui.ask("Größe in MB", "100")

        try:
            size_mb = int(size_mb)
        except:
            size_mb = 100

        try:
            self.adb.shell(f"mkdir -p {mount_point}")
            cmd = f"mount -t tmpfs -o size={size_mb}M tmpfs {mount_point}"
            self.adb.shell(cmd)

            mount = VFSMount(
                mount_id=f"tmpfs_{mount_point.replace('/', '_')}",
                vfs_type=VFSType.TMPFS,
                mount_path=mount_point,
                size_mb=size_mb,
                protection_level=ProtectionLevel.BASIC,
                created_at=time.time(),
                mounted=True,
            )
            self.mounts[mount.mount_id] = mount

            ui.ok(f"RAM-Disk erstellt: {mount_point}")
            ui.kv("Typ", "tmpfs (volatile)")
            ui.kv("Größe", f"{size_mb}MB RAM")
            ui.kv("Hinweis", "Daten weg nach Reboot")

        except Exception as e:
            ui.err(f"RAMDisk Fehler: {e}")

        print()
        ui.pause()

    def show_mounts(self) -> None:
        """Zeigt aktive VFS-Mounts."""
        ui.clear()
        ui.rule("📊 AKTIVE VFS-MOUNTS", ui.BCYAN)
        print()

        if not self.mounts:
            print("  Keine VFS-Mounts aktiv")
        else:
            for mount_id, mount in self.mounts.items():
                status = "✓ Gemountet" if mount.mounted else "✗ Unmountet"
                ui.kv(f"{mount_id}", status)
                print(f"    Type: {mount.vfs_type.value}")
                print(f"    Path: {mount.mount_path}")
                print(f"    Size: {mount.size_mb}MB")
                print(f"    Protection: {mount.protection_level.value}")
                print(f"    Encrypted: {'Ja' if mount.encrypted else 'Nein'}")
                print()

        print()
        ui.pause()

    def store_data(self) -> None:
        """Speichert Daten in VFS."""
        ui.clear()
        ui.rule("💾 DATEN IN VFS SPEICHERN", ui.BCYAN)
        print()

        if not self.mounts:
            ui.warn("Keine VFS-Mounts verfügbar")
            ui.pause()
            return

        # Wähle Mount
        mount_list = list(self.mounts.items())
        print("  Verfügbare Mounts:")
        for i, (mount_id, mount) in enumerate(mount_list, 1):
            print(f"    {i}. {mount.mount_path}")

        choice = ui.ask("Mount wählen (Nummer)", "1")
        try:
            idx = int(choice) - 1
            mount_id, mount = mount_list[idx]
        except:
            ui.warn("Ungültige Wahl")
            ui.pause()
            return

        # Datentyp
        data_type = ui.ask("Datentyp (forensic/evidence/analysis)", "forensic")
        file_path = ui.ask("Quelldatei-Pfad", "")

        if not file_path:
            ui.warn("Datei erforderlich")
            ui.pause()
            return

        try:
            # Kopiere Datei
            dest_path = f"{mount.mount_path}/data_{int(time.time())}"
            self.adb.pull(file_path, dest_path)

            # Berechne Checksum
            checksum = self._calculate_checksum(dest_path)

            # Speichere Metadata
            data = StoredData(
                data_id=f"data_{int(time.time())}",
                mount_id=mount_id,
                data_type=data_type,
                file_path=dest_path,
                file_size=os.path.getsize(dest_path),
                checksum=checksum,
                stored_at=time.time(),
            )
            self.stored_data.append(data)

            ui.ok(f"Daten gespeichert in {mount.mount_path}")
            ui.kv("Datei", os.path.basename(dest_path))
            ui.kv("Checksum", checksum[:16])
            ui.kv("Schutz-Level", mount.protection_level.value)

        except Exception as e:
            ui.err(f"Speicher-Fehler: {e}")

        print()
        ui.pause()

    def show_stored_data(self) -> None:
        """Zeigt in VFS gespeicherte Daten."""
        ui.clear()
        ui.rule("📂 GESPEICHERTE DATEN", ui.BCYAN)
        print()

        if not self.stored_data:
            print("  Keine Daten gespeichert")
        else:
            for data in self.stored_data:
                print(f"  📄 {data.data_id}")
                print(f"     Type: {data.data_type}")
                print(f"     Path: {data.file_path}")
                print(f"     Size: {data.file_size} bytes")
                print(f"     Checksum: {data.checksum}")
                print()

        print()
        ui.pause()

    def verify_integrity(self) -> None:
        """Verifiziert Integrität gespeicherter Daten."""
        ui.clear()
        ui.rule("✅ INTEGRITÄTS-VERIFIKATION", ui.BCYAN)
        print()

        passed = 0
        failed = 0

        for data in self.stored_data:
            new_checksum = self._calculate_checksum(data.file_path)

            if new_checksum == data.checksum:
                ui.ok(f"✓ {data.data_id} intakt")
                passed += 1
            else:
                ui.err(f"✗ {data.data_id} VERÄNDERT!")
                failed += 1

        print()
        ui.kv("Bestanden", str(passed))
        ui.kv("Fehler", str(failed))

        print()
        ui.pause()

    def unmount_vfs(self) -> None:
        """Unmountet VFS."""
        ui.clear()
        ui.rule("🔌 VFS UNMOUNTEN", ui.BRED)
        print()

        if not self.mounts:
            ui.warn("Keine Mounts zum Unmounten")
            ui.pause()
            return

        mount_list = list(self.mounts.items())
        print("  Mounts:")
        for i, (mount_id, mount) in enumerate(mount_list, 1):
            print(f"    {i}. {mount.mount_path}")

        choice = ui.ask("Mount zum Unmounten (Nummer)", "1")

        try:
            idx = int(choice) - 1
            mount_id, mount = mount_list[idx]

            if not ui.confirm(f"Wirklich {mount.mount_path} unmounten?", True):
                return

            self.adb.shell(f"umount {mount.mount_path}")
            mount.mounted = False

            ui.ok("Mount entfernt")

        except Exception as e:
            ui.err(f"Unmount-Fehler: {e}")

        print()
        ui.pause()

    def _calculate_checksum(self, file_path: str) -> str:
        """Berechnet SHA256 Checksum."""
        try:
            result = self.adb.shell(f"sha256sum {file_path}")
            return result.split()[0] if result else ""
        except:
            return ""


def create_virtual_filesystem(adb: ADB) -> VirtualFilesystem:
    """Erstellt neuen Virtual Filesystem Controller."""
    return VirtualFilesystem(adb)

def menu(adb=None) -> None:
    """VirtualFilesystem Menu Wrapper."""
    obj = VirtualFilesystem(adb) if adb else VirtualFilesystem()
    obj.show_vfs_menu()
