#!/usr/bin/env bash
set -o errexit

# Installation des dépendances système pour WeasyPrint (Linux/Render)
apt-get update && apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 libgdk-pixbuf-2.0-0 shared-mime-info

# Installation des dépendances Python
pip install -r requirements.txt

# Collecte des fichiers statiques
python manage.py collectstatic --no-input

# Application des migrations
python manage.py migrate