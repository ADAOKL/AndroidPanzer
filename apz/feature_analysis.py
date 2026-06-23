"""Feature-Analyse-Engine: Intelligente Ergebnis-Parsing & Visualisierung.

Parst und analysiert die Ausgabe von ADB-Kommandos und präsentiert
strukturierte, lesbare Ergebnisse im Dashboard-Format.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from . import ui
from .dashboard_feature import FeatureDashboard


class FeatureAnalyzer:
    """Analysiert Ausgaben von Features und extrahiert verwertbare Daten."""

    @staticmethod
    def parse_meminfo(output: str) -> dict[str, Any]:
        """Parst 'df -h' und 'dumpsys meminfo' Ausgabe."""
        results = {}

        # Total Memory
        total_match = re.search(r'Total:\s+(\d+)\s+KB', output)
        if total_match:
            mb = int(total_match.group(1)) // 1024
            results['RAM_Total'] = f"{mb} MB"

        # Used Memory
        used_match = re.search(r'Used:\s+(\d+)\s+KB', output)
        if used_match:
            mb = int(used_match.group(1)) // 1024
            results['RAM_Used'] = f"{mb} MB"

        # Free Memory
        free_match = re.search(r'Free:\s+(\d+)\s+KB', output)
        if free_match:
            mb = int(free_match.group(1)) // 1024
            results['RAM_Free'] = f"{mb} MB"

        return results

    @staticmethod
    def parse_cpu_info(output: str) -> dict[str, Any]:
        """Parst CPU-Frequenzen und Top-Prozesse."""
        results = {}
        lines = output.split('\n')

        # Extract frequencies
        freqs = []
        for line in lines:
            if line.strip().isdigit() and len(line.strip()) > 6:
                try:
                    freq_khz = int(line.strip())
                    freq_mhz = freq_khz // 1000
                    if 100 < freq_mhz < 5000:  # Reasonable range
                        freqs.append(freq_mhz)
                except:
                    pass

        if freqs:
            results['CPU_Frequencies'] = {
                'Min': f"{min(freqs)} MHz",
                'Max': f"{max(freqs)} MHz",
                'Avg': f"{sum(freqs) // len(freqs)} MHz",
            }

        # Top processes
        top_section = output.split('---')
        if len(top_section) > 1:
            processes = []
            for line in top_section[0].split('\n')[1:6]:
                if line.strip():
                    parts = line.split()
                    if len(parts) > 1:
                        processes.append(f"{parts[-1]} ({parts[0]}%)")
            if processes:
                results['Top_Processes'] = processes

        return results

    @staticmethod
    def parse_battery_info(output: str) -> dict[str, Any]:
        """Parst Batterie-Informationen."""
        results = {}

        patterns = {
            'Level': r'level:\s*(\d+)',
            'Temperature': r'temperature:\s*(\d+)',
            'Voltage': r'voltage:\s*(\d+)',
            'Health': r'health:\s*(\w+)',
            'Status': r'status:\s*(\w+)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                val = match.group(1)
                if key == 'Level':
                    results[key] = f"{val}%"
                elif key == 'Temperature':
                    results[key] = f"{val}°C"
                elif key == 'Voltage':
                    results[key] = f"{int(val) // 1000} V"
                else:
                    results[key] = val

        return results

    @staticmethod
    def parse_network_info(output: str) -> dict[str, Any]:
        """Parst Netzwerk-Informationen."""
        results = {}

        # IPv4
        ipv4_match = re.search(r'inet\s+([\d.]+)', output)
        if ipv4_match:
            results['IPv4'] = ipv4_match.group(1)

        # MAC
        mac_match = re.search(r'link/ether\s+([\da-f:]+)', output)
        if mac_match:
            results['MAC_Address'] = mac_match.group(1).upper()

        # WiFi Info
        wifi_patterns = {
            'RSSI': r'rssi=(-?\d+)',
            'Link_Speed': r'link speed:\s*(\d+)',
            'SSID': r"SSID:\s*'?([^']*)'?",
        }

        for key, pattern in wifi_patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                val = match.group(1)
                if key == 'Link_Speed':
                    results[key] = f"{val} Mbps"
                else:
                    results[key] = val

        return results

    @staticmethod
    def parse_sim_info(output: str) -> dict[str, Any]:
        """Parst SIM/Mobilfunk-Informationen."""
        results = {}

        patterns = {
            'Operator': r'operator[_\s]*name[:\s=]*([^\n]+)',
            'MCC_MNC': r'(mcc|mnc)[:\s=]*(\d+)',
            'Signal_Strength': r'signal.*strength[:\s=]*(-?\d+)',
            'Network_Type': r'network[_\s]*type[:\s=]*([^\n]+)',
            'State': r'sim[_\s]*state[:\s=]*([^\n]+)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                val = match.group(1) if key != 'MCC_MNC' else match.group(2)
                if key == 'Signal_Strength':
                    try:
                        strength = int(val)
                        bars = strength // 2 if strength else 0
                        results[key] = f"{strength} ({ui.BGREEN}{'▓' * bars}{ui.RESET})"
                    except:
                        results[key] = val
                else:
                    results[key] = val

        return results

    @staticmethod
    def parse_generic_table(output: str, delimiter: str = '\t') -> dict[str, list]:
        """Parst allgemeine tabellarische Ausgaben."""
        results = {'rows': []}

        lines = [l.strip() for l in output.split('\n') if l.strip()]
        for line in lines[:20]:  # Limit to first 20 rows
            results['rows'].append(line)

        results['total_lines'] = len(lines)
        return results


def analyze_feature_output(dashboard: FeatureDashboard, output: str,
                          feature_kind: str, feature_title: str) -> None:
    """Analysiert die Ausgabe eines Features automatisch."""
    title_lower = feature_title.lower()

    # Route to appropriate analyzer
    if 'speicher' in title_lower or 'meminfo' in output.lower():
        data = FeatureAnalyzer.parse_meminfo(output)
        if data:
            dashboard.add_result('Memory_Analysis', data, 'RAM-Analyse')

    elif 'cpu' in title_lower or 'top' in output.lower():
        data = FeatureAnalyzer.parse_cpu_info(output)
        if data:
            dashboard.add_result('CPU_Analysis', data, 'CPU-Analyse')

    elif 'akku' in title_lower or 'battery' in output.lower():
        data = FeatureAnalyzer.parse_battery_info(output)
        if data:
            dashboard.add_result('Battery_Analysis', data, 'Batterie-Analyse')

    elif 'netzwerk' in title_lower or 'wifi' in output.lower():
        data = FeatureAnalyzer.parse_network_info(output)
        if data:
            dashboard.add_result('Network_Analysis', data, 'Netzwerk-Analyse')

    elif 'sim' in title_lower or 'imsi' in output.lower():
        data = FeatureAnalyzer.parse_sim_info(output)
        if data:
            dashboard.add_result('SIM_Analysis', data, 'SIM/Mobilfunk-Analyse')

    else:
        # Generic table parsing
        data = FeatureAnalyzer.parse_generic_table(output)
        if data['rows']:
            dashboard.add_result('Output', f"{data['total_lines']} Zeilen geparst", 'Ausgabe')

    # Add raw output if substantial
    if len(output) > 500:
        dashboard.add_result('Output_Size', f"{len(output)} Bytes", 'Rohdaten-Größe')
