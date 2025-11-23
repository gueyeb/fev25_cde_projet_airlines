"""
Tests unitaires pour les fonctions utilitaires
"""
import pytest
from datetime import datetime


class TestSplitIso:
    """Tests pour la fonction split_iso"""

    def test_split_iso_valid_datetime(self):
        """Teste le parsing d'un datetime ISO valide"""
        from src.utils.utils_functions import split_iso

        iso_string = "2025-01-20T10:30:00"
        date, time, dt = split_iso(iso_string)

        assert date is not None
        assert time is not None
        assert dt is not None
        assert date.year == 2025
        assert date.month == 1
        assert date.day == 20
        assert time.hour == 10
        assert time.minute == 30

    def test_split_iso_none_input(self):
        """Teste le comportement avec None en entrée"""
        from src.utils.utils_functions import split_iso

        date, time, dt = split_iso(None)

        assert date is None
        assert time is None
        assert dt is None

    def test_split_iso_invalid_format(self):
        """Teste le comportement avec un format invalide"""
        from src.utils.utils_functions import split_iso

        date, time, dt = split_iso("invalid-datetime")

        assert date is None
        assert time is None
        assert dt is None


class TestSafeGet:
    """Tests pour la fonction _safe_get"""

    def test_safe_get_existing_path(self):
        """Teste l'accès à un chemin existant"""
        from src.utils.utils_functions import _safe_get

        data = {
            "level1": {
                "level2": {
                    "value": "test"
                }
            }
        }

        result = _safe_get(data, "level1", "level2", "value")
        assert result == "test"

    def test_safe_get_missing_path(self):
        """Teste l'accès à un chemin inexistant"""
        from src.utils.utils_functions import _safe_get

        data = {"level1": {}}

        result = _safe_get(data, "level1", "missing", "value")
        assert result is None

    def test_safe_get_with_default(self):
        """Teste l'utilisation de la valeur par défaut"""
        from src.utils.utils_functions import _safe_get

        data = {}

        result = _safe_get(data, "missing", default="default_value")
        assert result == "default_value"


class TestToBucketIso:
    """Tests pour la fonction to_bucket_iso"""

    def test_bucket_hourly(self):
        """Teste le bucketing horaire (1h)"""
        from src.utils.utils_functions import to_bucket_iso

        dt = datetime(2025, 1, 20, 14, 35, 42)
        result = to_bucket_iso(dt, hours=1)

        assert result == "2025-01-20T14:00:00"

    def test_bucket_three_hours(self):
        """Teste le bucketing de 3 heures"""
        from src.utils.utils_functions import to_bucket_iso

        dt = datetime(2025, 1, 20, 14, 35, 42)
        result = to_bucket_iso(dt, hours=3)

        # 14h devrait être arrondi à 12h (12, 15, 18, 21)
        assert result == "2025-01-20T12:00:00"

    def test_bucket_none_input(self):
        """Teste le comportement avec None"""
        from src.utils.utils_functions import to_bucket_iso

        result = to_bucket_iso(None)
        assert result is None


class TestExtractOffsetFromUrl:
    """Tests pour la fonction extract_offset_from_url"""

    def test_extract_offset_present(self):
        """Teste l'extraction de l'offset quand il est présent"""
        from src.utils.utils_functions import extract_offset_from_url

        url = "https://api.example.com/airports?limit=100&offset=6800"
        result = extract_offset_from_url(url)

        assert result == 6800

    def test_extract_offset_missing(self):
        """Teste le comportement quand l'offset est absent"""
        from src.utils.utils_functions import extract_offset_from_url

        url = "https://api.example.com/airports?limit=100"
        result = extract_offset_from_url(url)

        assert result is None
