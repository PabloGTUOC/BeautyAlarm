from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_token
from ..database import get_db
from ..services import utcnow

router = APIRouter(
    prefix="/products", tags=["products"], dependencies=[Depends(require_token)]
)


def get_product_or_404(product_id: int, db: Session) -> models.Product:
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} does not exist",
        )
    return product


@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_product = models.Product(**product.model_dump())
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
):
    query = db.query(models.Product)
    if not include_archived:
        query = query.filter(models.Product.archived_at.is_(None))
    return query.order_by(models.Product.name).offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    return get_product_or_404(product_id, db)


@router.patch("/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)
):
    product = get_product_or_404(product_id, db)
    # exclude_unset so omitting a field leaves it alone, rather than nulling it.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_product(product_id: int, db: Session = Depends(get_db)):
    """Archive rather than delete, so routines and history survive (specs.md section 5)."""
    product = get_product_or_404(product_id, db)
    if product.archived_at is None:
        product.archived_at = utcnow()
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
