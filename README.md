# TABaTAB Cash — version 2.14

Visionneuse et explorateur d’images Windows portable avec onglets, favoris, navigation plein écran et outils de retouche.

**[Télécharger la dernière version Windows](https://github.com/john-lebrument/tabatab-cash/releases/latest)** · **[Historique des versions et nouveautés](CHANGELOG.md)**

## Nouveautés 2.14

- Ouverture des onglets : suppression des vérifications synchrones des favoris et du balayage des 26 lettres de lecteurs. Les favoris indisponibles restent visibles et conservés ; accès au dossier seulement à la demande.
- « Fermer tous les onglets » conserve et active le plus ancien onglet encore ouvert, même après déplacement des onglets.
- Collage par clic droit corrigé dans le dossier actuel, sur un fichier comme dans une zone vide ; images du presse-papiers et fichiers copiés/coupés pris en charge.
- Doublons du dossier courant : détection des fichiers strictement identiques et des images statiques aux pixels RGBA strictement identiques, après orientation EXIF, malgré des métadonnées, compressions sans perte ou formats différents. Aucune comparaison approximative : des images recompressées avec perte peuvent rester distinctes. Animations et documents multipages : comparaison du fichier complet uniquement. Sous-dossiers exclus.
- Conservation du premier fichier par ordre alphabétique et nouvelle vérification avant mise à la corbeille. Les métadonnées des exemplaires peuvent différer ; vérifier les résultats avant suppression. L’outil Doublons croisés conserve sa comparaison octet par octet.

## Nouveautés 2.13

- **Flou déplaçable et transformable** : après F, dessiner une zone elliptique puis glisser dans son intérieur pour la déplacer. **Ctrl+T**, ou le bouton Transformer, affiche huit poignées sur la zone sélectionnée pour modifier sa largeur et sa hauteur. Cliquer dans une autre zone la sélectionne ; dessiner en dehors des zones en ajoute une autre. Les zones restent dans l’image et l’aperçu se recalcule à chaque déplacement / transformation.
- **Plusieurs flous** : les zones restent indépendantes et sont enregistrées ensemble. Entrée ou Échap quitte d’abord les poignées de transformation, en conservant les zones ; une nouvelle pression sur Entrée propose l’enregistrement du flou, Échap annule l’outil. Le panneau rappelle les gestes et propose toujours l’effacement de la dernière zone, l’enregistrement en copie ou l’écrasement de l’original.
- **Métadonnées en plein écran** : amener le pointeur sur les huit derniers pixels du bord droit ouvre un volet superposé. Revenir sur l’image, sortir de la fenêtre ou appuyer sur Échap le referme. Le volet conserve le zoom de l’image et permet de parcourir les informations du fichier, dimensions, format, canaux, trames, EXIF, sous-répertoires EXIF/GPS/interopérabilité, données fabricant décodables, balises TIFF, textes PNG, IPTC, XMP et profil ICC disponibles dans le fichier. Les balises inconnues sont conservées ; les données binaires non décodables sont proposées en hexadécimal complet. Sélectionner une ligne affiche sa valeur intégrale, sélectionnable et copiable dans la zone inférieure. Lecture en arrière-plan et erreurs signalées. Le volet est réservé au plein écran et absent des fenêtres B.
- **Zoom réel et dimensions** : l’indication représente désormais la taille par rapport aux pixels source, et non par rapport à l’ajustement initial. `100 %` correspond à un pixel source par pixel physique de l’écran, y compris avec la mise à l’échelle Windows. Les petites images ne sont plus agrandies automatiquement. Les grandes images sont réduites pour tenir entièrement dans l’écran en gardant leurs proportions ; leur vrai pourcentage est affiché. Le pourcentage est accompagné de la largeur et de la hauteur de l’image affichée, en pixels. L’agrandissement manuel reste possible.
- **Fenêtres B indépendantes** : réduire la fenêtre principale ne réduit plus les images B. Chaque image possède un bouton **−** à côté de la croix, visible au survol, pour être réduite séparément. Les fenêtres B s’ouvrent sur l’écran depuis lequel elles sont demandées ; elles restent gérées par l’application et se ferment quand celle-ci est quittée.
- **Zoom conservé dans B** : redimensionner une fenêtre, y compris par la poignée en bas à droite, conserve son échelle de zoom et son point de vue lorsque le défilement le permet. Glisser l’image permet toujours de la déplacer dans la fenêtre ; 0 / Ajuster réinitialise volontairement l’ajustement. Le pas de zoom est divisé par deux sur l’échelle multiplicative : deux crans correspondent à un ancien cran, dans les deux sens. Le zoom et le dézoom restent réversibles. Le menu du clic droit des petites fenêtres indique aussi le pourcentage réel et les dimensions.

## Nouveautés 2.12

- **Actualiser** : bouton à flèche circulaire placé près du chemin, en complément de F5. Recharge le dossier et conserve la sélection et le défilement.
- **Renommage sans conflit** : si le nom choisi existe déjà, une boîte propose un nom libre incrémenté, modifiable avant validation. Exemple : `Photo 009` → `Photo 010`, ou `Photo` → `Photo 001`. Fonctionne dans la grille, en plein écran, en fenêtre flottante et pour les séries ; toutes les destinations d’une série sont vérifiées avant le renommage. Annuler conserve les fichiers.
- **Chemin en blocs** : chaque dossier est un bloc cliquable. Cliquer dans l’espace libre juste après le dernier bloc permet de saisir un chemin ou de copier le chemin complet avec Ctrl+C. Alt+D et le bouton Chemin restent disponibles ; Échap revient aux blocs.
- **Doublons croisés** : nouvel outil indépendant du bouton Doublons existant. Choisir un ou plusieurs dossiers dans le groupe A et un ou plusieurs dans le groupe B ; seuls les contenus identiques présents entre les deux groupes sont affichés. Comparaison exacte SHA-256 de tous les fichiers ordinaires, avec sous-dossiers par défaut (désactivables), sans suivre les liens et jonctions. Les dossiers qui se recoupent ne produisent pas de faux doublon d’un fichier avec lui-même.
- Ouvrir **Doublons croisés…** depuis sa barre de boutons ou par clic droit sur un dossier de l’arborescence, des favoris ou de la grille (plusieurs dossiers sélectionnés possibles dans la grille). Le clic droit place le dossier dans A, reprend les autres choix mémorisés et ouvre l’outil ; cliquer ensuite sur **Rechercher les doublons**. La fenêtre reste ouverte pendant la navigation pour permettre le glisser-déposer.
- Dans chaque groupe : ajout par **Parcourir…**, liste des **favoris** et glisser-déposer de dossiers depuis l’arborescence. Le dépôt ajoute uniquement un chemin, sans déplacer le dossier. Listes et option de sous-dossiers sont conservées localement entre les utilisations. Les dossiers momentanément inaccessibles restent mémorisés.
- Résultats : ouvrir un fichier, l’afficher dans l’Explorateur, copier les chemins ou cocher des fichiers et cliquer sur **Mettre les fichiers cochés à la corbeille**, **sans confirmation supplémentaire**. Aucun fichier n’est coché automatiquement ; au moins un exemplaire doit rester dans chaque groupe. Les contenus sont revérifiés avant la mise à la corbeille ; si le contenu a changé ou si la corbeille est indisponible, le fichier est conservé. Recherche en arrière-plan, annulable, avec erreurs d’accès signalées.
- La compilation actualise l’enregistrement Windows existant vers le nouvel exécutable portable, sans modifier les choix d’applications par défaut.

## Nouveautés 2.11

- **Google Lens corrigé** : l’image est envoyée par le navigateur par défaut, qui conserve la session d’importation et affiche les résultats. L’application ne lui transmet plus une adresse de résultats issue d’une session Python distincte, cause du message « Recherche visuelle expirée » en 2.10.
- **Clic droit en plein écran ou en fenêtre flottante** : ouvre uniquement les outils. Utiliser le bouton « Images similaires (S) » pour rechercher sur Yandex.com et Google Lens. Dans les petites fenêtres flottantes, cette commande figure dans le menu contextuel. La touche **S** lance toujours directement la recherche ; **Ctrl+S** conserve sa fonction d’enregistrement.
- L’aperçu JPEG sans EXIF est transmis au navigateur par une page temporaire sur `127.0.0.1`, puis envoyé directement à Google Lens. Cette page ne donne accès à aucun dossier : elle contient uniquement l’aperçu de la recherche, reste disponible dix minutes et nécessite que TABaTAB reste ouvert jusqu’à l’envoi. Aucun fichier de transfert n’est écrit sur disque. Yandex conserve son envoi en arrière-plan.

## Nouveautés 2.10

- Le renommage par F2 reste lisible en plein écran et en fenêtre flottante, avec les thèmes clair et sombre. Le fond noir de l’image ne se propage plus aux boîtes de dialogue.
- **Images similaires (S)** : recherche de la photo courante sur Yandex.com et Google Lens, en ouvrant deux pages de résultats dans le navigateur par défaut. Disponible dans la grille, en plein écran et en fenêtre flottante. Ctrl+S conserve sa fonction d’enregistrement.
- En plein écran et en fenêtre flottante, un clic droit lance directement les deux recherches. Dans la grille, le menu contextuel propose « Images similaires sur Yandex et Google Lens (S) » pour l’image cliquée.
- Une copie JPEG de recherche, limitée à 1600 pixels de côté et sans métadonnées EXIF, est envoyée directement à chaque moteur lorsque la commande est utilisée. Le fichier original reste intact ; la recherche porte sur le fichier enregistré. Internet est nécessaire. Les envois sont indépendants et effectués en arrière-plan ; les erreurs réseau sont signalées. Le navigateur choisit l’ouverture en fenêtres ou en onglets selon ses réglages.

## Nouveautés 2.9

- Le menu contextuel des favoris propose maintenant l’ouverture du dossier dans l’Explorateur Windows.
- L’arborescence peint une bande de couleur vive et une teinte visible sur les dossiers colorés ; les couleurs proposées sont plus vives.
- Le plein écran décode HEIC/HEIF avec Pillow-Heif pour afficher correctement les pixels.
- Les résultats des doublons sont présentés dans une fenêtre française, avec aperçu des images et détails en lignes distinctes et en gras.
- Les boutons Vidéos et ZIP partagent le même style vert lorsqu’ils sont activés.
- Les commandes de tri sont renforcées visuellement.

## Nouveautés 2.8

- Clic droit sur un dossier de l’arborescence ou de la grille : ouvrir directement dans l’Explorateur Windows.
- Clic droit sur un dossier de l’arborescence : choisir une couleur prédéfinie ou personnalisée ; le choix est mémorisé.
- Après génération d’une vignette vidéo, le lecteur multimédia libère explicitement sa source afin de faciliter la suppression du fichier sous Windows.
- Les images HEIC et HEIF peuvent être affichées ; le support repose sur Pillow-Heif inclus dans la version portable.
- Les boutons latéraux 4 et 5 de la souris parcourent l’historique précédent/suivant dans l’arborescence et la grille.
- La fenêtre des doublons affiche les groupes avec les fichiers conservés et à supprimer, leur taille, leur date de modification et leur chemin. Le calcul et le choix des fichiers conservés sont inchangés.
- Le double-clic sur une archive ZIP ouvre son application Windows par défaut.

## Nouveautés 2.7

- **Miroir horizontal (H)** : inverse la gauche et la droite des images sélectionnées depuis la grille ou le menu de rotation. En plein écran, H et le bouton Miroir prévisualisent le résultat ; Ctrl+S permet de sauvegarder ou de créer une copie. Le miroir reste compatible avec les rotations, le recadrage et le floutage.
- **Début / Fin dans les miniatures** : rejoint la première ou la dernière image et fait défiler la grille jusqu’à elle.
- **Actualisation automatique** : surveillance du dossier, relecture au retour sur un onglet ou dans la fenêtre. Les nouveaux fichiers sont triés selon le réglage courant, avec conservation de la sélection et de la position de défilement. Les miniatures modifiées sont invalidées. F5 reste disponible.
- **Bouton ZIP** : affiche ou masque les archives ZIP, avec choix mémorisé. Double-cliquer ouvre l’archive avec Windows ; les ZIP ne font pas partie du diaporama.
- **Doublons du dossier affiché** : recherche en arrière-plan, annulable, des fichiers ordinaires identiques par SHA-256 et des images statiques aux pixels identiques (depuis la 2.14), indépendamment de leur nom et de leur extension. Les sous-dossiers et les liens sont exclus. La liste indique les fichiers conservés et les copies à supprimer. Le premier nom par ordre alphabétique est conservé ; les autres peuvent être envoyés à la corbeille avec le bouton Supprimer les doublons. Les empreintes sont revérifiées avant suppression et les fichiers sont conservés si la corbeille est indisponible.
- **Glisser-déposer renforcé** : suppression du transfert de secours utilisant une ancienne destination survolée ; dépôt dans une zone vide de la barre d’onglets refusé. Les transferts depuis la grille vers un onglet sont différés jusqu’à la fin du glisser-déposer Windows. Cette correction retire des comportements ambigus ; elle ne prétend pas établir la cause de l’incident observé en 2.6.


## Utilisation

Décompresser l’archive complète, puis lancer `TABaTAB Cash.exe` dans son dossier. Conserver le dossier `_internal` à côté de l’exécutable. Les préférences sont créées dans `data/settings.json` et restent locales.

- Onglets indépendants ; chemins cliquables, arborescence et miniatures.
- Favoris partagés et mémorisés : ajouter un dossier par clic droit, réorganiser par glisser-déposer, exporter/importer en JSON depuis le menu ⋯.
- Copier, couper, coller et déplacer entre dossiers, favoris et onglets ; Ctrl permet de copier pendant un glissement.
- Tri des miniatures par nom, date de modification, date de création, taille ou type, depuis la barre ou le clic droit.
- Retouche : rotations, recadrage, flou elliptique avec plusieurs zones, conversion JPEG/PNG et renommage groupé.
- Images et vidéos : vignettes vidéo lorsque le codec est disponible et lecture dans le lecteur Windows par défaut.
- Images HEIC/HEIF prises en charge dans la visionneuse.
- Associations d’images depuis le bouton de l’application, avec validation finale dans les paramètres Windows.

## Raccourcis

| Touche | Action |
| --- | --- |
| Ctrl+T / Ctrl+W / Ctrl+Tab | Nouvel onglet / fermer / changer d’onglet |
| F2 | Renommer une image ou un dossier |
| F5 | Actualiser le dossier |
| Ctrl+C / Ctrl+X / Ctrl+V | Copier / couper / coller |
| Double-clic / Espace dans la grille | Ouvrir l’image en plein écran |
| Échap | Quitter le plein écran ou annuler l’outil actif |
| Flèches / molette en plein écran | Image précédente ou suivante |
| Début / Fin | Première / dernière image |
| + / − ou Ctrl+molette | Zoom avant / arrière |
| 0 / * | Ajuster à l’écran, sans agrandir au-delà de la taille native |
| M | Déplacer le plein écran sur l’écran suivant |
| B | Fenêtres flottantes des images sélectionnées |
| C / X | Recadrage |
| F | Flou |
| Ctrl+T pendant le flou | Afficher / masquer les huit poignées de transformation |
| L / R | Rotation gauche / droite |
| H | Miroir horizontal gauche-droite |
| S | Rechercher l’image sur Yandex.com et Google Lens |
| Clic droit dans la visionneuse | Ouvrir les outils, dont « Images similaires (S) » |
| Ctrl+S | Enregistrer une rotation |
| Suppr / Maj+Suppr | Corbeille / suppression définitive |
| Ctrl+Z | Restaurer la dernière image supprimée pendant la session |

Le zoom affiché indique l’échelle réelle : 100 % correspond à un pixel source par pixel physique de l’écran, 50 % à la moitié de la largeur et de la hauteur natives. L’ajustement initial dépend des dimensions de l’image et de l’écran, avec un maximum de 100 %. Les fenêtres B utilisent un demi-pas : deux crans équivalent à un cran du plein écran.

## Historique

Les nouveautés de **2.11, 2.10, 2.9, 2.8, 2.7, 2.6, 2.5, 2.4, 2.3, 2.2, 2.1, 2.0 et 1.9**, puis celles de **1.8 à 1.4** et les fonctionnalités documentées des premières versions figurent dans [CHANGELOG.md](CHANGELOG.md). Les attributions incertaines avant 1.4 sont signalées.

## Développement et compilation

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m src.main
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe build_portable.py
```

Incrémenter `src/version.py` et `resources/version_info.txt` avant chaque nouvelle compilation. Les anciens dossiers compilés dans le projet restent conservés.

La compilation habituelle dépose la version complète dans `OneDrive - unicaen.fr/Setup 1D/__Last version`, vérifie chaque fichier par SHA-256, puis retire les anciennes distributions de TABaTAB de ce dossier. `TABATAB_LATEST_DIRECTORY` permet de choisir un autre dossier. Pour compiler ailleurs sans ce dépôt :

```powershell
python build_portable.py --no-publish --clean-settings
```

## Publier une nouvelle version

Documenter les changements, tester et compiler, puis commiter et pousser les sources. Publier avec un fichier de notes propre à la nouvelle version :

```powershell
.venv/Scripts/python.exe publish_release.py --notes release/notes-v2.6.md
```

La release contient le ZIP Windows x64 complet et son empreinte SHA-256. Les préférences personnelles sont exclues de l’archive GitHub. Les sources, les notes de version, la release compilée et la copie OneDrive doivent être actualisées pour chaque nouvelle version.
