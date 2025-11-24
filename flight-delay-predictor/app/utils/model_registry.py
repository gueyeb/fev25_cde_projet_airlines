"""
Model Registry for Managing ML Model Versions
Supports loading, versioning, and A/B testing of models
"""
import joblib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
import hashlib


class ModelMetadata:
    """Metadata for a trained model"""

    def __init__(
        self,
        version: str,
        model_type: str,
        trained_at: datetime,
        metrics: Dict[str, float],
        feature_columns: list,
        description: str = ""
    ):
        self.version = version
        self.model_type = model_type
        self.trained_at = trained_at
        self.metrics = metrics
        self.feature_columns = feature_columns
        self.description = description

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'version': self.version,
            'model_type': self.model_type,
            'trained_at': self.trained_at.isoformat(),
            'metrics': self.metrics,
            'feature_columns': self.feature_columns,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelMetadata':
        """Create from dictionary"""
        return cls(
            version=data['version'],
            model_type=data['model_type'],
            trained_at=datetime.fromisoformat(data['trained_at']),
            metrics=data['metrics'],
            feature_columns=data['feature_columns'],
            description=data.get('description', '')
        )


class ModelRegistry:
    """
    Registry for managing multiple model versions
    """

    def __init__(self, models_dir: Path):
        self.models_dir = Path(models_dir)
        self.models = {}  # version -> {'model': model, 'metadata': ModelMetadata}
        self.active_version = None
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def register_model(
        self,
        model: Any,
        version: str,
        metadata: ModelMetadata,
        save_to_disk: bool = True
    ) -> bool:
        """
        Register a model with metadata

        Args:
            model: The trained model object
            version: Version identifier
            metadata: Model metadata
            save_to_disk: Whether to save model to disk

        Returns:
            True if successful
        """
        try:
            self.models[version] = {
                'model': model,
                'metadata': metadata,
                'loaded_at': datetime.now()
            }

            if save_to_disk:
                self._save_model_to_disk(model, metadata, version)

            # Set as active if it's the first model
            if self.active_version is None:
                self.active_version = version

            return True

        except Exception as e:
            print(f"Error registering model {version}: {e}")
            return False

    def load_model_from_disk(self, version: str) -> bool:
        """
        Load a model from disk

        Args:
            version: Version identifier

        Returns:
            True if successful
        """
        try:
            model_path = self.models_dir / f"{version}.pkl"
            metadata_path = self.models_dir / f"{version}_metadata.json"

            if not model_path.exists():
                print(f"Model file not found: {model_path}")
                return False

            # Load model
            model = joblib.load(model_path)

            # Load metadata if exists
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata_dict = json.load(f)
                metadata = ModelMetadata.from_dict(metadata_dict)
            else:
                # Create basic metadata
                metadata = ModelMetadata(
                    version=version,
                    model_type=type(model).__name__,
                    trained_at=datetime.now(),
                    metrics={},
                    feature_columns=getattr(model, 'feature_names_in_', []).tolist() if hasattr(model, 'feature_names_in_') else []
                )

            self.models[version] = {
                'model': model,
                'metadata': metadata,
                'loaded_at': datetime.now()
            }

            return True

        except Exception as e:
            print(f"Error loading model {version}: {e}")
            return False

    def _save_model_to_disk(self, model: Any, metadata: ModelMetadata, version: str):
        """Save model and metadata to disk"""
        model_path = self.models_dir / f"{version}.pkl"
        metadata_path = self.models_dir / f"{version}_metadata.json"

        # Save model
        joblib.dump(model, model_path)

        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)

    def set_active(self, version: str) -> bool:
        """
        Set the active model version

        Args:
            version: Version to activate

        Returns:
            True if successful
        """
        if version not in self.models:
            # Try to load from disk
            if not self.load_model_from_disk(version):
                print(f"Model version {version} not found")
                return False

        self.active_version = version
        return True

    def get_active_model(self) -> Optional[Any]:
        """Get the currently active model"""
        if self.active_version and self.active_version in self.models:
            return self.models[self.active_version]['model']
        return None

    def get_active_metadata(self) -> Optional[ModelMetadata]:
        """Get metadata for the active model"""
        if self.active_version and self.active_version in self.models:
            return self.models[self.active_version]['metadata']
        return None

    def get_model(self, version: str) -> Optional[Any]:
        """Get a specific model version"""
        if version in self.models:
            return self.models[version]['model']

        # Try to load from disk
        if self.load_model_from_disk(version):
            return self.models[version]['model']

        return None

    def list_versions(self) -> list:
        """List all registered model versions"""
        return list(self.models.keys())

    def get_all_metadata(self) -> Dict[str, Dict]:
        """Get metadata for all registered models"""
        return {
            version: {
                **info['metadata'].to_dict(),
                'loaded_at': info['loaded_at'].isoformat(),
                'is_active': version == self.active_version
            }
            for version, info in self.models.items()
        }

    def scan_models_directory(self) -> list:
        """Scan the models directory for available models"""
        model_files = list(self.models_dir.glob("*.pkl"))
        versions = []

        for model_file in model_files:
            version = model_file.stem
            # Skip metadata files
            if not version.endswith('_metadata'):
                versions.append(version)

        return versions

    def auto_load_latest(self) -> bool:
        """
        Automatically load the latest model from disk

        Returns:
            True if a model was loaded
        """
        versions = self.scan_models_directory()

        if not versions:
            return False

        # Try to find version with timestamp or use last modified
        latest_version = None
        latest_time = None

        for version in versions:
            model_path = self.models_dir / f"{version}.pkl"
            mtime = model_path.stat().st_mtime

            if latest_time is None or mtime > latest_time:
                latest_time = mtime
                latest_version = version

        if latest_version:
            success = self.load_model_from_disk(latest_version)
            if success:
                self.set_active(latest_version)
            return success

        return False

    def compare_models(self, version1: str, version2: str) -> Dict:
        """
        Compare two model versions

        Args:
            version1: First version
            version2: Second version

        Returns:
            Dict with comparison results
        """
        if version1 not in self.models or version2 not in self.models:
            return {'error': 'One or both versions not found'}

        meta1 = self.models[version1]['metadata']
        meta2 = self.models[version2]['metadata']

        return {
            'version1': version1,
            'version2': version2,
            'metrics_comparison': {
                'version1': meta1.metrics,
                'version2': meta2.metrics
            },
            'feature_columns_match': meta1.feature_columns == meta2.feature_columns,
            'model_type_match': meta1.model_type == meta2.model_type,
            'trained_at': {
                'version1': meta1.trained_at.isoformat(),
                'version2': meta2.trained_at.isoformat()
            }
        }

    def get_model_hash(self, version: str) -> Optional[str]:
        """
        Get hash of model file for integrity checking

        Args:
            version: Model version

        Returns:
            SHA256 hash of model file
        """
        model_path = self.models_dir / f"{version}.pkl"

        if not model_path.exists():
            return None

        sha256_hash = hashlib.sha256()
        with open(model_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()


# Global registry instance
_model_registry = None


def get_model_registry(models_dir: Optional[Path] = None) -> ModelRegistry:
    """Get or create global model registry"""
    global _model_registry

    if _model_registry is None:
        if models_dir is None:
            # Default to app/models directory
            from pathlib import Path
            models_dir = Path(__file__).parent.parent / "models"

        _model_registry = ModelRegistry(models_dir)

    return _model_registry
