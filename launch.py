#!/usr/bin/env python3
"""
Script de lancement amélioré pour VibeVoice
Gère les erreurs et fournit des messages informatifs
"""

import sys
import os
import subprocess
import time
import signal
from pathlib import Path

def check_python_version():
    """Vérifie la version de Python"""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ requis. Version actuelle:", sys.version)
        return False
    return True

def check_requirements():
    """Vérifie que requirements.txt existe"""
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("❌ Fichier requirements.txt introuvable")
        return False
    return True

def install_dependencies():
    """Installe les dépendances si nécessaire"""
    try:
        print("🔍 Vérification des dépendances...")
        result = subprocess.run([
            sys.executable, "-c", 
            "import fastapi, uvicorn, faster_whisper, sounddevice, requests, numpy, pynput, scipy"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("📦 Installation des dépendances...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ Dépendances installées")
        else:
            print("✅ Dépendances déjà installées")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation: {e}")
        return False

def kill_existing_processes():
    """Tue les processus existants qui pourraient bloquer les ports"""
    try:
        # Chercher les processus sur le port 4242
        result = subprocess.run(["lsof", "-ti:4242"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"🔄 Arrêt du processus {pid} sur le port 4242...")
                    subprocess.run(["kill", "-9", pid], capture_output=True)
            time.sleep(1)
    except Exception as e:
        print(f"⚠️  Impossible de vérifier les processus existants: {e}")

def main():
    print("🎙️  VibeVoice - Lancement amélioré")
    print("=" * 50)
    
    # Vérifications préliminaires
    if not check_python_version():
        sys.exit(1)
    
    if not check_requirements():
        sys.exit(1)
    
    # Nettoyer les processus existants
    kill_existing_processes()
    
    # Installer les dépendances
    if not install_dependencies():
        sys.exit(1)
    
    print("\n🚀 Lancement de VibeVoice...")
    print("=" * 50)
    
    try:
        # Lancer l'application principale
        subprocess.run([sys.executable, "src/vibevoice/cli.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erreur lors du lancement: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
