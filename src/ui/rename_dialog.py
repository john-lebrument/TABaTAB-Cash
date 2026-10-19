"""Offer an editable, collision-free name without letting Qt slots fail."""
from PyQt6.QtWidgets import QInputDialog
from src.utils.file_ops import suggest_rename


def rename_with_suggestion(parent, paths, name, operation):
    while True:
        try:
            return operation(paths, name)
        except FileExistsError:
            suggestion = suggest_rename(paths, name)
            name, accepted = QInputDialog.getText(
                parent, 'Nom déjà utilisé',
                'Ce nom existe déjà. Voici un nom libre (modifiable), sans extension :',
                text=suggestion)
            if not accepted:
                return None
