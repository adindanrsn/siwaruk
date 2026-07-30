from app.extensions import db
from app.models.base import BaseModel


class SalesTransactionItem(BaseModel):
    """
    SalesTransactionItem model for line items in a SalesTransaction.
    """
    __tablename__ = 'sales_transaction_items'

    id = db.Column(db.Integer, primary_key=True)
    sales_transaction_id = db.Column(
        db.Integer,
        db.ForeignKey('sales_transactions.id', ondelete='CASCADE'),
        nullable=False
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.id', ondelete='RESTRICT'),
        nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    # Relationships
    sales_transaction = db.relationship('SalesTransaction', back_populates='items')
    product = db.relationship('Product')

    # Property Aliases for backwards compatibility & convenience
    @property
    def selling_price(self):
        return self.price

    @selling_price.setter
    def selling_price(self, val):
        self.price = val

    @property
    def sale_id(self):
        return self.sales_transaction_id

    @sale_id.setter
    def sale_id(self, val):
        self.sales_transaction_id = val

    def __repr__(self):
        return f'<SalesTransactionItem Trx:{self.sales_transaction_id} Product:{self.product_id}>'
