#!/bin/sh
# ——— Placez ce script à la racine du dossier pictocode ———
cd "$(dirname "$0")"

echo "[pictocode] Vérification de pictocode..."
if command -v pictocode >/dev/null 2>&1; then
    CMD="pictocode"
elif [ -f pictocode/__main__.py ]; then
    CMD="python3 -m pictocode"
else
    echo "ERREUR : pictocode introuvable."
    echo "Assurez-vous que le script pictocode est installé dans votre Python/bin."
    exit 1
fi

python3 - <<'EOF'
import sys
try:
    import PyQt5 # noqa: F401
except Exception:
    sys.exit(1)
EOF
CHECK_STATUS=$?
if [ $CHECK_STATUS -ne 0 ]; then
    echo "ERREUR : la dépendance PyQt5 est manquante."
    echo "Exécutez : pip install -r requirements.txt"
    exit 1
fi

echo "[pictocode] Lancement de pictocode…"
$CMD "$@"
STATUS=$?

if [ $STATUS -ne 0 ]; then
    echo
    echo "ERREUR : échec du lancement de pictocode."
else
    echo
    echo "pictocode s’est terminé normalement."
fi

exit $STATUS
