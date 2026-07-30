from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel


class Sale(BaseModel):
    """
    Sale model representing POS sales transaction records.
    """
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(
        db.Integer,
        db.ForeignKey('businesses.id', ondelete='CASCADE'),
        nullable=False
    )
    invoice_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )
    transaction_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    payment_method = db.Column(db.String(30), nullable=False, default='Tunai')
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    business = db.relationship('Business', back_populates='sales')
    sale_details = db.relationship(
        'SaleDetail',
        back_populates='sale',
        cascade='all, delete-orphan'
    )

    @property
    def transaction_number(self):
        return self.invoice_number

    @transaction_number.setter
    def transaction_number(self, val):
        self.invoice_number = val

    def __repr__(self):
        return f'<Sale {self.invoice_number}>'
