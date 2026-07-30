from app.extensions import db
from app.models.base import BaseModel


class SalesTransaction(BaseModel):
    """
    SalesTransaction model for sales/POS transaction headers.
    """
    __tablename__ = 'sales_transactions'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(
        db.Integer,
        db.ForeignKey('businesses.id', ondelete='CASCADE'),
        nullable=False
    )
    transaction_code = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )
    payment_method = db.Column(db.String(30), nullable=False, default='Tunai')
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)

    # Relationships
    business = db.relationship('Business', back_populates='sales_transactions')
    items = db.relationship(
        'SalesTransactionItem',
        back_populates='sales_transaction',
        cascade='all, delete-orphan'
    )

    # Property Aliases for backwards compatibility & convenience
    @property
    def invoice_number(self):
        return self.transaction_code

    @invoice_number.setter
    def invoice_number(self, val):
        self.transaction_code = val

    @property
    def total(self):
        return self.total_amount

    @total.setter
    def total(self, val):
        self.total_amount = val

    @property
    def sale_details(self):
        return self.items

    @property
    def transaction_date(self):
        return self.created_at

    def __repr__(self):
        return f'<SalesTransaction {self.transaction_code}>'
