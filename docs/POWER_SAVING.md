# Économie d'Énergie - VibeVoice

Ce document explique les options d'économie d'énergie de VibeVoice pour réduire la consommation de batterie.

## Le Problème

Par défaut, VibeVoice consomme beaucoup d'énergie car :
- **WhisperModel "medium"** (~2GB RAM) chargé en permanence
- **Serveur FastAPI** qui tourne 24/7
- **Enregistrement audio continu** même au repos

## Solutions Implémentées

### 1. Lazy Loading du Modèle Whisper

Le modèle n'est plus chargé au démarrage mais seulement lors de la **première transcription**.

**Avantages :**
- Économie ~1-2GB RAM au repos
- Démarrage plus rapide
- Meilleure autonomie

**Configuration :**
```bash
# Activer/désactiver (défaut: true)
export VIBEVOICE_LAZY_LOAD=true

# Choisir la taille du modèle
export WHISPER_MODEL=base    # ~140MB, rapide, bonne précision
export WHISPER_MODEL=small   # ~460MB, équilibré
export WHISPER_MODEL=medium  # ~1.5GB, plus précis (défaut avant)
export WHISPER_MODEL=tiny    # ~70MB, très rapide, moins précis
```

**Comparaison des modèles :**
| Modèle | Taille | RAM | Vitesse | Précision |
|--------|-------|-----|---------|-----------|
| tiny | 70MB | ~200MB | ⚡⚡⚡ | ** |
| base | 140MB | ~400MB | ⚡⚡ | *** |
| small | 460MB | ~800MB | ⚡ | **** |
| medium | 1.5GB | ~2GB | - | ***** |

### 2. Arrêt Automatique par Inactivité

Le serveur s'arrête automatiquement après une période d'inactivité.

**Configuration :**
```bash
# Durée avant arrêt (secondes)
# 0 = désactivé, 300 = 5 minutes (défaut)
export VIBEVOICE_IDLE_TIMEOUT=300

# Désactiver l'arrêt automatique
export VIBEVOICE_IDLE_TIMEOUT=0
```

### 3. Mode Économie d'Énergie

Réduit la consommation CPU quand l'app est au repos.

**Configuration :**
```bash
export VIBEVOICE_POWER_SAVE=true  # défaut
```

## Utilisation Recommandée

### Mode Ultra-Éco (Maximum Autonomie)
```bash
export WHISPER_MODEL=tiny
export VIBEVOICE_IDLE_TIMEOUT=60  # 1 minute
export VIBEVOICE_POWER_SAVE=true
python launch.py
```

### Mode Équilibré (Recommandé)
```bash
export WHISPER_MODEL=base
export VIBEVOICE_IDLE_TIMEOUT=300  # 5 minutes
export VIBEVOICE_POWER_SAVE=true
python launch.py
```

### Mode Performance (Plus Précis)
```bash
export WHISPER_MODEL=small
export VIBEVOICE_IDLE_TIMEOUT=0  # Pas d'arrêt auto
python launch.py
```

## Fichier .env Exemple

Créez un fichier `.env` à la racine du projet :

```bash
# Mode éco-énergie
WHISPER_MODEL=base
VIBEVOICE_IDLE_TIMEOUT=300
VIBEVOICE_LAZY_LOAD=true
VIBEVOICE_POWER_SAVE=true

# Clavier
VOICEKEY=cmd_r
VOICEKEY_CMD=f12
VOICEKEY_SCREENSHOT=alt_r

# Ollama
OLLAMA_MODEL=gemma3:27b
INCLUDE_SCREENSHOT=false
```

## Comparaison de Consommation

| Configuration | Repos | Transcription | Batterie (1h) |
|---------------|-------|---------------|---------------|
| **Avant** (medium, 24/7) | 15-20% CPU | 100% CPU | ~30% |
| **Éco** (base, lazy) | 0-2% CPU | 50-80% CPU | ~5-8% |
| **Ultra-éco** (tiny, 1min) | ~0% CPU | 30-50% CPU | ~3-5% |

## Conseils Additionnels

1. **Utilisez le mode "base"** - Meilleur rapport qualité/batterie
2. **Arrêtez l'app quand vous ne l'utilisez pas** - Même avec idle timeout
3. **Réduisez la fréquence des screenshots** - `INCLUDE_SCREENSHOT=false`
4. **Utilisez un modèle Ollama plus léger** pour les commandes IA
5. **Sur MacBook** : activez "Mode économie d'énergie" dans les réglages macOS

## Monitoring

Pour voir la consommation en temps réel :
```bash
# Activity Monitor → Rechercher "python"
# ou
sudo powermetrics --samplers cpu_power -i 1000
```
