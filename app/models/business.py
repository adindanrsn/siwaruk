from app.extensions import db
from app.models.base import BaseModel


# Valid choices for Bidang Usaha dropdown
BIDANG_USAHA_CHOICES = [
    'Kuliner',
    'Jasa',
    'Agribisnis Pangan',
    'Agribisnis Nonpangan',
    'Lain-lain',
]

# Certification definitions — used in routes and templates
SERTIFIKASI_LIST = [
    {'key': 'halal', 'label': 'Halal'},
    {'key': 'bpom',  'label': 'BPOM'},
    {'key': 'pirt',  'label': 'PIRT'},
    {'key': 'nib',   'label': 'NIB'},
]


class Business(BaseModel):
    """
    Business model representing MSME / UMKM profile.
    """
    __tablename__ = 'businesses'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    business_name = db.Column(db.String(100), nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    bidang_usaha = db.Column(db.String(50), nullable=True)

    # ── Certifications ──────────────────────────────────────────────
    has_halal    = db.Column(db.Boolean, default=False, nullable=False)
    halal_number = db.Column(db.String(100), nullable=True)

    has_bpom    = db.Column(db.Boolean, default=False, nullable=False)
    bpom_number = db.Column(db.String(100), nullable=True)

    has_pirt    = db.Column(db.Boolean, default=False, nullable=False)
    pirt_number = db.Column(db.String(100), nullable=True)

    has_nib    = db.Column(db.Boolean, default=False, nullable=False)
    nib_number = db.Column(db.String(100), nullable=True)
    # ────────────────────────────────────────────────────────────────

    # Relationships
    owner = db.relationship('User', back_populates='businesses')
    categories = db.relationship(
        'Category',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    products = db.relationship(
        'Product',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    expense_categories = db.relationship(
        'ExpenseCategory',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    expenses = db.relationship(
        'Expense',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    sales = db.relationship(
        'Sale',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    sales_transactions = db.relationship(
        'SalesTransaction',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    expense_transactions = db.relationship(
        'ExpenseTransaction',
        back_populates='business',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Business {self.business_name}>'
