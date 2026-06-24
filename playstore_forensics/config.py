"""Zentrale Konfiguration – Pfade, Limits, Konstanten."""
from __future__ import annotations
import os
from pathlib import Path
from enum import IntEnum

# =============================================================================
# ANDROID ARTIFACT PATHS
# =============================================================================

class APaths:
    """Forensisch relevante Pfade im Android-Dateisystem.
    Zugriff auf /data/data/* erfordert Root oder ADB-Backup."""

    VENDING_DATA = "/data/data/com.android.vending"
    FROSTING_DB  = "/data/system/users/0/frosting.db"
    SUGGESTIONS_DB = "/data/data/com.android.vending/databases/suggestions.db"
    VENDING_DB_DIR = "/data/data/com.android.vending/databases"
    USAGE_STATS_DIR = "/data/system/users/0/usagestats"
    PACKAGES_XML   = "/data/system/packages.xml"
    APP_USAGE_XML  = "/data/system/users/0/app_usage_stats.xml"

    # Fallback: In /sdcard temporär kopiert
    TMP_SDCARD = "/sdcard/_psf_tmp"

    # Bekannte Sub-DBs des Vending-Verzeichnisses
    VENDING_DBS = [
        "suggestions.db",
        "localapps.db",
        "library.db",
        "frosting.db",           # manchmal auch hier gespiegelt
        "billing.db",
        "acquire.db",
    ]


# =============================================================================
# LAUFZEIT-KONFIGURATION
# =============================================================================

OUTPUT_DIR: Path = Path(os.path.expanduser("~/AndroidPanzer/forensik/playstore"))
TEMP_DIR:   Path = Path("/tmp/psf_extract")
MAX_DB_SIZE_MB  = 200
ADB_TIMEOUT     = 45
CHUNK_BYTES     = 65536


# =============================================================================
# AUTHORIZATION LEVELS
# =============================================================================

class AuthLevel(IntEnum):
    NONE          = 0
    OWN_DEVICE    = 1   # eigenes Gerät
    CONSENT       = 2   # schriftliche Einwilligung
    LAW_ENFORCE   = 3   # Behördlicher Auftrag
    COURT_ORDER   = 4   # Gerichtsbeschluss


# =============================================================================
# BEKANNTE INSTALLER-QUELLEN
# =============================================================================

KNOWN_STORES: set[str] = {
    "com.android.vending",
    "com.google.android.packageinstaller",
    "com.android.packageinstaller",
    "com.sec.android.app.samsungapps",
    "com.amazon.venezia",
    "com.aurora.store",
    "org.fdroid.fdroid",
    "com.xiaomi.market",
    "com.huawei.appmarket",
}

SUSPICIOUS_PERMISSIONS: list[str] = [
    "BIND_ACCESSIBILITY_SERVICE",
    "BIND_DEVICE_ADMIN",
    "SYSTEM_ALERT_WINDOW",
    "WRITE_SETTINGS",
    "REQUEST_INSTALL_PACKAGES",
    "READ_CALL_LOG",
    "RECEIVE_BOOT_COMPLETED",
    "FOREGROUND_SERVICE",
    "BIND_NOTIFICATION_LISTENER_SERVICE",
]
