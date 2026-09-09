"""Study Service - Application-level study management.

This service handles creation, configuration, and persistence of optimization studies
without any dependency on external CAD platforms.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.models import CADModel
from core.study import (
    Study,
    LoadDefinition,
    ConstraintDefinition,
    Objectives,
    SolverSettings,
    LoadType,
    ConstraintType,
)
from core.materials import Material, STANDARD_MATERIALS

logger = logging.getLogger(__name__)


class StudyService:
    """Application service for study management."""

    def __init__(self, db_path: str = "jobs.sqlite3"):
        self.db_path = db_path
        self._init_database()

    def _db_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_database(self) -> None:
        """Initialize database schema for standalone studies."""
        with self._db_connection() as connection:
            # CAD models table (independent of OAuth)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cad_models (
                    model_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT,
                    filename TEXT,
                    metadata TEXT,
                    model_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            # Studies table (independent of OAuth)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS studies (
                    study_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    cad_model_id TEXT,
                    material_json TEXT,
                    loads_json TEXT,
                    constraints_json TEXT,
                    objectives_json TEXT,
                    solver_settings_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (cad_model_id) REFERENCES cad_models(model_id)
                )
                """
            )

    def create_study(
        self,
        name: str,
        cad_model: Optional[CADModel] = None,
        material: Optional[Material] = None,
        loads: Optional[List[LoadDefinition]] = None,
        constraints: Optional[List[ConstraintDefinition]] = None,
        objectives: Optional[Objectives] = None,
        solver_settings: Optional[SolverSettings] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Study:
        """Create a new optimization study (standalone, no Onshape required)."""
        study_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        study = Study(
            id=study_id,
            name=name,
            cad_model=cad_model,
            cad_model_id=cad_model.id if cad_model else None,
            material=material or STANDARD_MATERIALS["steel"],
            loads=loads or [],
            constraints=constraints or [],
            objectives=objectives or Objectives(),
            solver_settings=solver_settings or SolverSettings(),
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        # Save to database
        self._save_study(study)
        logger.info("Created study: %s (ID: %s)", name, study_id)
        return study

    def _save_study(self, study: Study) -> None:
        """Save study to database."""
        import json

        with self._db_connection() as connection:
            connection.execute(
                """
                INSERT INTO studies
                (study_id, name, cad_model_id, material_json, loads_json, constraints_json,
                 objectives_json, solver_settings_json, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(study_id) DO UPDATE SET
                    name=excluded.name,
                    cad_model_id=excluded.cad_model_id,
                    material_json=excluded.material_json,
                    loads_json=excluded.loads_json,
                    constraints_json=excluded.constraints_json,
                    objectives_json=excluded.objectives_json,
                    solver_settings_json=excluded.solver_settings_json,
                    updated_at=excluded.updated_at,
                    metadata=excluded.metadata
                """,
                (
                    study.id,
                    study.name,
                    study.cad_model_id,
                    json.dumps(study.material.to_dict()) if study.material else None,
                    json.dumps([l.to_dict() for l in study.loads]),
                    json.dumps([c.to_dict() for c in study.constraints]),
                    json.dumps(study.objectives.to_dict()),
                    json.dumps(study.solver_settings.to_dict()),
                    study.created_at,
                    study.updated_at,
                    json.dumps(study.metadata),
                ),
            )

    def get_study(self, study_id: str) -> Optional[Study]:
        """Retrieve study from database."""
        import json

        with self._db_connection() as connection:
            row = connection.execute(
                "SELECT * FROM studies WHERE study_id = ?", (study_id,)
            ).fetchone()

            if not row:
                return None

            try:
                material = Material(**json.loads(row["material_json"])) if row["material_json"] else None
                loads = [LoadDefinition(**l) for l in json.loads(row["loads_json"])] if row["loads_json"] else []
                constraints = [ConstraintDefinition(**c) for c in json.loads(row["constraints_json"])] if row["constraints_json"] else []
                objectives = Objectives(**json.loads(row["objectives_json"])) if row["objectives_json"] else Objectives()
                solver_settings = SolverSettings(**json.loads(row["solver_settings_json"])) if row["solver_settings_json"] else SolverSettings()

                return Study(
                    id=row["study_id"],
                    name=row["name"],
                    cad_model_id=row["cad_model_id"],
                    material=material,
                    loads=loads,
                    constraints=constraints,
                    objectives=objectives,
                    solver_settings=solver_settings,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
            except Exception as exc:
                logger.exception("Failed to deserialize study %s", study_id)
                return None

    def list_studies(self) -> List[Dict[str, Any]]:
        """List all studies."""
        with self._db_connection() as connection:
            rows = connection.execute(
                "SELECT study_id, name, cad_model_id, created_at, updated_at FROM studies ORDER BY created_at DESC"
            ).fetchall()

            return [
                {
                    "study_id": row["study_id"],
                    "name": row["name"],
                    "cad_model_id": row["cad_model_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    def delete_study(self, study_id: str) -> bool:
        """Delete a study from database."""
        with self._db_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM studies WHERE study_id = ?", (study_id,)
            )
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Deleted study: %s", study_id)
            return deleted

    def save_cad_model(self, cad_model: CADModel) -> None:
        """Save CAD model to database (independent of OAuth)."""
        import json

        with self._db_connection() as connection:
            connection.execute(
                """
                INSERT INTO cad_models
                (model_id, name, source_type, source_id, filename, metadata, model_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                    name=excluded.name,
                    metadata=excluded.metadata,
                    model_json=excluded.model_json,
                    updated_at=excluded.updated_at
                """,
                (
                    cad_model.id,
                    cad_model.name,
                    cad_model.source.source_type.value if cad_model.source else "unknown",
                    cad_model.source.source_id if cad_model.source else None,
                    cad_model.source.filename if cad_model.source else None,
                    json.dumps(cad_model.source.metadata) if cad_model.source else None,
                    json.dumps(cad_model.to_dict()),
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            logger.info("Saved CAD model: %s (ID: %s)", cad_model.name, cad_model.id)

    def get_cad_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve CAD model from database."""
        import json

        with self._db_connection() as connection:
            row = connection.execute(
                "SELECT model_json FROM cad_models WHERE model_id = ?", (model_id,)
            ).fetchone()

            if not row:
                return None

            try:
                return json.loads(row["model_json"])
            except Exception as exc:
                logger.exception("Failed to deserialize CAD model %s", model_id)
                return None