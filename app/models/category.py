from app.extensions import db
from app.models.base import BaseModel


class Category(BaseModel):
    """
    Category model for organizing products.
    """
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(
        db.Integer,
        db.ForeignKey('businesses.id', ondelete='CASCADE'),
        nullable=False
    )
    name = db.Column(db.String(100), nullable=False)

    # Relationships
    business = db.relationship('Business', back_populates='categories')
    products = db.relationship(
        'Product',
        back_populates='category',
        cascade='all, delete-orphan'
    )

    @property
    def category_name(self):
        return self.name

    @category_name.setter
    def category_name(self, value):
        self.name = value

    def __repr__(self):
        return f'<Category {self.name}>'
