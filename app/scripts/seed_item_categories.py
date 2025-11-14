from pathlib import Path
import sys, os
from dotenv import load_dotenv

# Load .env and add project root to sys.path
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.models.item_categories import BenchmarkCategory

CATEGORIES = [
    ("sand", "Fine aggregate (cement concrete work)"),
    
    # flooring (tile work)
    ("tile", "Flooring (tile work)"),
    ("steel", "Reinforcement steel/iron (cement concrete work)"),

    # cement concrete work
    ("cement", "Cement (cement concrete work)"),
    # earth work
    ("granular", "Granular/GSB materials (earth work)"),
]

def seed():
    created, updated = 0, 0
    with SessionLocal() as db:
        for name, desc in CATEGORIES:
            row = db.query(BenchmarkCategory).filter(BenchmarkCategory.name == name).one_or_none()
            if not row:
                db.add(BenchmarkCategory(name=name, description=desc))
                created += 1
            else:
                if (row.description or "") != desc:
                    row.description = desc
                    updated += 1
        db.commit()
    print(f"[item_categories] done | created={created} updated={updated}")

if __name__ == "__main__":
    seed()