# GifConverter

Petit outil avec interface graphique moderne pour convertir une vidéo en GIF.

## Prérequis

- Python 3.10+
- ffmpeg installé (ex: `sudo dnf install ffmpeg`)

## Installation

```bash
pip install -r requirements.txt
```

## Lancer

```bash
python3 main.py
```

## Fonctionnalités

- Interface moderne sombre (CustomTkinter)
- Réglage FPS avec slider
- Redimensionnement (largeur/hauteur)
- Sélection du segment (début/fin en secondes)
- Barre de progression animée
- Affichage de la taille finale du GIF

## Notes

- Le champ largeur/hauteur à `0` conserve la dimension auto.
- Le filtre utilise palettegen/paletteuse pour une meilleure qualité.
- Par défaut, la largeur est de 480px pour des GIFs plus légers.
