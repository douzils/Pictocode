#!/bin/sh
# Script de lancement pour Pictocode sous Linux/Debian
set -e
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
cd "$SCRIPT_DIR"

if ! command -v pictocode >/dev/null 2>&1; then
    echo "ERREUR : l'exécutable pictocode est introuvable."
    echo "Installez-le d'abord avec 'pip install .' depuis ce dossier."
    exit 1
fi

echo "[pictocode] Lancement de Pictocode…"
pictocode "$@"
status=$?
if [ $status -ne 0 ]; then
    echo "\nERREUR : échec du lancement de Pictocode."
else
    echo "\nPictocode s'est terminé normalement."
fi
