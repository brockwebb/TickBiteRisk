from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.design_matrix import (
    ID_COLUMNS,
    PASSTHROUGH_COLUMNS,
    TARGET_COLUMNS,
    ModelDesignMatrixResult,
)


@dataclass(frozen=True)
class ModelDesignMatrixOutputPaths:
    matrix_path: Path
    schema_path: Path


def write_model_design_matrix_outputs(
    result: ModelDesignMatrixResult,
    output_dir: Path,
) -> ModelDesignMatrixOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = output_dir / "model_design_matrix_county_year.csv"
    schema_path = output_dir / "model_design_matrix_schema.json"
    columns = [
        *ID_COLUMNS,
        *TARGET_COLUMNS,
        *result.schema.feature_columns,
        *PASSTHROUGH_COLUMNS,
    ]
    with matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {
                column: row.get(column, "")
                for column in columns
            }
            for row in result.rows
        )
    schema_path.write_text(
        json.dumps(asdict(result.schema), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ModelDesignMatrixOutputPaths(
        matrix_path=matrix_path,
        schema_path=schema_path,
    )
