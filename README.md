# Pictocode

Pictocode est une application permettant de composer visuellement des formes pour ensuite générer du code. Son interface rappelle les logiciels de dessin comme Illustrator.

Ce dépôt contient **l'intégralité du code source** de l'application. Les modules Python se trouvent dans le package `pictocode` et implémentent l'ensemble des fonctionnalités décrites ci-dessous.

## Fonctionnalités principales

### Écran d'accueil
- Interface modernisée avec en‑tête coloré.
- Bouton **Nouveau projet** pour créer un canvas vierge.
- Liste des projets sauvegardés dans le dossier `Projects` avec icônes.
- Liste de modèles et formats disponibles (double-cliquez pour préremplir la création de projet).
- Recherche instantanée pour retrouver rapidement un projet existant.


### Création d'un projet
- Fenêtre de création avec choix du nom, des dimensions et de l'unité.
- Orientation portrait ou paysage.
- Mode couleur (RGB, CMJN ou niveaux de gris).
- Résolution en DPI.

### Barre de menu
- **Fichier** : nouveau projet, ouvrir, enregistrer, enregistrer sous, retour à l'accueil et quitter l'application.
- **Projet** : paramètres du projet en cours.
- **Préférences** : réglages généraux et apparence (thème clair ou sombre).

### Fenêtre de paramètres
- **Général** : choix de la langue.
- **Apparence** : personnalisation fine de l'interface. Chaque zone (menu, barre d'outils, inspecteur) peut
  avoir sa propre couleur d'accent et sa taille de police.

### Dans un projet
- Canvas avec grille optionnelle et magnétisme. La grille s'adapte à
  l'échelle de zoom pour conserver un espacement lisible.
- Outils : rectangle, ellipse, ligne, polygone, tracé libre, texte, sélection et gomme.
- Choix de la couleur des formes.
- Clic droit sur une forme pour modifier couleur, remplissage ou bordure.
- Zoom à la molette et déplacement (pan). Utilisez l'outil **Pan** de la barre
  d'outils ou un clic molette pour déplacer temporairement la vue.
- Inspecteur pour modifier position, taille et couleur de l'objet sélectionné.
  Les champs numériques utilisent désormais des "spin box" pour une saisie
  plus fiable et un bouton affiche la couleur courante.
- Sauvegarde du projet au format JSON et génération de code Python.

### Fonctionnalités supplémentaires

#### Dessin et création de formes
- Tracer des lignes droites, des rectangles et des ellipses.
- Tracer des polygones simples.
- Tracer librement à la main.

#### Couleurs et styles
- Remplir les formes avec une couleur unie.
- Modifier la couleur et l'épaisseur du contour via le clic droit.

#### Texte
- Ajouter du texte libre et choisir sa police ainsi que sa couleur.

#### Transformations et déplacements
- Déplacer les objets dans le canvas à la souris.
- Redimensionner une forme depuis n'importe quel bord ou coin.
- Faire pivoter une forme grâce à la poignée de rotation placée au-dessus.

#### Précision et aides
- Grille visible avec magnétisme optionnel et taille ajustable.

#### Export
- Exporter au format image (PNG ou JPEG).
- Exporter en PDF.
- Exporter en SVG.
- Générer le code Python correspondant aux formes.

#### Sélection
- Sélectionner et déplacer les objets existants par glisser-déposer.
- Annuler ou rétablir une action (Undo/Redo).

#### Aides visuelles
- Contours visibles sur l'objet sélectionné.

## Installation des dépendances

Pictocode nécessite **Python 3.8 ou plus récent** ainsi que **PyQt5** :

```bash
pip install -r requirements.txt
```

## Lancement de l'application

Deux méthodes sont possibles :

1. Via le module installé :
   ```bash
   python -m pictocode
   ```
2. Ou en exécutant directement `main.py` :
   ```bash
   python main.py
   ```

Ces commandes ouvrent la fenêtre principale de l'éditeur.

