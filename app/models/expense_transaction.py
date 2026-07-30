from app.extensions import db
from app.models.base import BaseModel


class ExpenseTransaction(BaseModel):
    """
    ExpenseTransaction model for recording expenditure transactions.
    """
    __tablename__ = 'expense_transactions'

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
    purpose = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=True, default=1.00)
    unit = db.Column(db.String(50), nullable=True)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    business = db.relationship('Business', back_populates='expense_transactions')

    # Property Aliases for backwards compatibility & convenience
    @property
    def description(self):
        return self.purpose

    @description.setter
    def description(self, val):
        self.purpose = val

    @property
    def amount(self):
        return self.total_amount

    @amount.setter
    def amount(self, val):
        self.total_amount = val

    @property
    def expense_date(self):
        return self.created_at

    def __repr__(self):
        return f'<ExpenseTransaction {self.transaction_code} - {self.purpose}>'
