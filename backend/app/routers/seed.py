"""
Seed router — dev/demo only endpoint to populate database.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.seed_data import seed_database
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/seed",
    tags=["Dev/Seed"],
    dependencies=[Depends(get_current_user)]
)


@router.post("", summary="Seed database with 5000 employees, 5500 seats, and allocations")
def seed(db: Session = Depends(get_db)):
    """
    Populates the database with demo data. Safe to call multiple times
    (idempotent — skips if data already exists).
    """
    result = seed_database(db, verbose=False)
    return result
