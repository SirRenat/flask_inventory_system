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
        
class EditProductForm(FlaskForm):
    title = StringField('Название товара', validators=[DataRequired()])
    description = TextAreaField('Описание')
    price = FloatField('Цена', validators=[DataRequired()])
    category_id = SelectField('Категория', coerce=int, validators=[Optional()])
    images = StringField('Изображения (URL через запятую)')
    status = SelectField('Статус', choices=[
        ('1', 'Опубликован'),
        ('2', 'Готов к публикации'), 
        ('3', 'На проверке'),
        ('4', 'Не опубликован')
    ], validators=[DataRequired()])
    expires_at = DateTimeField('Действует до', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    is_active = BooleanField('Активный товар')
    submit = SubmitField('Сохранить изменения')