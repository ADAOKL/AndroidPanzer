"""Internationalisierung – übersetzt alle sichtbaren UI-Strings.

Standard ist Deutsch. Die gewählte Sprache wird unter
~/.config/androidpanzer/lang gespeichert und beim nächsten Start
voreingestellt. Fehlende Übersetzungen fallen auf Deutsch zurück.
"""
from __future__ import annotations

import os

_LANG = "de"

LANGUAGES: dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "pt": "Português",
    "it": "Italiano",
    "tr": "Türkçe",
    "ru": "Русский",
}

_CFG = os.path.expanduser("~/.config/androidpanzer/lang")


def _load_saved() -> str:
    try:
        with open(_CFG) as fh:
            code = fh.read().strip()
            if code in LANGUAGES:
                return code
    except OSError:
        pass
    return "de"


def _save(code: str) -> None:
    try:
        os.makedirs(os.path.dirname(_CFG), exist_ok=True)
        with open(_CFG, "w") as fh:
            fh.write(code)
    except OSError:
        pass


def set_lang(code: str) -> None:
    global _LANG
    if code in LANGUAGES:
        _LANG = code


def current() -> str:
    return _LANG


def t(key: str, **kwargs) -> str:
    """Gibt den übersetzten String zurück; fehlt er, fällt das System auf Deutsch zurück."""
    d = _STRINGS.get(key, {})
    s = d.get(_LANG) or d.get("de", key)
    return s.format(**kwargs) if kwargs else s


def select_language() -> None:
    """Zeigt eine Sprachauswahl vor dem Start. Speichert die Wahl dauerhaft."""
    from . import ui  # lokaler Import – vermeidet Zirkelbezug auf Modulebene

    saved = _load_saved()
    set_lang(saved)

    ui.clear()
    ui.banner()

    langs = list(LANGUAGES.items())
    print()
    ui.rule("Sprache / Language / Idioma / Langue / Língua / Lingua / Dil / Язык", ui.YELLOW)
    for i, (code, name) in enumerate(langs, 1):
        marker = f"  {ui.BGREEN}►{ui.RESET}" if code == saved else "   "
        print(f"{marker} {ui.BOLD}{ui.CYAN}{i:>2}{ui.RESET}  {name:<20}  {ui.GREY}({code}){ui.RESET}")

    saved_name = LANGUAGES.get(saved, saved)
    print()
    print(f"  {ui.GREY}[ENTER] = {saved_name} beibehalten / keep / mantener{ui.RESET}")
    choice = ui.ask(f"1-{len(langs)}", "").strip()

    if not choice:
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(langs):
            code = langs[idx][0]
            set_lang(code)
            _save(code)
    except ValueError:
        pass


# ─────────────────────────────── ÜBERSETZUNGEN ───────────────────────────────

