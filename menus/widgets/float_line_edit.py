from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Qt
from asteval import Interpreter
import math

class SafeMathLineEdit(QLineEdit):
    
    SYM_TABLE = {
        'pi': math.pi,
        'e': math.e,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'sqrt': math.sqrt,
        'log': math.log,
        'log10': math.log10,
        'log2': math.log2,
        'exp': math.exp,
        'abs': abs
    }
    
    def __init__(self, value: str | float = 0.0, default_value = None, parent = None):
        
        super().__init__(parent)
        
        if default_value is None:
            self.default_value = value
        else:
            self.default_value = default_value
        if isinstance(value, (float, int)):
            value = round(value, 5)
        
        self.setAlignment(Qt.AlignRight)
        self.setText(str(value))  # assure qu'on part d'un float

        # Création d'un interpréteur asteval sécurisé
        self.aeval = Interpreter()
        self.aeval.symtable.clear()  # supprime tout par défaut

        # Ajouter uniquement les fonctions et constantes mathiques souhaitées
        for k, v in self.SYM_TABLE.items():
            self.aeval.symtable[k] = v
        self.aeval.symtable['x'] = default_value

        # Connecte l'évaluation à la fin de l'édition ou à Enter
        self.editingFinished.connect(self.evaluate_expression)
        self.returnPressed.connect(self.evaluate_expression)

    def evaluate_expression(self):
        """Évalue le texte et remplace par le résultat float."""
        expr = self.text().replace(',', '.')  # convertir les virgules en points
        try:
            result = self.aeval(expr)
            # S'assurer que le résultat est un float
            if not isinstance(result, (int, float)):
                raise ValueError("L'expression doit être un nombre")
            self.setText(str(float(result)))
        except Exception:
            self.setText("0.0")  # fallback si invalide

    def value(self) -> float:
        """Retourne la valeur actuelle en float"""
        self.evaluate_expression()
        try:
            return float(self.text())
        except ValueError:
            return 0.0

    def setValue(self, value: str | float, set_default = True):
        """Change la valeur affichée"""
        self.setText(str(value))
        if set_default:
            self.default_value = value