### Exporter une image

Depuis un projet ouvert, utilisez le menu **Fichier > Exporter en image…**
pour enregistrer le contenu du canvas au format PNG ou JPEG.

### Exporter en PDF

Le menu **Fichier > Exporter en PDF…** permet d'enregistrer un fichier `.pdf`
à partir du contenu du document.

### Exporter en SVG

Le menu **Fichier > Exporter en SVG…** permet d'enregistrer un fichier `.svg`
contenant toutes les formes vectorielles du canvas.

### Exporter le code Python

Utilisez **Fichier > Exporter en code Python…** pour générer un script
`PyQt5` reproduisant les formes de votre projet.

### Personnaliser l'apparence

Dans le menu **Préférences**, vous pouvez choisir le thème (clair ou sombre),
définir une couleur et une taille de police spécifique pour la barre de menu,
la barre d'outils et l'inspecteur. Les menus disposent d'une animation
d'ouverture pour un rendu plus élégant.
Les couleurs par défaut du menu ont été modernisées pour offrir un meilleur contraste
et restent lisibles lors du passage d'un thème clair à sombre.
Une barre de titre personnalisée adopte également ces réglages, avec les boutons
de réduction, plein écran et fermeture.
Les passages entre l'accueil et le canvas utilisent désormais un effet de fondu.

### Raccourcis personnalisables

Une boîte de dialogue **Préférences > Raccourcis…** permet de modifier les
combinaisons clavier associées aux principales commandes (ouvrir, enregistrer,
etc.). Les raccourcis choisis sont sauvegardés et réappliqués au lancement de
l'application.

### Gestion des fenetres

Un panneau lateral "Panneaux" permet d'activer ou non diverses fenetres : proprietes, barre d'outils ou encore la liste des images importees.
Par defaut, ces fenetres sont rattachees a la fenetre principale et ne flottent plus.
Le plan de travail reste fixe : masquer ou afficher un panneau devoile simplement une plus grande partie de la zone visible sans la deplacer, quel que soit le cote auquel il est rattache.

La barre de titre personnalisée prend désormais en charge le déplacement système
pour profiter des raccourcis de redimensionnement Windows (snap et agrandissement
au bord de l'écran).

### Disposition d'onglets inspirée de Blender

L'interface peut être divisée en zones réorganisables. Chaque zone dispose d'un
petit coin servant à la scinder horizontalement ou verticalement. Un carré rouge
placé dans ce coin signale l'endroit où démarrer la création d'un nouvel onglet.
Lorsque la souris survole une zone, une icône en forme de croix apparaît pour
indiquer que le fractionnement est possible. Un menu contextuel permet
également de fusionner la zone courante avec ses voisines. Le contenu d'une zone
(éditeur, vue ou outil) se déplace simplement par glisser‑déposer d'une zone à
l'autre. Les dispositions peuvent être sauvegardées au format JSON puis
restaurées ultérieurement.

### Rapport de bugs

En cas d'erreur inattendue, Pictocode enregistre automatiquement la trace dans `~/pictocode_logs/pictocode.log`. Ce fichier peut être joint pour signaler un problème.

### Commandes utiles

Ces quelques lignes résument les commandes principales pour démarrer avec Pictocode :

- `pip install -r requirements.txt` pour installer les dépendances.
- `python -m pictocode` pour lancer l'application depuis le module installé.
- `python main.py` pour exécuter directement l'application.


## Dépannage

Si vous ne parvenez pas à déplacer une forme sur le canvas :

- Sélectionnez d'abord l'outil **Sélection** dans la barre d'outils.
- Vérifiez dans le panneau **Calques** que le calque contenant l'objet est actif et non verrouillé.
- Si l'option « Lock other » est cochée, seuls les éléments du calque courant peuvent être modifiés.
- Désactivez éventuellement l'aimantation à la grille (« Snap to grid ») pour tester un déplacement libre.

