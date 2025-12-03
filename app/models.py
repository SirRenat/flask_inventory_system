from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    company_name = db.Column(db.String(100))
    inn = db.Column(db.String(20))
    legal_address = db.Column(db.Text)
    contact_person = db.Column(db.String(100))
    position = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    industry = db.Column(db.String(100))
    about = db.Column(db.Text)
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    products = db.relationship('Product', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.email}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    
    category_products = db.relationship('Product', backref='product_category', lazy=True)
    
    children = db.relationship(
        'Category', 
        backref=db.backref('parent', remote_side=[id]),
        lazy=True
    )
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    STATUS_PUBLISHED = 1
    STATUS_UNPUBLISHED = 2
    STATUS_READY_FOR_PUBLICATION = 3
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    manufacturer = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    images = db.Column(db.JSON)
    status = db.Column(db.Integer, default=STATUS_PUBLISHED)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    view_count = db.Column(db.Integer, default=0)  # ← ДОБАВЛЕНО для совместимости с dashboard.html
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.status == self.STATUS_PUBLISHED:
            self.expires_at = datetime.utcnow() + timedelta(days=30)
    
    def update_status(self):
        if self.status == self.STATUS_PUBLISHED and self.expires_at:
            if datetime.utcnow() > self.expires_at:
                self.status = self.STATUS_READY_FOR_PUBLICATION
                return True
        return False
    
    def publish(self):
        self.status = self.STATUS_PUBLISHED
        self.expires_at = datetime.utcnow() + timedelta(days=30)
    
    def unpublish(self):
        self.status = self.STATUS_UNPUBLISHED
    
    @property
    def days_remaining(self):
        if self.status == self.STATUS_PUBLISHED and self.expires_at:
            remaining = self.expires_at - datetime.utcnow()
            return max(0, remaining.days)
        return 0
    
    @property
    def is_expired(self):
        if self.status == self.STATUS_PUBLISHED and self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def status_text(self):
        status_map = {
            self.STATUS_PUBLISHED: 'Опубликован',
            self.STATUS_UNPUBLISHED: 'Снят с публикации',
            self.STATUS_READY_FOR_PUBLICATION: 'Готов к публикации'
        }
        return status_map.get(self.status, 'Неизвестно')
    
    def __repr__(self):
        return f'<Product {self.title}>'