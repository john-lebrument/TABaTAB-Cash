# TABaTAB Cash 2.14

- Ouverture des onglets : suppression des vérifications synchrones des favoris et du balayage des 26 lettres de lecteurs. Les favoris indisponibles restent visibles et conservés ; accès au dossier seulement à la demande.
- « Fermer tous les onglets » conserve et active le plus ancien onglet encore ouvert, même après déplacement des onglets.
- Collage par clic droit corrigé dans le dossier actuel, sur un fichier comme dans une zone vide ; images du presse-papiers et fichiers copiés/coupés pris en charge.
- Doublons du dossier courant : détection des fichiers strictement identiques et des images statiques aux pixels RGBA strictement identiques, après orientation EXIF, malgré des métadonnées, compressions sans perte ou formats différents. Aucune comparaison approximative : des images recompressées avec perte peuvent rester distinctes. Animations et documents multipages : comparaison du fichier complet uniquement. Sous-dossiers exclus.
- Conservation du premier fichier par ordre alphabétique et nouvelle vérification avant mise à la corbeille. Les métadonnées des exemplaires peuvent différer ; vérifier les résultats avant suppression. L’outil Doublons croisés conserve sa comparaison octet par octet.
