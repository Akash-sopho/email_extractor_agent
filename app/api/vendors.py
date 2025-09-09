from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import api_key_auth
from app.db.models import Vendor
from app.db.session import get_db
from app.schemas.dto import VendorResponse

router = APIRouter(dependencies=[Depends(api_key_auth)])


@router.get("", response_model=list[VendorResponse])
def list_vendors(db: Session = Depends(get_db)) -> list[VendorResponse]:
    vendors = db.query(Vendor).order_by(Vendor.name.asc().nullslast()).all()
    return [VendorResponse(id=v.id, name=v.name, domain=v.domain) for v in vendors]
