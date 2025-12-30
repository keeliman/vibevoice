#!/usr/bin/env python3
"""
Script de nettoyage pour VibeVoice
Arrête tous les processus liés à VibeVoice
"""

import subprocess
import sys
import time

# Import configuration
try:
    from src.vibevoice.config import ALL_PORTS
except ImportError:
    # Fallback if import fails
    ALL_PORTS = list(range(4242, 4252))

def kill_processes_on_ports():
    """Tue les processus sur les ports utilisés par VibeVoice"""
    ports = ALL_PORTS
    
    for port in ports:
        try:
            result = subprocess.run(["lsof", f"-ti:{port}"], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        print(f"🔄 Arrêt du processus {pid} sur le port {port}...")
                        subprocess.run(["kill", "-9", pid], capture_output=True)
        except Exception as e:
            print(f"⚠️  Erreur lors de la vérification du port {port}: {e}")

def kill_python_processes():
    """Tue les processus Python liés à VibeVoice"""
    try:
        # Chercher les processus Python qui contiennent "vibevoice" ou "server.py"
        result = subprocess.run([
            "ps", "aux"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'vibevoice' in line.lower() or 'server.py' in line:
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        print(f"🔄 Arrêt du processus Python {pid}...")
                        subprocess.run(["kill", "-9", pid], capture_output=True)
    except Exception as e:
        print(f"⚠️  Erreur lors de la recherche des processus Python: {e}")

def main():
    print("🧹 Nettoyage de VibeVoice...")
    print("=" * 40)
    
    print("🔍 Recherche des processus sur les ports...")
    kill_processes_on_ports()
    
    print("🔍 Recherche des processus Python...")
    kill_python_processes()
    
    print("⏳ Attente de 2 secondes...")
    time.sleep(2)
    
    print("✅ Nettoyage terminé")
    print("💡 Vous pouvez maintenant relancer VibeVoice")

if __name__ == "__main__":
    main()
