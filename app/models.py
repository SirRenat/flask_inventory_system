from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

user_favorites = db.Table('user_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
)

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

    favorited_products = db.relationship('Product', secondary=user_favorites, lazy='dynamic', backref='favorited_by')
    
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

    @property
    def average_rating(self):
        """Средний рейтинг продавца"""
        from sqlalchemy import func
        avg_rating = db.session.query(func.avg(Review.rating)).filter(
            Review.seller_id == self.id,
            Review.is_published == True
        ).scalar()
        return round(avg_rating, 1) if avg_rating else 0
    
    @property
    def reviews_count(self):
        """Количество опубликованных отзывов"""
        from app.models import Review
        return Review.query.filter(
            Review.seller_id == self.id,
            Review.is_published == True
        ).count()
    
    @property
    def rating_distribution(self):
        """Распределение оценок (сколько каждого рейтинга)"""
        from app.models import Review
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        # Получаем все отзывы
        reviews = Review.query.filter(
            Review.seller_id == self.id,
            Review.is_published == True
        ).all()
        
        # Считаем распределение
        for review in reviews:
            if 1 <= review.rating <= 5:
                distribution[review.rating] += 1
        
        return distribution
    
    @property
    def recent_reviews(self, limit=5):
        """Последние отзывы"""
        from app.models import Review
        return Review.query.filter(
            Review.seller_id == self.id,
            Review.is_published == True
        ).order_by(Review.created_at.desc()).limit(limit).all()

    @classmethod
    def get_total_users_count(cls):
        """Возвращает общее количество пользователей"""
        return cls.query.count()
    
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    image = db.Column(db.String(255))  # путь к файлу или URL

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
    view_count = db.Column(db.Integer, default=0)
    vat_included = db.Column(db.Boolean, default=False)
    condition = db.Column(db.String(10), default='new')  # 'new' или 'used'
    region = db.Column(db.String(100))
    city = db.Column(db.String(100))
    delivery = db.Column(db.Boolean, default=False)
    
    # ← ДОБАВЛЕННЫЕ ПОЛЯ ДЛЯ ЗАВИСИМЫХ ВЫБОРОВ
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    
    # Связи с новыми таблицами
    region_rel = db.relationship('Region', foreign_keys=[region_id], backref='products')
    city_rel = db.relationship('City', foreign_keys=[city_id], backref='products')
    
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

class Review(db.Model):
    __tablename__ = 'review'
    
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True)
    
    # Связи
    seller = db.relationship('User', foreign_keys=[seller_id], backref='reviews_received')
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='reviews_given')
    product = db.relationship('Product', foreign_keys=[product_id], backref='reviews')
    
    def __repr__(self):
        return f'<Review {self.id} {self.rating}★>'
    
    @property
    def rating_stars(self):
        """Возвращает звездочки для отображения"""
        return '★' * self.rating + '☆' * (5 - self.rating)
    
    @property
    def created_at_formatted(self):
        """Форматированная дата"""
        return self.created_at.strftime('%d.%m.%Y')

# === МОДЕЛЬ: РЕГИОН ===
class Region(db.Model):
    __tablename__ = 'region'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship(
        'Region',
        backref=db.backref('parent', remote_side=[id]),
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<Region {self.name}>'


# === НОВАЯ МОДЕЛЬ: ГОРОД ===
class City(db.Model):
    __tablename__ = 'city'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    region = db.relationship('Region', backref='cities')
    
    def __repr__(self):
        return f'<City {self.name}>'
    
    @property
    def full_name(self):
        """Полное название города с регионом"""
        if self.region:
            return f"{self.name} ({self.region.name})"
        return self.name

class ContactRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_info = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='new')  # new, read, resolved

    def __repr__(self):
        return f'<ContactRequest {self.id} {self.category}>'
