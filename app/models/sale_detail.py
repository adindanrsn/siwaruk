from app.extensions import db
from app.models.base import BaseModel


class SaleDetail(BaseModel):
    """
    SaleDetail model representing line items for each sale.
    """
    __tablename__ = 'sale_details'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(
        db.Integer,
        db.ForeignKey('sales.id', ondelete='CASCADE'),
        nullable=False
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.id', ondelete='RESTRICT'),
        nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    selling_price = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    # Relationships
    sale = db.relationship('Sale', back_populates='sale_details')
    product = db.relationship('Product', back_populates='sale_details')

    def __repr__(self):
        return f'<SaleDetail Sale:{self.sale_id} Product:{self.product_id}>'