_STRINGS: dict[str, dict[str, str]] = {

    # ── ui.py: confirm() ────────────────────────────────────────────────────
    "ui_yes_no_true": {
        "de": "J/n",  "en": "Y/n",  "es": "S/n",  "fr": "O/n",
        "pt": "S/n",  "it": "S/n",  "tr": "E/h",  "ru": "Д/н",
    },
    "ui_yes_no_false": {
        "de": "j/N",  "en": "y/N",  "es": "s/N",  "fr": "o/N",
        "pt": "s/N",  "it": "s/N",  "tr": "e/H",  "ru": "д/Н",
    },
    # Leerzeichen-getrennte Liste gültiger Ja-Antworten
    "ui_yes_answers": {
        "de": "j ja y yes",
        "en": "y yes j ja",
        "es": "s si y yes",
        "fr": "o oui y yes",
        "pt": "s sim y yes",
        "it": "s si y yes",
        "tr": "e evet y yes",
        "ru": "д да y yes",
    },

    # ── ui.py: pause() ──────────────────────────────────────────────────────
    "ui_pause": {
        "de": "Weiter mit ENTER",
        "en": "Press ENTER to continue",
        "es": "Pulsa ENTER para continuar",
        "fr": "Appuyez sur ENTRÉE pour continuer",
        "pt": "Prima ENTER para continuar",
        "it": "Premi INVIO per continuare",
        "tr": "Devam için ENTER'a basın",
        "ru": "Нажмите ENTER для продолжения",
    },

    # ── ui.py: pager() ──────────────────────────────────────────────────────
    "ui_pager_more": {
        "de": "-- mehr ({done}/{total}) -- ENTER=weiter, q=Ende --",
        "en": "-- more ({done}/{total}) -- ENTER=continue, q=quit --",
        "es": "-- más ({done}/{total}) -- ENTER=continuar, q=salir --",
        "fr": "-- suite ({done}/{total}) -- ENTRÉE=continuer, q=quitter --",
        "pt": "-- mais ({done}/{total}) -- ENTER=continuar, q=sair --",
        "it": "-- altro ({done}/{total}) -- INVIO=continua, q=esci --",
        "tr": "-- devam ({done}/{total}) -- ENTER=devam, q=çıkış --",
        "ru": "-- далее ({done}/{total}) -- ENTER=продолжить, q=выход --",
    },
    "ui_no_output": {
        "de": "(keine Ausgabe)",   "en": "(no output)",       "es": "(sin salida)",
        "fr": "(aucune sortie)",   "pt": "(sem saída)",       "it": "(nessun output)",
        "tr": "(çıktı yok)",       "ru": "(нет вывода)",
    },

    # ── ui.py: menu() ───────────────────────────────────────────────────────
    "ui_select": {
        "de": "Auswahl",    "en": "Choice",      "es": "Selección",
        "fr": "Choix",      "pt": "Escolha",     "it": "Scelta",
        "tr": "Seçim",      "ru": "Выбор",
    },
    "ui_back": {
        "de": "Zurück",     "en": "Back",        "es": "Volver",
        "fr": "Retour",     "pt": "Voltar",      "it": "Indietro",
        "tr": "Geri",       "ru": "Назад",
    },
    "ui_quit": {
        "de": "Beenden",    "en": "Quit",        "es": "Salir",
        "fr": "Quitter",    "pt": "Sair",        "it": "Esci",
        "tr": "Çıkış",      "ru": "Выход",
    },
    # Leerzeichen-getrennte Liste aller Schlüsselworte, die als "Zurück" gelten
    "ui_back_keywords": {
        "de": "zurück back",    "en": "back zurück",    "es": "volver back",
        "fr": "retour back",    "pt": "voltar back",    "it": "indietro back",
        "tr": "geri back",      "ru": "назад back",
    },

    # ── ui.py: multiselect() ────────────────────────────────────────────────
    "ui_multiselect_help": {
        "de": "↑/↓ bewegen · LEERTASTE wählen · a alle · n keine · i invertieren · ENTER export · q Abbruch",
        "en": "↑/↓ move · SPACE select · a all · n none · i invert · ENTER export · q cancel",
        "es": "↑/↓ mover · ESPACIO seleccionar · a todo · n ninguno · i invertir · ENTER exportar · q cancelar",
        "fr": "↑/↓ déplacer · ESPACE sélectionner · a tout · n rien · i inverser · ENTRÉE exporter · q annuler",
        "pt": "↑/↓ mover · ESPAÇO selecionar · a tudo · n nada · i inverter · ENTER exportar · q cancelar",
        "it": "↑/↓ muovere · SPAZIO seleziona · a tutto · n niente · i inverti · INVIO esporta · q annulla",
        "tr": "↑/↓ hareket · BOŞLUK seç · a tümü · n hiçbiri · i ters çevir · ENTER dışa aktar · q iptal",
        "ru": "↑/↓ перемещение · ПРОБЕЛ выбрать · a все · n ничего · i инверт · ENTER экспорт · q отмена",
    },
    "ui_multiselect_fallback": {
        "de": "Auswahl-Nrn (Komma, 'all', leer=Abbruch)",
        "en": "Selection numbers (comma, 'all', empty=cancel)",
        "es": "Números de selección (coma, 'all', vacío=cancelar)",
        "fr": "Numéros de sélection (virgule, 'all', vide=annuler)",
        "pt": "Números de seleção (vírgula, 'all', vazio=cancelar)",
        "it": "Numeri di selezione (virgola, 'all', vuoto=annulla)",
        "tr": "Seçim numaraları (virgül, 'all', boş=iptal)",
        "ru": "Номера выбора (запятая, 'all', пусто=отмена)",
    },
    "ui_selected_count": {
        "de": "{sel}/{total} gewählt",       "en": "{sel}/{total} selected",
        "es": "{sel}/{total} seleccionados", "fr": "{sel}/{total} sélectionnés",
        "pt": "{sel}/{total} selecionados",  "it": "{sel}/{total} selezionati",
        "tr": "{sel}/{total} seçildi",       "ru": "{sel}/{total} выбрано",
    },

    # ── ui.py: badge() ──────────────────────────────────────────────────────
    "badge_danger": {
        "de": "GEFAHR",   "en": "DANGER",    "es": "PELIGRO",
        "fr": "DANGER",   "pt": "PERIGO",    "it": "PERICOLO",
        "tr": "TEHLİKE",  "ru": "ОПАСНО",
    },

    # ── main.py: _connect() ─────────────────────────────────────────────────
    "connect_title": {
        "de": "Universelle Geräteerkennung – alle Modi",
        "en": "Universal device detection – all modes",
        "es": "Detección universal de dispositivos – todos los modos",
        "fr": "Détection universelle d'appareils – tous les modes",
        "pt": "Deteção universal de dispositivos – todos os modos",
        "it": "Rilevamento universale dispositivi – tutte le modalità",
        "tr": "Evrensel cihaz algılama – tüm modlar",
        "ru": "Универсальное обнаружение устройств – все режимы",
    },
    "connect_no_device": {
        "de": "Kein Gerät erkannt. Verbinde ein Android-Gerät per USB.",
        "en": "No device detected. Connect an Android device via USB.",
        "es": "No se detectó ningún dispositivo. Conecta un dispositivo Android por USB.",
        "fr": "Aucun appareil détecté. Connectez un appareil Android via USB.",
        "pt": "Nenhum dispositivo detetado. Ligue um dispositivo Android por USB.",
        "it": "Nessun dispositivo rilevato. Collega un dispositivo Android via USB.",
        "tr": "Cihaz algılanmadı. USB ile bir Android cihaz bağlayın.",
        "ru": "Устройств не обнаружено. Подключите Android-устройство по USB.",
    },
    "connect_detects": {
        "de": "Erkennt: ADB · Recovery · Sideload · Fastboot · EDL · MTK · Odin · auch ohne USB-Debugging.",
        "en": "Detects: ADB · Recovery · Sideload · Fastboot · EDL · MTK · Odin · even without USB debugging.",
        "es": "Detecta: ADB · Recovery · Sideload · Fastboot · EDL · MTK · Odin · incluso sin depuración USB.",
        "fr": "Détecte : ADB · Recovery · Sideload · Fastboot · EDL · MTK · Odin · même sans débogage USB.",
        "pt": "Deteta: ADB · Recovery · Sideload · Fastboot · EDL · MTK · Odin · mesmo sem depuração USB.",
        "it": "Rileva: ADB · Recovery · Sideload · Fastboot · EDL · MTK · Odin · anche senza debug USB.",
        "tr": "Algılar: ADB · Recovery · Sideload · Fastboot · EDL · MTK · Odin · USB hata ayıklama olmadan bile.",
        "ru": "Определяет: ADB · Recovery · Sideload · Fastboot · EDL · MTK · Odin · даже без отладки по USB.",
    },
    "connect_prompt_line": {
        "de": "[ENTER] = scannen & warten   [m] = Bootloop-Live-Monitor   [q] = beenden",
        "en": "[ENTER] = scan & wait   [m] = bootloop live monitor   [q] = quit",
        "es": "[ENTER] = escanear y esperar   [m] = monitor de bootloop   [q] = salir",
        "fr": "[ENTRÉE] = scanner & attendre   [m] = moniteur bootloop   [q] = quitter",
        "pt": "[ENTER] = procurar e aguardar   [m] = monitor de bootloop   [q] = sair",
        "it": "[INVIO] = scansiona e attendi   [m] = monitor bootloop   [q] = esci",
        "tr": "[ENTER] = tara ve bekle   [m] = bootloop canlı monitör   [q] = çıkış",
        "ru": "[ENTER] = сканировать и ждать   [m] = монитор загрузки   [q] = выход",
    },
    "connect_scanning": {
        "de": "Scanne … Abbrechen mit STRG+C.\n",
        "en": "Scanning … Press CTRL+C to abort.\n",
        "es": "Escaneando … CTRL+C para cancelar.\n",
        "fr": "Scan en cours … CTRL+C pour annuler.\n",
        "pt": "A procurar … CTRL+C para cancelar.\n",
        "it": "Scansione … CTRL+C per annullare.\n",
        "tr": "Taranıyor … İptal için CTRL+C.\n",
        "ru": "Сканирование … CTRL+C для отмены.\n",
    },
    "connect_scanning_spin": {
        "de": "Scanne USB-Bus (adb + fastboot + lsusb) …",
        "en": "Scanning USB bus (adb + fastboot + lsusb) …",
        "es": "Escaneando bus USB (adb + fastboot + lsusb) …",
        "fr": "Scan du bus USB (adb + fastboot + lsusb) …",
        "pt": "A procurar bus USB (adb + fastboot + lsusb) …",
        "it": "Scansione bus USB (adb + fastboot + lsusb) …",
        "tr": "USB veri yolu taranıyor (adb + fastboot + lsusb) …",
        "ru": "Сканирование USB-шины (adb + fastboot + lsusb) …",
    },
    "connect_found": {
        "de": "{n} Gerät(e) erkannt",       "en": "{n} device(s) detected",
        "es": "{n} dispositivo(s) detectado(s)", "fr": "{n} appareil(s) détecté(s)",
        "pt": "{n} dispositivo(s) detetado(s)", "it": "{n} dispositivo/i rilevato/i",
        "tr": "{n} cihaz algılandı",         "ru": "Обнаружено устройств: {n}",
    },
    "connect_chosen": {
        "de": "Gewählt:",     "en": "Selected:",    "es": "Seleccionado:",
        "fr": "Sélectionné:", "pt": "Selecionado:", "it": "Selezionato:",
        "tr": "Seçildi:",     "ru": "Выбрано:",
    },
    "connect_choose_device": {
        "de": "Gerät wählen",            "en": "Choose device",
        "es": "Elegir dispositivo",      "fr": "Choisir un appareil",
        "pt": "Escolher dispositivo",    "it": "Scegli dispositivo",
        "tr": "Cihaz seç",               "ru": "Выберите устройство",
    },

    # ── main.py: run() ──────────────────────────────────────────────────────
    "run_fastboot_notice": {
        "de": "Fastboot-Modus erkannt – ENTER für Fastboot-Menü",
        "en": "Fastboot mode detected – ENTER for Fastboot menu",
        "es": "Modo Fastboot detectado – ENTER para el menú Fastboot",
        "fr": "Mode Fastboot détecté – ENTRÉE pour le menu Fastboot",
        "pt": "Modo Fastboot detetado – ENTER para menu Fastboot",
        "it": "Modalità Fastboot rilevata – INVIO per menu Fastboot",
        "tr": "Fastboot modu algılandı – Fastboot menüsü için ENTER",
        "ru": "Обнаружен режим Fastboot – ENTER для меню Fastboot",
    },
    "run_analyzing": {
        "de": "Gerät erkannt: {label} – starte Auto-Analyse …",
        "en": "Device detected: {label} – starting auto-analysis …",
        "es": "Dispositivo detectado: {label} – iniciando análisis automático …",
        "fr": "Appareil détecté : {label} – démarrage de l'analyse automatique …",
        "pt": "Dispositivo detetado: {label} – a iniciar análise automática …",
        "it": "Dispositivo rilevato: {label} – avvio analisi automatica …",
        "tr": "Cihaz algılandı: {label} – otomatik analiz başlatılıyor …",
        "ru": "Устройство обнаружено: {label} – запуск автоанализа …",
    },
    "run_collecting": {
        "de": "Sammle Kerndaten (Hardware, Android, Akku, RAM, Netz, SIM, Root) …",
        "en": "Collecting core data (hardware, Android, battery, RAM, network, SIM, root) …",
        "es": "Recopilando datos principales (hardware, Android, batería, RAM, red, SIM, root) …",
        "fr": "Collecte des données principales (matériel, Android, batterie, RAM, réseau, SIM, root) …",
        "pt": "A recolher dados principais (hardware, Android, bateria, RAM, rede, SIM, root) …",
        "it": "Raccolta dati principali (hardware, Android, batteria, RAM, rete, SIM, root) …",
        "tr": "Ana veriler toplanıyor (donanım, Android, batarya, RAM, ağ, SIM, root) …",
        "ru": "Сбор основных данных (железо, Android, батарея, ОЗУ, сеть, SIM, root) …",
    },
    "run_not_rooted": {
        "de": "Gerät ist nicht gerootet. Für [ROOT]-Funktionen: Hauptmenü → R (Rooting-Assistent).",
        "en": "Device is not rooted. For [ROOT] features: main menu → R (Rooting Assistant).",
        "es": "El dispositivo no está rooteado. Para funciones [ROOT]: menú principal → R.",
        "fr": "L'appareil n'est pas rooté. Pour les fonctions [ROOT] : menu principal → R.",
        "pt": "Dispositivo sem root. Para funções [ROOT]: menu principal → R.",
        "it": "Dispositivo non rootato. Per le funzioni [ROOT]: menu principale → R.",
        "tr": "Cihaz rootlanmamış. [ROOT] özellikleri için: ana menü → R.",
        "ru": "Устройство не рутировано. Для функций [ROOT]: главное меню → R.",
    },
    "run_go_menu": {
        "de": "Weiter zum Hauptmenü mit ENTER",
        "en": "Press ENTER to go to main menu",
        "es": "Pulsa ENTER para ir al menú principal",
        "fr": "Appuyez sur ENTRÉE pour accéder au menu principal",
        "pt": "Prima ENTER para ir ao menu principal",
        "it": "Premi INVIO per andare al menu principale",
        "tr": "Ana menüye gitmek için ENTER'a basın",
        "ru": "Нажмите ENTER для перехода в главное меню",
    },
    "run_other_device": {
        "de": "Anderes Gerät wählen?",         "en": "Choose another device?",
        "es": "¿Elegir otro dispositivo?",     "fr": "Choisir un autre appareil ?",
        "pt": "Escolher outro dispositivo?",   "it": "Scegliere un altro dispositivo?",
        "tr": "Başka bir cihaz seçilsin mi?",  "ru": "Выбрать другое устройство?",
    },
    "run_goodbye": {
        "de": "Android Panzer beendet. Stay safe.",
        "en": "Android Panzer finished. Stay safe.",
        "es": "Android Panzer finalizado. Mantente seguro.",
        "fr": "Android Panzer terminé. Restez prudent.",
        "pt": "Android Panzer terminado. Fica em segurança.",
        "it": "Android Panzer terminato. Stai al sicuro.",
        "tr": "Android Panzer bitti. Güvende kal.",
        "ru": "Android Panzer завершён. Будьте осторожны.",
    },
    "run_no_device_abort": {
        "de": "Kein Gerät – Abbruch.",      "en": "No device – aborting.",
        "es": "Sin dispositivo – cancelando.", "fr": "Aucun appareil – annulation.",
        "pt": "Sem dispositivo – a cancelar.", "it": "Nessun dispositivo – annullamento.",
        "tr": "Cihaz yok – iptal ediliyor.", "ru": "Нет устройства – прерывание.",
    },

    # ── main.py: _main_menu() ───────────────────────────────────────────────
    "menu_rooted": {
        "de": "gerootet",       "en": "rooted",        "es": "rooteado",
        "fr": "rooté",          "pt": "com root",      "it": "rootato",
        "tr": "rootlanmış",     "ru": "рутирован",
    },
    "menu_not_rooted": {
        "de": "nicht gerootet", "en": "not rooted",    "es": "sin root",
        "fr": "non rooté",      "pt": "sem root",      "it": "non rootato",
        "tr": "root yok",       "ru": "не рутирован",
    },
    "menu_functions_label": {
        "de": "Funktionen",     "en": "Features",      "es": "Funciones",
        "fr": "Fonctionnalités","pt": "Funções",        "it": "Funzioni",
        "tr": "Özellikler",     "ru": "Функции",
    },
    "menu_main_title": {
        "de": "HAUPTMENÜ",          "en": "MAIN MENU",          "es": "MENÚ PRINCIPAL",
        "fr": "MENU PRINCIPAL",     "pt": "MENU PRINCIPAL",     "it": "MENU PRINCIPALE",
        "tr": "ANA MENÜ",           "ru": "ГЛАВНОЕ МЕНЮ",
    },
    "menu_back_choose_device": {
        "de": "Gerät neu wählen",       "en": "Re-select device",
        "es": "Reseleccionar dispositivo", "fr": "Resélectionner l'appareil",
        "pt": "Resselecionat dispositivo", "it": "Ri-seleziona dispositivo",
        "tr": "Cihazı yeniden seç",     "ru": "Переключить устройство",
    },
    "menu_quit_confirm": {
        "de": "Android Panzer beenden?",    "en": "Quit Android Panzer?",
        "es": "¿Salir de Android Panzer?",  "fr": "Quitter Android Panzer ?",
        "pt": "Sair do Android Panzer?",    "it": "Uscire da Android Panzer?",
        "tr": "Android Panzer'dan çıkılsın mı?", "ru": "Выйти из Android Panzer?",
    },
    "menu_invalid": {
        "de": "Ungültige Auswahl.",  "en": "Invalid choice.",    "es": "Selección no válida.",
        "fr": "Choix invalide.",     "pt": "Escolha inválida.",  "it": "Scelta non valida.",
        "tr": "Geçersiz seçim.",     "ru": "Неверный выбор.",
    },

    # Menü-Einträge (Buchstabenkeys)
    "menu_D": {
        "de": "Dashboard / Geräte-Analyse erneut anzeigen",
        "en": "Dashboard / Re-run device analysis",
        "es": "Panel / Mostrar análisis del dispositivo de nuevo",
        "fr": "Tableau de bord / Relancer l'analyse du dispositif",
        "pt": "Painel / Mostrar análise do dispositivo novamente",
        "it": "Dashboard / Mostra di nuovo l'analisi del dispositivo",
        "tr": "Gösterge Paneli / Cihaz analizini tekrar göster",
        "ru": "Панель / Повторить анализ устройства",
    },
    "menu_K": {
        "de": "Alle 45 Kategorien (450 Funktionen)",
        "en": "All 45 categories (450 features)",
        "es": "Todas las 45 categorías (450 funciones)",
        "fr": "Toutes les 45 catégories (450 fonctionnalités)",
        "pt": "Todas as 45 categorias (450 funções)",
        "it": "Tutte le 45 categorie (450 funzioni)",
        "tr": "Tüm 45 kategori (450 özellik)",
        "ru": "Все 45 категорий (450 функций)",
    },
    "menu_X": {
        "de": "ROOT-ARSENAL – Tiefenzugriff, Wiederherstellung, Backdoor-Scan (NUR ROOT)",
        "en": "ROOT ARSENAL – deep access, recovery, backdoor scan (ROOT ONLY)",
        "es": "ARSENAL ROOT – acceso profundo, recuperación, escaneo backdoor (SOLO ROOT)",
        "fr": "ARSENAL ROOT – accès profond, récupération, scan backdoor (ROOT UNIQUEMENT)",
        "pt": "ARSENAL ROOT – acesso profundo, recuperação, scan backdoor (SÓ ROOT)",
        "it": "ARSENALE ROOT – accesso profondo, recupero, scansione backdoor (SOLO ROOT)",
        "tr": "ROOT ARSENAL – derin erişim, kurtarma, arka kapı taraması (YALNIZCA ROOT)",
        "ru": "ROOT-АРСЕНАЛ – глубокий доступ, восстановление, скан бэкдоров (ТОЛЬКО ROOT)",
    },
    "menu_R": {
        "de": "Root-Status & Rooting-Assistent",
        "en": "Root status & Rooting assistant",
        "es": "Estado de root y asistente de rooting",
        "fr": "État root et assistant de rootage",
        "pt": "Estado root e assistente de rooting",
        "it": "Stato root e assistente di rooting",
        "tr": "Root durumu ve rooting asistanı",
        "ru": "Статус root и помощник рутинга",
    },
    "menu_R_detail": {
        "de": "Root-Status / Rooting-Assistent (Details)",
        "en": "Root status / Rooting assistant (details)",
        "es": "Estado root / Asistente de rooting (detalles)",
        "fr": "État root / Assistant de rootage (détails)",
        "pt": "Estado root / Assistente de rooting (detalhes)",
        "it": "Stato root / Assistente di rooting (dettagli)",
        "tr": "Root durumu / Rooting asistanı (ayrıntılar)",
        "ru": "Статус root / Помощник рутинга (подробности)",
    },
    "menu_V": {
        "de": "VOLLANALYSE – 45-Sektionen-Forensik → Gesamtbericht",
        "en": "FULL ANALYSIS – 45-section forensics → complete report",
        "es": "ANÁLISIS COMPLETO – forense de 45 secciones → informe completo",
        "fr": "ANALYSE COMPLÈTE – forensique 45 sections → rapport complet",
        "pt": "ANÁLISE COMPLETA – forense 45 secções → relatório completo",
        "it": "ANALISI COMPLETA – forense 45 sezioni → rapporto completo",
        "tr": "TAM ANALİZ – 45 bölümlü adli analiz → tam rapor",
        "ru": "ПОЛНЫЙ АНАЛИЗ – криминалистика 45 разделов → отчёт",
    },
    "menu_S": {
        "de": "Forensischer Deep-Scan (versteckte Apps/Profile/Icons)",
        "en": "Forensic deep scan (hidden apps/profiles/icons)",
        "es": "Escaneo forense profundo (apps/perfiles/iconos ocultos)",
        "fr": "Scan forensique approfondi (apps/profils/icônes cachés)",
        "pt": "Scan forense profundo (apps/perfis/ícones ocultos)",
        "it": "Scansione forense approfondita (app/profili/icone nascosti)",
        "tr": "Adli derin tarama (gizli uygulamalar/profiller/simgeler)",
        "ru": "Глубокий криминалистический скан (скрытые приложения/профили/иконки)",
    },
    "menu_A": {
        "de": "APK-Analyse · App-Risiko-Inventar · IOC-Scan (Stalkerware)",
        "en": "APK analysis · App risk inventory · IOC scan (stalkerware)",
        "es": "Análisis APK · Inventario de riesgos de apps · Escaneo IOC (stalkerware)",
        "fr": "Analyse APK · Inventaire risques apps · Scan IOC (stalkerware)",
        "pt": "Análise APK · Inventário de riscos de apps · Scan IOC (stalkerware)",
        "it": "Analisi APK · Inventario rischi app · Scansione IOC (stalkerware)",
        "tr": "APK analizi · Uygulama risk envanteri · IOC taraması (stalkerware)",
        "ru": "APK-анализ · Инвентарь рисков приложений · IOC-скан (сталкерware)",
    },
    "menu_U": {
        "de": "App-Inventar – ALLE Apps, Anomalien rot, Auswahl & Export",
        "en": "App inventory – ALL apps, anomalies in red, select & export",
        "es": "Inventario de apps – TODAS las apps, anomalías en rojo, seleccionar y exportar",
        "fr": "Inventaire des apps – TOUTES les apps, anomalies en rouge, sélection & export",
        "pt": "Inventário de apps – TODAS as apps, anomalias a vermelho, selecionar e exportar",
        "it": "Inventario app – TUTTE le app, anomalie in rosso, selezione ed export",
        "tr": "Uygulama envanteri – TÜM uygulamalar, anomaliler kırmızı, seç ve dışa aktar",
        "ru": "Инвентарь приложений – ВСЕ приложения, аномалии красным, выбор и экспорт",
    },
    "menu_O": {
        "de": "Ordnerstruktur komplett analysieren (Baum + verdächtige Dateien)",
        "en": "Analyze full folder structure (tree + suspicious files)",
        "es": "Analizar estructura de carpetas completa (árbol + archivos sospechosos)",
        "fr": "Analyser la structure de dossiers complète (arborescence + fichiers suspects)",
        "pt": "Analisar estrutura de pastas completa (árvore + ficheiros suspeitos)",
        "it": "Analisi completa struttura cartelle (albero + file sospetti)",
        "tr": "Tam klasör yapısını analiz et (ağaç + şüpheli dosyalar)",
        "ru": "Полный анализ структуры папок (дерево + подозрительные файлы)",
    },
    "menu_F": {
        "de": "Daten-Forensik & Wiederherstellung (Konten/Anrufe/Medien…)",
        "en": "Data forensics & recovery (accounts/calls/media…)",
        "es": "Forense de datos y recuperación (cuentas/llamadas/medios…)",
        "fr": "Forensique de données & récupération (comptes/appels/médias…)",
        "pt": "Forense de dados e recuperação (contas/chamadas/media…)",
        "it": "Forense dati e recupero (account/chiamate/media…)",
        "tr": "Veri adli tıp ve kurtarma (hesaplar/aramalar/medya…)",
        "ru": "Криминалистика данных и восстановление (аккаунты/звонки/медиа…)",
    },
    "menu_T": {
        "de": "TIEFEN-ENGINE – Frida / Traffic / Messenger / Timeline",
        "en": "DEEP ENGINE – Frida / Traffic / Messenger / Timeline",
        "es": "MOTOR PROFUNDO – Frida / Tráfico / Mensajería / Línea de tiempo",
        "fr": "MOTEUR PROFOND – Frida / Trafic / Messagerie / Chronologie",
        "pt": "MOTOR PROFUNDO – Frida / Tráfego / Mensageiro / Linha do tempo",
        "it": "MOTORE PROFONDO – Frida / Traffico / Messenger / Timeline",
        "tr": "DERİN MOTOR – Frida / Trafik / Mesajlaşma / Zaman çizelgesi",
        "ru": "ГЛУБОКИЙ ДВИЖОК – Frida / Трафик / Мессенджер / Таймлайн",
    },
    "menu_B": {
        "de": "Fall-Datenbank & Beweissicherung (PC-seitig, SHA-256 + Chain-of-Custody)",
        "en": "Case database & evidence preservation (PC-side, SHA-256 + chain-of-custody)",
        "es": "Base de datos de casos y preservación de evidencias (SHA-256 + cadena de custodia)",
        "fr": "Base de données d'affaires & préservation des preuves (SHA-256 + chaîne de preuve)",
        "pt": "Base de dados de casos e preservação de evidências (SHA-256 + cadeia de custódia)",
        "it": "Database casi e conservazione prove (SHA-256 + catena di custodia)",
        "tr": "Dava veritabanı ve delil koruma (SHA-256 + delil zinciri)",
        "ru": "База дел и сохранение улик (SHA-256 + цепочка хранения)",
    },
    "menu_E": {
        "de": "Report & Export (HTML/Markdown/JSON + SHA-256-Manifest über alle Funde)",
        "en": "Report & export (HTML/Markdown/JSON + SHA-256 manifest of all findings)",
        "es": "Informe y exportación (HTML/Markdown/JSON + manifiesto SHA-256)",
        "fr": "Rapport & export (HTML/Markdown/JSON + manifeste SHA-256)",
        "pt": "Relatório e exportação (HTML/Markdown/JSON + manifesto SHA-256)",
        "it": "Report ed esport (HTML/Markdown/JSON + manifesto SHA-256)",
        "tr": "Rapor ve dışa aktarma (HTML/Markdown/JSON + SHA-256 manifestosu)",
        "ru": "Отчёт и экспорт (HTML/Markdown/JSON + SHA-256-манифест)",
    },
    "menu_Y": {
        "de": "Modus-Wechsel – Gerät automatisch in Download/Fastboot/Recovery bringen",
        "en": "Mode switch – automatically put device into Download/Fastboot/Recovery",
        "es": "Cambio de modo – poner dispositivo en Download/Fastboot/Recovery automáticamente",
        "fr": "Changement de mode – mettre l'appareil en Download/Fastboot/Recovery automatiquement",
        "pt": "Mudança de modo – colocar dispositivo em Download/Fastboot/Recovery automaticamente",
        "it": "Cambio modalità – porta il dispositivo in Download/Fastboot/Recovery automaticamente",
        "tr": "Mod değiştirme – cihazı otomatik olarak Download/Fastboot/Recovery moduna al",
        "ru": "Переключение режима – автоматически перевести устройство в Download/Fastboot/Recovery",
    },
    "menu_J": {
        "de": "Custom-Firmware/ROMs fürs Gerät anzeigen (LineageOS/TWRP/…)",
        "en": "Show custom firmware/ROMs for device (LineageOS/TWRP/…)",
        "es": "Mostrar firmware/ROMs personalizados para el dispositivo (LineageOS/TWRP/…)",
        "fr": "Afficher les firmwares/ROMs personnalisés pour l'appareil (LineageOS/TWRP/…)",
        "pt": "Mostrar firmware/ROMs personalizados para o dispositivo (LineageOS/TWRP/…)",
        "it": "Mostra firmware/ROM personalizzati per il dispositivo (LineageOS/TWRP/…)",
        "tr": "Cihaz için özel firmware/ROM'ları göster (LineageOS/TWRP/…)",
        "ru": "Показать кастомные прошивки/ROMs для устройства (LineageOS/TWRP/…)",
    },
    "menu_P": {
        "de": "Bootloop-Live-Monitor (USB-Zyklen beobachten)",
        "en": "Bootloop live monitor (observe USB cycles)",
        "es": "Monitor en vivo de bootloop (observar ciclos USB)",
        "fr": "Moniteur bootloop en direct (observer les cycles USB)",
        "pt": "Monitor ao vivo de bootloop (observar ciclos USB)",
        "it": "Monitor live bootloop (osserva cicli USB)",
        "tr": "Bootloop canlı monitör (USB döngülerini izle)",
        "ru": "Монитор загрузочного цикла (наблюдение USB-циклов)",
    },
    "menu_Z": {
        "de": "AUTO-RESCUE – automatische Rettungs-/Flash-Kaskade",
        "en": "AUTO-RESCUE – automatic rescue/flash cascade",
        "es": "AUTO-RESCATE – cascada automática de rescate/flash",
        "fr": "AUTO-SAUVETAGE – cascade de sauvetage/flash automatique",
        "pt": "AUTO-RESGATE – cascata automática de resgate/flash",
        "it": "AUTO-SOCCORSO – cascata automatica soccorso/flash",
        "tr": "OTOMATİK KURTARMA – otomatik kurtarma/flash kaskadı",
        "ru": "АВТО-СПАСЕНИЕ – автоматический каскад спасения/прошивки",
    },
    "menu_L": {
        "de": "Live: Mobilfunk-Zellen-/IMSI-Monitor",
        "en": "Live: Cell tower / IMSI monitor",
        "es": "En vivo: Monitor de torres celulares / IMSI",
        "fr": "En direct : moniteur de cellules / IMSI",
        "pt": "Ao vivo: Monitor de torres celulares / IMSI",
        "it": "Live: Monitor celle / IMSI",
        "tr": "Canlı: Hücre kulesi / IMSI monitörü",
        "ru": "Онлайн: монитор сотовых вышек / IMSI",
    },
    "menu_N": {
        "de": "OSINT-Toolkit (Telefon/E-Mail/Username/Domain/KI-Analyst)",
        "en": "OSINT toolkit (phone/email/username/domain/AI analyst)",
        "es": "Kit de herramientas OSINT (teléfono/email/usuario/dominio/analista IA)",
        "fr": "Boîte à outils OSINT (téléphone/email/nom d'utilisateur/domaine/analyste IA)",
        "pt": "Kit de ferramentas OSINT (telefone/email/utilizador/domínio/analista IA)",
        "it": "Toolkit OSINT (telefono/email/username/dominio/analista IA)",
        "tr": "OSINT araç seti (telefon/e-posta/kullanıcı adı/domain/yapay zeka analisti)",
        "ru": "OSINT-инструментарий (телефон/email/имя пользователя/домен/ИИ-аналитик)",
    },
    "menu_W": {
        "de": "LABOR-EINRICHTUNG – alle Forensik-Tools installieren (apt/pip)",
        "en": "LAB SETUP – install all forensics tools (apt/pip)",
        "es": "CONFIGURACIÓN DE LABORATORIO – instalar todas las herramientas forenses (apt/pip)",
        "fr": "CONFIGURATION LABO – installer tous les outils forensiques (apt/pip)",
        "pt": "CONFIGURAÇÃO DO LABORATÓRIO – instalar todas as ferramentas forenses (apt/pip)",
        "it": "CONFIGURAZIONE LABORATORIO – installa tutti gli strumenti forensi (apt/pip)",
        "tr": "LAB KURULUMU – tüm adli araçları yükle (apt/pip)",
        "ru": "НАСТРОЙКА ЛАБОРАТОРИИ – установить все криминалистические инструменты (apt/pip)",
    },
    "menu_C": {
        "de": "Eigenes ADB-Shell-Kommando",
        "en": "Custom ADB shell command",
        "es": "Comando ADB shell personalizado",
        "fr": "Commande ADB shell personnalisée",
        "pt": "Comando ADB shell personalizado",
        "it": "Comando ADB shell personalizzato",
        "tr": "Özel ADB kabuk komutu",
        "ru": "Собственная команда ADB shell",
    },
    "menu_G": {
        "de": "Samsung Root/Odin · TWRP · Modul-Flasher",
        "en": "Samsung Root/Odin · TWRP · Module flasher",
        "es": "Samsung Root/Odin · TWRP · Flasher de módulos",
        "fr": "Samsung Root/Odin · TWRP · Flasheur de modules",
        "pt": "Samsung Root/Odin · TWRP · Flasher de módulos",
        "it": "Samsung Root/Odin · TWRP · Flasher moduli",
        "tr": "Samsung Root/Odin · TWRP · Modül flaşlayıcı",
        "ru": "Samsung Root/Odin · TWRP · Модульный прошивальщик",
    },
    "menu_M": {
        "de": "MediaTek Root (mtkclient/BROM, oft ohne Wipe)",
        "en": "MediaTek Root (mtkclient/BROM, often without wipe)",
        "es": "Root MediaTek (mtkclient/BROM, a menudo sin wipe)",
        "fr": "Root MediaTek (mtkclient/BROM, souvent sans wipe)",
        "pt": "Root MediaTek (mtkclient/BROM, frequentemente sem wipe)",
        "it": "Root MediaTek (mtkclient/BROM, spesso senza wipe)",
        "tr": "MediaTek Root (mtkclient/BROM, çoğunlukla silme yok)",
        "ru": "MediaTek Root (mtkclient/BROM, часто без wipe)",
    },
    "menu_H": {
        "de": "Xiaomi/MIUI – Mi Unlock · Fastboot-Root-Assistent",
        "en": "Xiaomi/MIUI – Mi Unlock · Fastboot root assistant",
        "es": "Xiaomi/MIUI – Mi Unlock · Asistente root Fastboot",
        "fr": "Xiaomi/MIUI – Mi Unlock · Assistant root Fastboot",
        "pt": "Xiaomi/MIUI – Mi Unlock · Assistente root Fastboot",
        "it": "Xiaomi/MIUI – Mi Unlock · Assistente root Fastboot",
        "tr": "Xiaomi/MIUI – Mi Unlock · Fastboot root asistanı",
        "ru": "Xiaomi/MIUI – Mi Unlock · Помощник Fastboot-рутинга",
    },
    "menu_H_pixel": {
        "de": "Google Pixel – Fastboot Unlock · init_boot / boot.img patchen",
        "en": "Google Pixel – Fastboot unlock · patch init_boot / boot.img",
        "es": "Google Pixel – Fastboot Unlock · parchear init_boot / boot.img",
        "fr": "Google Pixel – Fastboot Unlock · patcher init_boot / boot.img",
        "pt": "Google Pixel – Fastboot Unlock · patchar init_boot / boot.img",
        "it": "Google Pixel – Fastboot Unlock · patching init_boot / boot.img",
        "tr": "Google Pixel – Fastboot Unlock · init_boot / boot.img yamala",
        "ru": "Google Pixel – Fastboot Unlock · патч init_boot / boot.img",
    },
    "menu_H_oneplus": {
        "de": "OnePlus/OPPO/Realme – Fastboot Unlock · Magisk-Root",
        "en": "OnePlus/OPPO/Realme – Fastboot unlock · Magisk root",
        "es": "OnePlus/OPPO/Realme – Fastboot Unlock · Root Magisk",
        "fr": "OnePlus/OPPO/Realme – Fastboot Unlock · Root Magisk",
        "pt": "OnePlus/OPPO/Realme – Fastboot Unlock · Root Magisk",
        "it": "OnePlus/OPPO/Realme – Fastboot Unlock · Root Magisk",
        "tr": "OnePlus/OPPO/Realme – Fastboot Unlock · Magisk root",
        "ru": "OnePlus/OPPO/Realme – Fastboot Unlock · Root Magisk",
    },
    "menu_H_motorola": {
        "de": "Motorola – Unlock-Code anfordern · Fastboot-Root",
        "en": "Motorola – Request unlock code · Fastboot root",
        "es": "Motorola – Solicitar código de desbloqueo · Root Fastboot",
        "fr": "Motorola – Demander un code de déverrouillage · Root Fastboot",
        "pt": "Motorola – Pedir código de desbloqueio · Root Fastboot",
        "it": "Motorola – Richiedere codice di sblocco · Root Fastboot",
        "tr": "Motorola – Kilit açma kodu talep et · Fastboot root",
        "ru": "Motorola – Запросить код разблокировки · Fastboot root",
    },
    "menu_H_huawei": {
        "de": "Huawei/Honor – Einschränkungen & Optionen",
        "en": "Huawei/Honor – Restrictions & options",
        "es": "Huawei/Honor – Restricciones y opciones",
        "fr": "Huawei/Honor – Restrictions et options",
        "pt": "Huawei/Honor – Restrições e opções",
        "it": "Huawei/Honor – Restrizioni e opzioni",
        "tr": "Huawei/Honor – Kısıtlamalar ve seçenekler",
        "ru": "Huawei/Honor – Ограничения и варианты",
    },
    "menu_I": {
        "de": "KI-ADB-Shell (lokal · ollama)",
        "en": "AI ADB shell (local · ollama)",
        "es": "Shell ADB con IA (local · ollama)",
        "fr": "Shell ADB IA (local · ollama)",
        "pt": "Shell ADB com IA (local · ollama)",
        "it": "Shell ADB con IA (locale · ollama)",
        "tr": "Yapay zeka ADB kabuğu (yerel · ollama)",
        "ru": "ИИ-оболочка ADB (локально · ollama)",
    },

    # ── main.py: _run_feature() ─────────────────────────────────────────────
    "feature_root_required": {
        "de": "Diese Funktion benötigt Root.",
        "en": "This feature requires root.",
        "es": "Esta función requiere root.",
        "fr": "Cette fonctionnalité nécessite le root.",
        "pt": "Esta função requer root.",
        "it": "Questa funzione richiede il root.",
        "tr": "Bu özellik root gerektirir.",
        "ru": "Для этой функции необходим root.",
    },
    "feature_root_hint": {
        "de": "Root-Status/Assistent: Hauptmenü → R",
        "en": "Root status/assistant: main menu → R",
        "es": "Estado root/asistente: menú principal → R",
        "fr": "État root/assistant : menu principal → R",
        "pt": "Estado root/assistente: menu principal → R",
        "it": "Stato root/assistente: menu principale → R",
        "tr": "Root durumu/asistanı: ana menü → R",
        "ru": "Статус root/помощник: главное меню → R",
    },
    "feature_try_no_root": {
        "de": "Trotzdem ohne Root versuchen (read-only Teil)?",
        "en": "Try anyway without root (read-only part)?",
        "es": "¿Intentar igualmente sin root (parte de solo lectura)?",
        "fr": "Essayer quand même sans root (partie lecture seule) ?",
        "pt": "Tentar mesmo assim sem root (parte só de leitura)?",
        "it": "Provare comunque senza root (parte sola lettura)?",
        "tr": "Yine de root olmadan dene (salt okunur kısım)?",
        "ru": "Попробовать без root (только чтение)?",
    },
    "feature_aborted": {
        "de": "Abgebrochen.",  "en": "Cancelled.",    "es": "Cancelado.",
        "fr": "Annulé.",       "pt": "Cancelado.",    "it": "Annullato.",
        "tr": "İptal edildi.", "ru": "Отменено.",
    },
    "feature_executing": {
        "de": "Führe aus:",  "en": "Executing:",   "es": "Ejecutando:",
        "fr": "Exécution :", "pt": "A executar:",  "it": "Esecuzione:",
        "tr": "Çalıştırılıyor:", "ru": "Выполняется:",
    },
    "feature_executed": {
        "de": "(ausgeführt)", "en": "(executed)", "es": "(ejecutado)",
        "fr": "(exécuté)",    "pt": "(executado)", "it": "(eseguito)",
        "tr": "(çalıştırıldı)", "ru": "(выполнено)",
    },
    "feature_sdr_required": {
        "de": "Spezial-Hardware / SDR erforderlich:",
        "en": "Special hardware / SDR required:",
        "es": "Se requiere hardware especial / SDR:",
        "fr": "Matériel spécial / SDR requis :",
        "pt": "Hardware especial / SDR necessário:",
        "it": "Hardware speciale / SDR richiesto:",
        "tr": "Özel donanım / SDR gerekli:",
        "ru": "Требуется специальное оборудование / SDR:",
    },
    "feature_destructive": {
        "de": "DESTRUKTIV / IRREVERSIBEL",
        "en": "DESTRUCTIVE / IRREVERSIBLE",
        "es": "DESTRUCTIVO / IRREVERSIBLE",
        "fr": "DESTRUCTIF / IRRÉVERSIBLE",
        "pt": "DESTRUTIVO / IRREVERSÍVEL",
        "it": "DISTRUTTIVO / IRREVERSIBILE",
        "tr": "YIKICI / GERİ ALINAMAZ",
        "ru": "ДЕСТРУКТИВНО / НЕОБРАТИМО",
    },
    "feature_destructive_note": {
        "de": "Aus Sicherheitsgründen nicht automatisiert. Erfordert bewusste manuelle Ausführung.",
        "en": "Not automated for safety reasons. Requires deliberate manual execution.",
        "es": "No automatizado por razones de seguridad. Requiere ejecución manual deliberada.",
        "fr": "Non automatisé pour des raisons de sécurité. Nécessite une exécution manuelle délibérée.",
        "pt": "Não automatizado por razões de segurança. Requer execução manual deliberada.",
        "it": "Non automatizzato per motivi di sicurezza. Richiede esecuzione manuale deliberata.",
        "tr": "Güvenlik nedeniyle otomatikleştirilmedi. Bilinçli manuel yürütme gerektirir.",
        "ru": "Не автоматизировано по соображениям безопасности. Требует осознанного ручного выполнения.",
    },
    "feature_adb_error": {
        "de": "ADB-Fehler:", "en": "ADB error:", "es": "Error ADB:",
        "fr": "Erreur ADB :", "pt": "Erro ADB:", "it": "Errore ADB:",
        "tr": "ADB hatası:", "ru": "Ошибка ADB:",
    },
    "feature_aborted_ctrl_c": {
        "de": "Abgebrochen.", "en": "Aborted.", "es": "Cancelado.",
        "fr": "Annulé.",     "pt": "Cancelado.", "it": "Annullato.",
        "tr": "İptal edildi.", "ru": "Прервано.",
    },
    "feature_error": {
        "de": "Fehler:", "en": "Error:", "es": "Error:", "fr": "Erreur :",
        "pt": "Erro:", "it": "Errore:", "tr": "Hata:", "ru": "Ошибка:",
    },

    # ── _category_menu() ────────────────────────────────────────────────────
    "cat_overview_title": {
        "de": "Alle 45 Kategorien · 450 Funktionen",
        "en": "All 45 categories · 450 features",
        "es": "Todas las 45 categorías · 450 funciones",
        "fr": "Toutes les 45 catégories · 450 fonctionnalités",
        "pt": "Todas as 45 categorias · 450 funções",
        "it": "Tutte le 45 categorie · 450 funzioni",
        "tr": "Tüm 45 kategori · 450 özellik",
        "ru": "Все 45 категорий · 450 функций",
    },
    "cat_back": {
        "de": "Kategorie-Übersicht",   "en": "Category overview",
        "es": "Resumen de categorías", "fr": "Vue d'ensemble des catégories",
        "pt": "Visão geral das categorias", "it": "Panoramica categorie",
        "tr": "Kategori genel bakış",  "ru": "Обзор категорий",
    },
    "cat_ask": {
        "de": "Kategorie-Nr (1-45)",   "en": "Category no. (1-45)",
        "es": "Nº de categoría (1-45)", "fr": "N° de catégorie (1-45)",
        "pt": "Nº de categoria (1-45)", "it": "N° di categoria (1-45)",
        "tr": "Kategori no. (1-45)",   "ru": "Номер категории (1-45)",
    },
    "cat_out_of_range": {
        "de": "Außerhalb 1-45.",    "en": "Outside 1-45.",
        "es": "Fuera del rango 1-45.", "fr": "Hors de 1-45.",
        "pt": "Fora de 1-45.",      "it": "Fuori dall'intervallo 1-45.",
        "tr": "1-45 dışında.",      "ru": "Вне диапазона 1-45.",
    },
    "cat_enter_number": {
        "de": "Bitte Zahl eingeben.",  "en": "Please enter a number.",
        "es": "Por favor ingresa un número.", "fr": "Veuillez entrer un nombre.",
        "pt": "Por favor, introduza um número.", "it": "Inserire un numero.",
        "tr": "Lütfen bir sayı girin.", "ru": "Пожалуйста, введите число.",
    },

    # ── depth engine ────────────────────────────────────────────────────────
    "depth_title": {
        "de": "Tiefen-Engine",   "en": "Deep Engine",       "es": "Motor Profundo",
        "fr": "Moteur Profond",  "pt": "Motor Profundo",    "it": "Motore Profondo",
        "tr": "Derin Motor",     "ru": "Глубокий движок",
    },
    "depth_frida_note": {
        "de": "Frida ist das Fundament: holt Klartext-Keys/Passwörter & bricht SSL-Pinning.\n",
        "en": "Frida is the foundation: extracts plaintext keys/passwords & breaks SSL pinning.\n",
        "es": "Frida es la base: extrae claves/contraseñas en texto claro y rompe el SSL pinning.\n",
        "fr": "Frida est le fondement : extrait les clés/mots de passe en clair et contourne le SSL pinning.\n",
        "pt": "O Frida é a base: extrai chaves/palavras-passe em texto claro e quebra o SSL pinning.\n",
        "it": "Frida è il fondamento: estrae chiavi/password in chiaro e rompe l'SSL pinning.\n",
        "tr": "Frida temeldir: düz metin anahtarlar/parolalar çıkarır ve SSL pinning'i kırar.\n",
        "ru": "Frida — основа: извлекает ключи/пароли в открытом виде и обходит SSL pinning.\n",
    },

    # ── ADB-Konsole ─────────────────────────────────────────────────────────
    "adb_console_title": {
        "de": "ADB-Konsole",    "en": "ADB console",    "es": "Consola ADB",
        "fr": "Console ADB",    "pt": "Consola ADB",    "it": "Console ADB",
        "tr": "ADB konsolu",    "ru": "Консоль ADB",
    },
    "adb_console_interactive": {
        "de": "Interaktive ADB-Shell (echte Shell, wie 'adb shell')",
        "en": "Interactive ADB shell (real shell, like 'adb shell')",
        "es": "Shell ADB interactiva (shell real, como 'adb shell')",
        "fr": "Shell ADB interactif (vrai shell, comme 'adb shell')",
        "pt": "Shell ADB interativa (shell real, como 'adb shell')",
        "it": "Shell ADB interattiva (shell reale, come 'adb shell')",
        "tr": "Etkileşimli ADB kabuğu (gerçek kabuk, 'adb shell' gibi)",
        "ru": "Интерактивная ADB-оболочка (настоящий shell, как 'adb shell')",
    },
    "adb_console_single": {
        "de": "Einzelkommando ausführen",        "en": "Run single command",
        "es": "Ejecutar comando único",          "fr": "Exécuter une commande unique",
        "pt": "Executar comando único",          "it": "Esegui comando singolo",
        "tr": "Tek komut çalıştır",              "ru": "Выполнить одну команду",
    },
    "adb_console_interactive_hint": {
        "de": "Interaktive Shell – 'exit' oder STRG+D kehrt ins Panzer-Menü zurück.\n",
        "en": "Interactive shell – 'exit' or CTRL+D returns to Panzer menu.\n",
        "es": "Shell interactiva – 'exit' o CTRL+D vuelve al menú Panzer.\n",
        "fr": "Shell interactif – 'exit' ou CTRL+D retourne au menu Panzer.\n",
        "pt": "Shell interativa – 'exit' ou CTRL+D volta ao menu Panzer.\n",
        "it": "Shell interattiva – 'exit' o CTRL+D torna al menu Panzer.\n",
        "tr": "Etkileşimli kabuk – 'exit' veya CTRL+D Panzer menüsüne döner.\n",
        "ru": "Интерактивная оболочка – 'exit' или CTRL+D возвращает в меню Panzer.\n",
    },
    "adb_console_back_hint": {
        "de": "Zurück im Panzer-Menü – ENTER",    "en": "Back in Panzer menu – ENTER",
        "es": "De vuelta al menú Panzer – ENTER",  "fr": "Retour au menu Panzer – ENTRÉE",
        "pt": "De volta ao menu Panzer – ENTER",   "it": "Di ritorno al menu Panzer – INVIO",
        "tr": "Panzer menüsüne geri – ENTER",      "ru": "Назад в меню Panzer – ENTER",
    },
    "adb_console_cmd_prompt": {
        "de": "Kommando",  "en": "Command",  "es": "Comando",  "fr": "Commande",
        "pt": "Comando",   "it": "Comando",  "tr": "Komut",    "ru": "Команда",
    },
    "adb_console_as_root": {
        "de": "Als Root (su) ausführen?",          "en": "Execute as root (su)?",
        "es": "¿Ejecutar como root (su)?",         "fr": "Exécuter en tant que root (su) ?",
        "pt": "Executar como root (su)?",          "it": "Esegui come root (su)?",
        "tr": "Root olarak (su) çalıştır?",        "ru": "Выполнить от root (su)?",
    },

    # ── brands.py ──────────────────────────────────────────────────────────
    "brand_assistant_title": {
        "de": "Hersteller-Assistent",       "en": "Brand assistant",
        "es": "Asistente del fabricante",   "fr": "Assistant fabricant",
        "pt": "Assistente do fabricante",   "it": "Assistente produttore",
        "tr": "Üretici asistanı",           "ru": "Помощник по производителю",
    },
    "brand_continue_rooting": {
        "de": "Zum Rooting-Assistenten wechseln (Hauptmenü → R)?",
        "en": "Switch to rooting assistant (main menu → R)?",
        "es": "¿Ir al asistente de rooting (menú principal → R)?",
        "fr": "Passer à l'assistant de rootage (menu principal → R) ?",
        "pt": "Ir para o assistente de rooting (menu principal → R)?",
        "it": "Passare all'assistente di rooting (menu principale → R)?",
        "tr": "Rooting asistanına geç (ana menü → R)?",
        "ru": "Перейти к помощнику рутинга (главное меню → R)?",
    },

    # ── panzer.py ───────────────────────────────────────────────────────────
    "startup_aborted": {
        "de": "Android Panzer abgebrochen. Stay safe.",
        "en": "Android Panzer aborted. Stay safe.",
        "es": "Android Panzer cancelado. Mantente seguro.",
        "fr": "Android Panzer interrompu. Restez prudent.",
        "pt": "Android Panzer interrompido. Fica em segurança.",
        "it": "Android Panzer interrotto. Stai al sicuro.",
        "tr": "Android Panzer durduruldu. Güvende kal.",
        "ru": "Android Panzer прерван. Будьте осторожны.",
    },
}
