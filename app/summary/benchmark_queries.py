from sqlalchemy.orm import Session
from app.models.benchmarks import BenchmarkMaterial
from app.models.item_categories import BenchmarkCategory

def get_project_benchmarks_json(project_id: int, db: Session) -> list[dict]:
    """
    Fetch all benchmarks for a project and return a list of one-line JSON descriptions.

    Args:
        project_id: Project ID to filter benchmarks.
        db: SQLAlchemy session.

    Returns:
        List of dicts with one-line benchmark descriptions.
    """
    # Join BenchmarkMaterial with BenchmarkCategory
    results = (
        db.query(BenchmarkMaterial, BenchmarkCategory)
        .join(BenchmarkCategory, BenchmarkMaterial.category_id == BenchmarkCategory.item_category_id)
        .filter(BenchmarkMaterial.project_id == project_id)
        .all()
    )

    benchmarks = []
    for material, category in results:
        line = (
            f"{material.name} ({category.name}): "
            f"{material.default_quantity_per_m3} {material.unit}"
            f"{' | ' + material.quality_standard if material.quality_standard else ''}"
            f"{' | ' + material.notes if material.notes else ''}"
            f"{' | Wastage: ' + str(material.default_wastage_multiplier) if material.default_wastage_multiplier else ''}"
        )
        benchmarks.append({
            "benchmark_material_id": material.benchmark_material_id,
            "category": category.name,
            "description": line,
            "required_by": material.required_by.isoformat() if material.required_by else None
        })

    return benchmarks

if __name__ == "__main__":
    import json
    from app.core.database import SessionLocal  # Adjust if your session import is different

    project_id = 1  # Change to your desired project ID
    db = SessionLocal()
    try:
        benchmarks = get_project_benchmarks_json(project_id, db)
        print(json.dumps(benchmarks, indent=2, default=str))
    finally:
        db.close()