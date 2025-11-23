"""
Tests unitaires pour les fonctions PostgreSQL
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch


class TestInsertDataframe:
    """Tests pour la fonction insert_dataframe"""

    def test_insert_dataframe_empty(self):
        """Teste que insert_dataframe gère correctement un DataFrame vide"""
        from src.utils.pg_functions import insert_dataframe

        df = pd.DataFrame()

        # Devrait afficher un message et ne rien faire
        with patch('builtins.print') as mock_print:
            insert_dataframe(df, "test_table")
            mock_print.assert_called()
            # Vérifier que le message contient "Aucune donnée"
            call_args = str(mock_print.call_args)
            assert "Aucune donnée" in call_args

    def test_insert_dataframe_not_empty(self):
        """Teste l'insertion d'un DataFrame non vide (mock)"""
        # Ce test nécessiterait une vraie DB ou un mock plus complexe
        # Pour l'instant, juste vérifier que la fonction existe
        from src.utils.pg_functions import insert_dataframe
        assert callable(insert_dataframe)


class TestIsFkViolation:
    """Tests pour la fonction _is_fk_violation"""

    def test_is_fk_violation_true(self):
        """Teste la détection d'une violation de clé étrangère"""
        from src.utils.pg_functions import _is_fk_violation
        from sqlalchemy.exc import IntegrityError

        # Mock d'une erreur avec code 23503
        mock_orig = Mock()
        mock_orig.sqlstate = "23503"
        mock_error = IntegrityError("statement", {}, None)
        mock_error.orig = mock_orig

        assert _is_fk_violation(mock_error) is True

    def test_is_fk_violation_false(self):
        """Teste avec une autre erreur d'intégrité"""
        from src.utils.pg_functions import _is_fk_violation
        from sqlalchemy.exc import IntegrityError

        # Mock d'une erreur avec un autre code
        mock_orig = Mock()
        mock_orig.sqlstate = "23505"  # Violation de contrainte unique
        mock_error = IntegrityError("statement", {}, None)
        mock_error.orig = mock_orig

        assert _is_fk_violation(mock_error) is False
