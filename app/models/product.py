from app.extensions import db
from app.models.base import BaseModel


class Product(BaseModel):
    """
    Product model for items sold by the business.
    """
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(
        db.Integer,
        db.ForeignKey('businesses.id', ondelete='CASCADE'),
        nullable=False
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey('categories.id', ondelete='SET NULL'),
        nullable=True
    )
    name = db.Column(db.String(150), nullable=False)
    selling_price = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    stock = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(20), nullable=False, default='pcs')
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Relationships
    business = db.relationship('Business', back_populates='products')
    category = db.relationship('Category', back_populates='products')
    sale_details = db.relationship('SaleDetail', back_populates='product')

    def __repr__(self):
        return f'<Product {self.name}>'
