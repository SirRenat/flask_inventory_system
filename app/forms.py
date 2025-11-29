from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, FileField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Optional
from models import Category, Unit

class ProductForm(FlaskForm):
    title = StringField('Название товара', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[Optional()])
    price = FloatField('Цена', validators=[DataRequired()])
    quantity = FloatField('Количество', default=1)  # ⭐ ДОБАВИТЬ
    category_id = SelectField('Категория', coerce=int, validators=[Optional()])  # ⭐ ИСПРАВИТЬ
    unit_id = SelectField('Единица измерения', coerce=int, validators=[Optional()])  # ⭐ ДОБАВИТЬ
    images = FileField('Изображения товара')  # ⭐ ДОБАВИТЬ
    
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        # Заполняем выбор категорий из БД
        self.category_id.choices = [(0, 'Без категории')] + [
            (cat.id, cat.name) for cat in Category.query.order_by('name').all()
        ]
        # Заполняем единицы измерения
        self.unit_id.choices = [(0, 'Выберите единицу')] + [
            (unit.id, unit.name) for unit in Unit.query.order_by('name').all()
        ]
