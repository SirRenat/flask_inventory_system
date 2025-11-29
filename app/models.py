from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    company_name = db.Column(db.String(200), nullable=False)
    inn = db.Column(db.String(12))
    legal_address = db.Column(db.Text)
    contact_person = db.Column(db.String(100))
    position = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    industry = db.Column(db.String(100))
    about = db.Column(db.Text)
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return str(self.id)

class Category(db.Model):
    __tablename__ = 'category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    
    parent = db.relationship('Category', remote_side=[id], backref='children')

class Product(db.Model):
    __tablename__ = 'product'
    
    # Статусы товара
    STATUS_PUBLISHED = 1  # Опубликован
    STATUS_UNDER_REVIEW = 2  # На проверке (временно не используется)
    STATUS_READY_FOR_PUBLICATION = 3  # Готов к публикации
    STATUS_UNPUBLISHED = 4  # Снят с публикации
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    images = db.Column(db.JSON)  # Список имен файлов изображений
    status = db.Column(db.Integer, default=STATUS_PUBLISHED)  # Статус товара
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Дата истечения срока публикации
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    
    user = db.relationship('User', backref=db.backref('products', lazy=True))
    category = db.relationship('Category', backref=db.backref('products', lazy=True))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Устанавливаем срок истечения публикации (30 дней от создания)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=30)
    
    def update_status(self):
        """Обновляет статус товара на основе даты истечения"""
        if self.status == self.STATUS_PUBLISHED and datetime.utcnow() > self.expires_at:
            self.status = self.STATUS_READY_FOR_PUBLICATION
            return True
        return False
    
    def renew_publication(self):
        """Продлевает публикацию товара на 30 дней"""
        self.expires_at = datetime.utcnow() + timedelta(days=30)
        self.status = self.STATUS_PUBLISHED
        return True
    
    def unpublish(self):
        """Снимает товар с публикации"""
        self.status = self.STATUS_UNPUBLISHED
        return True
    
    def publish(self):
        """Публикует товар"""
        self.expires_at = datetime.utcnow() + timedelta(days=30)
        self.status = self.STATUS_PUBLISHED
        return True
    
    @property
    def status_text(self):
        """Текстовое представление статуса"""
        status_map = {
            self.STATUS_PUBLISHED: 'Опубликован',
            self.STATUS_UNDER_REVIEW: 'На проверке',
            self.STATUS_READY_FOR_PUBLICATION: 'Готов к публикации',
            self.STATUS_UNPUBLISHED: 'Снят с публикации'
        }
        return status_map.get(self.status, 'Неизвестно')
    
    @property
    def is_published(self):
        """Проверяет, опубликован ли товар"""
        return self.status == self.STATUS_PUBLISHED
    
    @property
    def is_unpublished(self):
        """Проверяет, снят ли товар с публикации"""
        return self.status == self.STATUS_UNPUBLISHED
    
    @property
    def is_expired(self):
        """Проверяет, истек ли срок публикации"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def days_remaining(self):
        """Оставшееся количество дней публикации"""
        if self.status == self.STATUS_PUBLISHED:
            remaining = self.expires_at - datetime.utcnow()
            return max(0, remaining.days)
        return 0
    
    @property
    def can_be_viewed_by_public(self):
        """Может ли товар быть просмотрен другими пользователями"""
        return self.status == self.STATUS_PUBLISHED