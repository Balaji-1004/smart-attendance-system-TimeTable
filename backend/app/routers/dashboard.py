from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.database import get_db
from app.models import User
from app.schemas.dashboard import HODDashboardResponse
from app.services.dashboard_service import get_hod_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/hod", response_model=HODDashboardResponse)
def get_hod_dashboard_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    return get_hod_dashboard(db)
