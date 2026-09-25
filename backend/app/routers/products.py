from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import current_user, owned_or_404
from ..database import get_db
from ..services import utcnow

router = APIRouter(prefix="/products", tags=["products"])


def get_product_or_404(
    product_id: int, db: Session, user: models.User
) -> models.Product:
    """Products are per-user (D4a); somebody else's id is a 404, not a 403."""
    return owned_or_404(models.Product, product_id, user, db, "Product")


@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    db_product = models.Product(**product.model_dump(), user_id=user.id)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("/", response_model=List[schemas.Product])
def read_products(
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    query = db.query(models.Product).filter(models.Product.user_id == user.id)
    if not include_archived:
        query = query.filter(models.Product.archived_at.is_(None))
    return query.order_by(models.Product.name).offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=schemas.Product)
def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    return get_product_or_404(product_id, db, user)


@router.patch("/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    product = get_product_or_404(product_id, db, user)
    # exclude_unset so omitting a field leaves it alone, rather than nulling it.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    """Archive rather than delete, so routines and history survive (specs.md section 5)."""
    product = get_product_or_404(product_id, db, user)
    if product.archived_at is None:
        product.archived_at = utcnow()
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
