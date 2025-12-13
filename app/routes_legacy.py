from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app, jsonify
from flask_login import login_required, current_user
from app import db, csrf
from app.models import Product, Category, User, Review, Region, City
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from PIL import Image

main = Blueprint('main', __name__, template_folder='../templates')

try:
    from app.forms import ReviewForm
except ImportError:
    class ReviewForm:
        def __init__(self, *args, **kwargs):
            pass
        def validate_on_submit(self):
            return False

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def _deserialize_images(images_field):
    """Преобразует значение поля images (строка или список) в список имён файлов."""
    if not images_field:
        return []
    if isinstance(images_field, list):
        return [img for img in images_field if img]
    if isinstance(images_field, str):
        return [img.strip() for img in images_field.split(',') if img.strip()]
    return []

def _serialize_images(images_list):
    """Преобразует список имён файлов в строку для хранения в БД."""
    return ','.join(images_list) if images_list else ''

def process_category_image(file, category_id=None):
    """Обрабатывает и сохраняет изображение категории с обрезкой"""
    if file and allowed_file(file.filename):
        try:
            # Открываем изображение
            img = Image.open(file)
            
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Определяем размеры
            width, height = img.size
            
            # Если изображение очень большое, уменьшаем перед обрезкой
            max_dimension = 800
            if width > max_dimension or height > max_dimension:
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                width, height = img.size
            
            # Обрезаем до квадрата (центрированно)
            target_size = min(width, height)
            
            # Координаты для обрезки
            left = (width - target_size) // 2
            top = (height - target_size) // 2
            right = left + target_size
            bottom = top + target_size
            
            img_cropped = img.crop((left, top, right, bottom))
            
            # Создаем несколько размеров
            sizes = {
                'original': (target_size, target_size),  # Оригинальный квадрат
                'large': (200, 200),  # Для десктопа
                'medium': (150, 150), # Для планшетов
                'small': (100, 100),  # Для мобильных
                'thumbnail': (80, 80)  # Для превью (как в блоке категорий)
            }
            
            # Генерируем уникальное имя файла
            unique_filename = str(uuid.uuid4())
            original_filename = secure_filename(file.filename)
            ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
            
            base_filename = f"{unique_filename}_{original_filename.split('.')[0]}"
            
            # Сохраняем все размеры
            saved_filenames = {}
            
            for size_name, (size_width, size_height) in sizes.items():
                # Ресайзим
                img_resized = img_cropped.resize((size_width, size_height), Image.Resampling.LANCZOS)
                
                # Формируем имя файла
                if size_name == 'thumbnail':
                    filename = f"{base_filename}.{ext}"  # Основное имя для thumbnail
                else:
                    filename = f"{base_filename}_{size_name}.{ext}"
                
                # Путь для сохранения
                upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories')
                os.makedirs(upload_folder, exist_ok=True)
                
                filepath = os.path.join(upload_folder, filename)
                
                # Сохраняем с оптимизацией
                if ext in ['jpg', 'jpeg']:
                    img_resized.save(filepath, 'JPEG', quality=85, optimize=True)
                elif ext == 'png':
                    img_resized.save(filepath, 'PNG', optimize=True)
                else:
                    img_resized.save(filepath)
                
                saved_filenames[size_name] = filename
            
            # Возвращаем имя thumbnail-файла (основное)
            return saved_filenames['thumbnail'], None
            
        except Exception as e:
            print(f"Error processing category image: {e}")
            return None, str(e)
    
    return None, "Invalid file format"

@main.route('/')
def index():
    category_id = request.args.get('category_id')
    search_term = request.args.get('search', '').strip()
    location = request.args.get('location', '').strip()
    query = Product.query.filter_by(status=Product.STATUS_PUBLISHED)
    if category_id and category_id.isdigit():
        query = query.filter_by(category_id=int(category_id))
    if search_term:
        query = query.filter(
            Product.title.ilike(f'%{search_term}%') | 
            Product.description.ilike(f'%{search_term}%')
        )
    if location and location != 'Все регионы':
        query = query.filter(
            (Product.region == location) | 
            (Product.city == location)
        )
    query = query.options(joinedload(Product.product_category))
    products = query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('main.html', 
                         products=products, 
                         categories=categories,
                         search_term=search_term)

@main.route('/dashboard')
@login_required
def dashboard():
    user_products = Product.query.options(joinedload(Product.product_category)).filter_by(user_id=current_user.id).order_by(Product.created_at.desc()).all()
    
    # Автоматически снимаем с публикации просроченные товары
    expired_count = Product.query.filter(
        Product.user_id == current_user.id,
        Product.status == Product.STATUS_PUBLISHED,
        Product.expires_at <= datetime.utcnow()
    ).update({Product.status: Product.STATUS_READY_FOR_PUBLICATION})
    if expired_count > 0:
        db.session.commit()
        # После коммита перезагружаем данные
        user_products = Product.query.options(joinedload(Product.product_category)).filter_by(user_id=current_user.id).order_by(Product.created_at.desc()).all()

    # Добавляем image_list к каждому объекту Product для корректного отображения в шаблоне
    for product in user_products:
        product.image_list = _deserialize_images(product.images)

    # Подготавливаем JSON-данные для JS (остаётся как есть)
    products_data = []
    for product in user_products:
        product_dict = {
            'id': product.id,
            'title': product.title,
            'description': product.description,
            'price': product.price,
            'quantity': product.quantity,
            'manufacturer': product.manufacturer,
            'category_id': product.category_id,
            'images': _deserialize_images(product.images),
            'status': product.status,
            'status_text': product.status_text,
            'created_at': product.created_at.isoformat() if product.created_at else None,
            'expires_at': product.expires_at.isoformat() if product.expires_at else None,
            'view_count': product.view_count,
            'vat_included': product.vat_included,
            'condition': product.condition,
            'region': product.region,
            'city': product.city,
            'delivery': product.delivery,
            'days_remaining': product.days_remaining,
            'is_expired': product.is_expired,
            'product_category': {
                'id': product.product_category.id if product.product_category else None,
                'name': product.product_category.name if product.product_category else None
            } if product.product_category else None
        }
        products_data.append(product_dict)

    return render_template('dashboard.html', 
                         products=user_products,
                         products_json=products_data,
                         now=datetime.utcnow())

@main.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.options(
        joinedload(Product.product_category),
        joinedload(Product.owner)
    ).get_or_404(product_id)
    can_view = (
        product.status == Product.STATUS_PUBLISHED or
        (current_user.is_authenticated and (current_user.id == product.user_id or current_user.role == 'admin'))
    )
    if not can_view:
        flash('Этот товар недоступен для просмотра', 'error')
        return redirect(url_for('main.index'))
    if product.status == Product.STATUS_PUBLISHED:
        product.view_count = (product.view_count or 0) + 1
        db.session.commit()
    return render_template('product_detail.html', product=product)

@main.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            price = request.form.get('price')
            category_id_str = request.form.get('category_id', '').strip()
            if not title:
                flash('Название товара обязательно для заполнения', 'error')
                return redirect(url_for('main.add_product'))
            if not price:
                flash('Цена товара обязательна для заполнения', 'error')
                return redirect(url_for('main.add_product'))
            if not category_id_str:
                flash('Категория товара обязательна для выбора', 'error')
                return redirect(url_for('main.add_product'))
            try:
                category_id_int = int(category_id_str)
            except (ValueError, TypeError):
                flash('Некорректный выбор категория', 'error')
                return redirect(url_for('main.add_product'))
            category = Category.query.get(category_id_int)
            if not category:
                flash('Выбранная категория не существует', 'error')
                return redirect(url_for('main.add_product'))
            region_id = request.form.get('region_id')
            city_id = request.form.get('city_id')
            old_region = request.form.get('old_region', '').strip()
            old_city = request.form.get('old_city', '').strip()
            region_name = None
            city_name = None
            if region_id:
                region = Region.query.get(int(region_id))
                region_name = region.name if region else old_region
            else:
                region_name = old_region
            if city_id:
                city = City.query.get(int(city_id))
                city_name = city.name if city else old_city
            else:
                city_name = old_city
            if not region_name:
                flash('Субъект РФ обязателен для выбора', 'error')
                return redirect(url_for('main.add_product'))
            if not city_name:
                flash('Город обязателен для выбора', 'error')
                return redirect(url_for('main.add_product'))

            # === Получение и валидация количества и производителя ===
            quantity_str = request.form.get('quantity', '1')
            manufacturer = request.form.get('manufacturer', '').strip()

            try:
                quantity = int(quantity_str)
                if quantity < 1:
                    quantity = 1
            except (ValueError, TypeError):
                quantity = 1
            # === Конец получения количества и производителя ===

            uploaded_files = request.files.getlist('image_files')
            new_images = []
            if uploaded_files and any(f.filename for f in uploaded_files):
                for file in uploaded_files:
                    if file and file.filename:
                        if not allowed_file(file.filename):
                            flash('Недопустимый тип файла. Разрешены: png, jpg, jpeg, gif, webp', 'error')
                            return redirect(url_for('main.add_product'))
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        new_images.append(unique_filename)

            new_product = Product(
                title=title,
                description=description,
                price=float(price),
                quantity=quantity,
                manufacturer=manufacturer,
                category_id=category_id_int,
                user_id=current_user.id,
                images=','.join(new_images) if new_images else None,
                status=Product.STATUS_PUBLISHED,
                vat_included=request.form.get('vat_included') == 'on', 
                condition=request.form.get('condition', 'new'),
                region=region_name,
                city=city_name,
                region_id=int(region_id) if region_id else None,
                city_id=int(city_id) if city_id else None,
                delivery=request.form.get('delivery') == 'on'
            )
            db.session.add(new_product)
            db.session.commit()
            flash('Товар успешно добавлен! Срок размещения - 30 дней', 'success')
            return redirect(url_for('main.dashboard'))
        except ValueError as e:
            flash(f'Некорректное значение: {str(e)}', 'error')
            return redirect(url_for('main.add_product'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении товара: {str(e)}', 'error')
            return redirect(url_for('main.add_product'))
    categories = Category.query.all()
    if not categories:
        flash('Прежде чем добавлять товары, создайте хотя бы одну категорию', 'warning')
        return redirect(url_for('main.admin_categories'))
    regions = Region.query.filter_by(parent_id=None).order_by(Region.name).all()
    return render_template('add_product.html', categories=categories, regions=regions)

@main.route('/product/<int:product_id>/renew', methods=['POST'])
@login_required
def renew_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        flash('У вас нет прав для продления этого товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    if product.status not in [Product.STATUS_READY_FOR_PUBLICATION, Product.STATUS_UNPUBLISHED]:
        flash('Этот товар нельзя опубликовать', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    try:
        product.publish()
        db.session.commit()
        flash('Товар успешно опубликован! Срок размещения - 30 дней', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при публикации товара', 'error')
    return redirect(url_for('main.dashboard'))

@main.route('/product/<int:product_id>/unpublish', methods=['POST'])
@login_required
def unpublish_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        flash('У вас нет прав для снятия этого товара с публикации', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    if product.status != Product.STATUS_PUBLISHED:
        flash('Этот товар уже не опубликован', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    try:
        product.unpublish()
        db.session.commit()
        flash('Товар снят с публикации. Теперь он виден только вам.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при снятии товара с публикации', 'error')
    return redirect(url_for('main.dashboard'))

@main.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id and current_user.role != 'admin':
        flash('У вас нет прав для редактирования этого товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            price = request.form.get('price')
            category_id = request.form.get('category_id')
            if not title:
                flash('Название товара обязательно для заполнения', 'error')
                return redirect(url_for('main.edit_product', product_id=product_id))
            if not price:
                flash('Цена товара обязательна для заполнения', 'error')
                return redirect(url_for('main.edit_product', product_id=product_id))
            if not category_id:
                flash('Категория товара обязательна для выбора', 'error')
                return redirect(url_for('main.edit_product', product_id=product_id))
            category = Category.query.get(int(category_id))
            if not category:
                flash('Выбранная категория не существует', 'error')
                return redirect(url_for('main.edit_product', product_id=product_id))
            region_id = request.form.get('region_id')
            city_id = request.form.get('city_id')
            old_region = request.form.get('old_region', '').strip()
            old_city = request.form.get('old_city', '').strip()
            region_name = None
            city_name = None
            if region_id:
                region = Region.query.get(int(region_id))
                region_name = region.name if region else old_region
            else:
                region_name = old_region
            if city_id:
                city = City.query.get(int(city_id))
                city_name = city.name if city else old_city
            else:
                city_name = old_city
            if not region_name:
                flash('Субъект РФ обязателен для выбора', 'error')
                return redirect(url_for('main.edit_product', product_id=product_id))
            if not city_name:
                flash('Город обязателен для выбора', 'error')
                return redirect(url_for('main.edit_product', product_id=product_id))
            product.title = title
            product.description = description
            product.price = float(price)
            product.quantity = int(request.form.get('quantity', 1))
            product.manufacturer = request.form.get('manufacturer')
            product.category_id = int(category_id)
            product.status = int(request.form.get('status'))
            product.vat_included = request.form.get('vat_included') == 'on'
            product.condition = request.form.get('condition', 'new')
            product.region = region_name
            product.city = city_name
            product.region_id = int(region_id) if region_id else None
            product.city_id = int(city_id) if city_id else None
            product.delivery = request.form.get('delivery') == 'on'
            expires_at_str = request.form.get('expires_at')
            if expires_at_str:
                product.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M')
            # ========== ИСПРАВЛЕННАЯ ОБРАБОТКА ИЗОБРАЖЕНИЙ ==========
            current_images = _deserialize_images(product.images)
            removed_images = request.form.get('removed_images', '')
            if removed_images:
                removed_list = [img.strip() for img in removed_images.split(',') if img.strip()]
                current_images = [img for img in current_images if img not in removed_list]
                for image_filename in removed_list:
                    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename)
                    if os.path.exists(image_path):
                        os.remove(image_path)
            uploaded_files = request.files.getlist('image_files')
            new_images = []
            if uploaded_files and any(f.filename for f in uploaded_files):
                available_slots = 8 - len(current_images)
                if available_slots <= 0:
                    flash('Достигнут лимит в 8 изображений. Удалите некоторые существующие изображения перед добавлением новых.', 'error')
                    return redirect(url_for('main.edit_product', product_id=product_id))
                files_to_process = uploaded_files[:available_slots]
                if len(uploaded_files) > available_slots:
                    flash(f'Добавлено {len(files_to_process)} из {len(uploaded_files)} изображений. Достигнут лимит в 8 изображений.', 'warning')
                for file in files_to_process:
                    if file and file.filename:
                        if not allowed_file(file.filename):
                            flash(f'Файл "{file.filename}" недопустимого типа. Разрешены: png, jpg, jpeg, gif, webp', 'error')
                            return redirect(url_for('main.edit_product', product_id=product_id))
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        new_images.append(unique_filename)
            if new_images:
                current_images.extend(new_images)
            current_images = current_images[:8]
            product.images = _serialize_images(current_images)
            # ========== КОНЕЦ ОБРАБОТКИ ИЗОБРАЖЕНИЙ ==========
            db.session.commit()
            flash('Товар успешно обновлен', 'success')
            return redirect(url_for('main.product_detail', product_id=product_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении товара: {str(e)}', 'error')
            return redirect(url_for('main.edit_product', product_id=product_id))
    categories = Category.query.all()
    if not categories:
        flash('Нет доступных категорий', 'error')
        return redirect(url_for('main.index'))
    regions = Region.query.filter_by(parent_id=None).order_by(Region.name).all()
    cities = []
    if product.region_id:
        cities = City.query.filter_by(region_id=product.region_id).order_by(City.name).all()
    elif product.region:
        region_obj = Region.query.filter_by(name=product.region).first()
        if region_obj:
            product.region_id = region_obj.id
            cities = City.query.filter_by(region_id=region_obj.id).order_by(City.name).all()
    # Десериализуем изображения для корректной передачи в шаблоне
    if product.images:
        if isinstance(product.images, str):
            product_images = [img.strip() for img in product.images.split(',') if img.strip()]
        elif isinstance(product.images, list):
            product_images = [img for img in product.images if img]
        else:
            product_images = []
    else:
        product_images = []
    return render_template('edit_product.html', 
                         product=product, 
                         product_images=product_images,
                         categories=categories,
                         regions=regions,
                         cities=cities)

@main.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id and current_user.role != 'admin':
        flash('У вас нет прав для удаления этого товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    try:
        if product.images:
            for image_filename in _deserialize_images(product.images):
                if isinstance(image_filename, str) and not image_filename.startswith('http'):
                    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename)
                    if os.path.exists(image_path):
                        os.remove(image_path)
        db.session.delete(product)
        db.session.commit()
        flash('Товар успешно удален', 'success')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))

@main.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    if os.path.exists(file_path):
        return send_from_directory(upload_folder, filename)
    else:
        return "File not found", 404

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username')
        current_user.company_name = request.form.get('company_name')
        current_user.inn = request.form.get('inn')
        current_user.legal_address = request.form.get('legal_address')
        current_user.contact_person = request.form.get('contact_person')
        current_user.position = request.form.get('position')
        current_user.phone = request.form.get('phone')
        current_user.industry = request.form.get('industry')
        current_user.about = request.form.get('about')
        new_password = request.form.get('new_password')
        if new_password and new_password.strip():
            if len(new_password) < 6:
                flash('Пароль должен содержать минимум 6 символов', 'error')
                return redirect(url_for('main.profile'))
            current_user.set_password(new_password)
            flash('Пароль успешно изменен', 'success')
        db.session.commit()
        flash('Данные успешно обновлены', 'success')
        return redirect(url_for('main.profile'))
    return render_template('profile.html')

@main.route('/admin/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_category':
            name = request.form.get('name')
            parent_id = request.form.get('parent_id') or None
            description = request.form.get('description')
            
            if not name:
                flash('Название категории обязательно', 'error')
                return redirect(url_for('main.admin_categories'))
            
            existing_category = Category.query.filter_by(name=name, parent_id=parent_id).first()
            if existing_category:
                flash('Такая категория уже существует', 'error')
                return redirect(url_for('main.admin_categories'))
            
            try:
                # === ОБРАБОТКА ЗАГРУЗКИ ИЗОБРАЖЕНИЯ ===
                image_filename = None
                if 'category_image' in request.files:
                    image_file = request.files['category_image']
                    if image_file and image_file.filename:
                        image_filename, error = process_category_image(image_file)
                        if error:
                            flash(f'Ошибка обработки изображения: {error}', 'warning')
                
                # === КОНЕЦ ОБРАБОТКИ ИЗОБРАЖЕНИЯ ===
                
                new_category = Category(
                    name=name,
                    description=description,
                    parent_id=parent_id if parent_id else None,
                    image=image_filename
                )
                db.session.add(new_category)
                db.session.commit()
                flash(f'Категория "{name}" успешно добавлена', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении категории: {str(e)}', 'error')
        
        elif action == 'edit_category':
            category_id = request.form.get('category_id')
            name = request.form.get('name')
            parent_id = request.form.get('parent_id') or None
            description = request.form.get('description')
            remove_image = request.form.get('remove_image') == 'on'
            
            category = Category.query.get(category_id)
            if not category:
                flash('Категория не найдена', 'error')
                return redirect(url_for('main.admin_categories'))
            
            try:
                category.name = name
                category.description = description
                category.parent_id = parent_id
                
                # Обработка изображения
                if remove_image and category.image:
                    # Удаляем старые файлы всех размеров
                    base_filename = category.image.rsplit('.', 1)[0]
                    ext = category.image.rsplit('.', 1)[1] if '.' in category.image else 'jpg'
                    
                    sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
                    for size in sizes:
                        if size == 'thumbnail':
                            filename = category.image
                        else:
                            filename = f"{base_filename}_{size}.{ext}"
                        
                        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories', filename)
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    category.image = None
                
                if 'category_image' in request.files:
                    image_file = request.files['category_image']
                    if image_file and image_file.filename:
                        # Удаляем старое изображение, если есть
                        if category.image:
                            base_filename = category.image.rsplit('.', 1)[0]
                            ext = category.image.rsplit('.', 1)[1] if '.' in category.image else 'jpg'
                            
                            sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
                            for size in sizes:
                                if size == 'thumbnail':
                                    filename = category.image
                                else:
                                    filename = f"{base_filename}_{size}.{ext}"
                                
                                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories', filename)
                                if os.path.exists(old_path):
                                    os.remove(old_path)
                        
                        # Сохраняем новое изображение
                        image_filename, error = process_category_image(image_file)
                        if error:
                            flash(f'Ошибка обработки изображения: {error}', 'warning')
                        else:
                            category.image = image_filename
                
                db.session.commit()
                flash(f'Категория "{name}" успешно обновлена', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при обновлении категории: {str(e)}', 'error')
        
        elif action == 'delete_category':
            category_id = request.form.get('category_id')
            if category_id:
                category = Category.query.get(category_id)
                if category:
                    children = Category.query.filter_by(parent_id=category_id).all()
                    if children:
                        flash(f'Нельзя удалить категорию "{category.name}" - у нее есть дочерние категории', 'error')
                    else:
                        products_in_category = Product.query.filter_by(category_id=category_id).count()
                        if products_in_category > 0:
                            flash(f'Нельзя удалить категорию "{category.name}" - в ней есть товары', 'error')
                        else:
                            # Удаляем файлы изображений всех размеров, если есть
                            if category.image:
                                base_filename = category.image.rsplit('.', 1)[0]
                                ext = category.image.rsplit('.', 1)[1] if '.' in category.image else 'jpg'
                                
                                sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
                                for size in sizes:
                                    if size == 'thumbnail':
                                        filename = category.image
                                    else:
                                        filename = f"{base_filename}_{size}.{ext}"
                                    
                                    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories', filename)
                                    if os.path.exists(image_path):
                                        os.remove(image_path)
                            
                            db.session.delete(category)
                            db.session.commit()
                            flash(f'Категория "{category.name}" удалена', 'success')
                else:
                    flash('Категория не найдена', 'error')
        
        elif action == 'clear_empty':
            categories = Category.query.all()
            deleted_count = 0
            for cat in categories:
                products_count = Product.query.filter_by(category_id=cat.id).count()
                children_count = Category.query.filter_by(parent_id=cat.id).count()
                if products_count == 0 and children_count == 0:
                    # Удаляем файлы изображений всех размеров, если есть
                    if cat.image:
                        base_filename = cat.image.rsplit('.', 1)[0]
                        ext = cat.image.rsplit('.', 1)[1] if '.' in cat.image else 'jpg'
                        
                        sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
                        for size in sizes:
                            if size == 'thumbnail':
                                filename = cat.image
                            else:
                                filename = f"{base_filename}_{size}.{ext}"
                            
                            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories', filename)
                            if os.path.exists(image_path):
                                os.remove(image_path)
                    
                    db.session.delete(cat)
                    deleted_count += 1
            if deleted_count > 0:
                db.session.commit()
                flash(f'Удалено {deleted_count} пустых категорий', 'success')
            else:
                flash('Пустых категорий не найдено', 'info')
        
        elif action == 'clear_images':
            # Находим все категории с изображениями
            categories_with_images = Category.query.filter(Category.image.isnot(None)).all()
            deleted_count = 0
            for cat in categories_with_images:
                if cat.image:
                    # Удаляем файлы всех размеров
                    base_filename = cat.image.rsplit('.', 1)[0]
                    ext = cat.image.rsplit('.', 1)[1] if '.' in cat.image else 'jpg'
                    
                    sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
                    for size in sizes:
                        if size == 'thumbnail':
                            filename = cat.image
                        else:
                            filename = f"{base_filename}_{size}.{ext}"
                        
                        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories', filename)
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    # Очищаем поле в БД
                    cat.image = None
                    deleted_count += 1
            if deleted_count > 0:
                db.session.commit()
                flash(f'Удалено {deleted_count} изображений категорий', 'success')
            else:
                flash('Изображений категорий не найдено', 'info')
        
        return redirect(url_for('main.admin_categories'))
    
    # ========== ОЧИСТКА НАЗВАНИЙ РЕГИОНОВ ==========
    regions_to_clean = Region.query.filter(Region.name.like('% - %')).all()
    if regions_to_clean:
        for region in regions_to_clean:
            cleaned_name = region.name.split('-', 1)[-1].strip()
            region.name = cleaned_name
        db.session.commit()
        print(f"DEBUG: Очищены названия {len(regions_to_clean)} регионов")
    
    categories = Category.query.all()
    parent_categories = Category.query.filter_by(parent_id=None).all()
    total_products = Product.query.count()
    all_regions = Region.query.all()
    regions = Region.query.filter_by(parent_id=None).all()
    child_regions = Region.query.filter(Region.parent_id.isnot(None)).all()
    all_cities = City.query.all()
    cities_count = len(all_cities)
    
    # Подсчет категорий с изображениями
    try:
        categories_with_images = Category.query.filter(Category.image.isnot(None)).all()
    except AttributeError:
        categories_with_images = []
    
    regions_with_cities = []
    for region in regions:
        region_cities = [city for city in all_cities if city.region_id == region.id]
        regions_with_cities.append({
            'region': region,
            'cities': region_cities
        })
    
    return render_template('admin_categories.html', 
                         categories=categories,
                         parent_categories=parent_categories,
                         categories_with_images=categories_with_images,
                         total_products=total_products,
                         all_regions=all_regions,
                         regions=regions,
                         child_regions=child_regions,
                         cities=all_cities,
                         cities_count=cities_count,
                         regions_with_cities=regions_with_cities)

@main.route('/admin/upload-locations', methods=['POST'])
@login_required
def upload_locations():
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('main.admin_categories'))
    if 'locations_file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('main.admin_categories'))
    file = request.files['locations_file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('main.admin_categories'))
    file_type = request.form.get('file_type', 'json')
    clear_existing = request.form.get('clear_existing') == 'on'
    try:
        if clear_existing:
            products_count = Product.query.filter(
                (Product.region_id.isnot(None)) | (Product.city_id.isnot(None))
            ).count()
            if products_count > 0:
                flash(f'Нельзя удалить существующие данные - {products_count} товаров связаны с ними', 'error')
                return redirect(url_for('main.admin_categories'))
            City.query.delete()
            Region.query.delete()
            db.session.flush()
        added_regions = 0
        added_cities = 0
        region_cache = {}
        if file_type == 'csv':
            import csv
            import io
            content = file.read().decode('utf-8')
            for delimiter in [';', ',', '\t']:
                try:
                    csv_reader = csv.reader(io.StringIO(content), delimiter=delimiter)
                    rows = list(csv_reader)
                    if len(rows) > 0 and len(rows[0]) >= 2:
                        break
                except:
                    continue
            if rows and ('регион' in rows[0][0].lower() or 'region' in rows[0][0].lower()):
                rows = rows[1:]
            for row in rows:
                if len(row) >= 2:
                    region_name = row[0].strip()
                    city_name = row[1].strip()
                    if not region_name or not city_name:
                        continue
                    if region_name not in region_cache:
                        region = Region.query.filter_by(name=region_name, parent_id=None).first()
                        if not region:
                            region = Region(name=region_name)
                            db.session.add(region)
                            db.session.flush()
                            added_regions += 1
                        region_cache[region_name] = region
                    else:
                        region = region_cache[region_name]
                    existing_city = City.query.filter_by(
                        name=city_name, 
                        region_id=region.id
                    ).first()
                    if not existing_city:
                        city = City(name=city_name, region_id=region.id)
                        db.session.add(city)
                        added_cities += 1
        elif file_type == 'json':
            import json
            content = file.read().decode('utf-8')
            data = json.loads(content)
            if isinstance(data, dict) and 'regions' in data:
                for region_data in data['regions']:
                    region_name = region_data.get('name', '').strip()
                    cities_list = region_data.get('cities', [])
                    if not region_name:
                        continue
                    if region_name not in region_cache:
                        region = Region.query.filter_by(name=region_name, parent_id=None).first()
                        if not region:
                            region = Region(name=region_name)
                            db.session.add(region)
                            db.session.flush()
                            added_regions += 1
                        region_cache[region_name] = region
                    else:
                        region = region_cache[region_name]
                    for city_name in cities_list:
                        if isinstance(city_name, str) and city_name.strip():
                            city_name_clean = city_name.strip()
                            existing_city = City.query.filter_by(
                                name=city_name_clean, 
                                region_id=region.id
                            ).first()
                            if not existing_city:
                                city = City(name=city_name_clean, region_id=region.id)
                                db.session.add(city)
                                added_cities += 1
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        region_name = item.get('region', '').strip()
                        city_name = item.get('city', '').strip()
                        if not region_name or not city_name:
                            continue
                        if region_name not in region_cache:
                            region = Region.query.filter_by(name=region_name, parent_id=None).first()
                            if not region:
                                region = Region(name=region_name)
                                db.session.add(region)
                                db.session.flush()
                                added_regions += 1
                            region_cache[region_name] = region
                        else:
                            region = region_cache[region_name]
                        existing_city = City.query.filter_by(
                            name=city_name, 
                            region_id=region.id
                        ).first()
                        if not existing_city:
                            city = City(name=city_name, region_id=region.id)
                            db.session.add(city)
                            added_cities += 1
            else:
                flash('❌ Неподдерживаемый формат JSON файла', 'error')
                return redirect(url_for('main.admin_categories'))
        db.session.commit()
        if added_regions > 0 or added_cities > 0:
            flash(f'✅ Успешно добавлено {added_regions} регионов и {added_cities} городов', 'success')
        else:
            flash('⚠️ Новых регионов и городов не обнаружено', 'info')
    except json.JSONDecodeError as e:
        db.session.rollback()
        flash(f'❌ Ошибка чтения JSON: {str(e)}', 'error')
        print(f"Ошибка JSON: {str(e)}")
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Ошибка загрузки: {str(e)}', 'error')
        print(f"Ошибка загрузки локаций: {str(e)}")
    return redirect(url_for('main.admin_categories'))

@main.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к админке', 'error')
        return redirect(url_for('main.index'))
    search = request.args.get('search', '').strip()
    query = User.query
    if search:
        query = query.filter(
            User.username.ilike(f'%{search}%') |
            User.email.ilike(f'%{search}%') |
            User.company_name.ilike(f'%{search}%') |
            User.contact_person.ilike(f'%{search}%')
        )
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users, search=search)

@main.route('/admin/regions/add', methods=['POST'])
@login_required
def add_region():
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('main.admin_categories'))
    name = request.form.get('name', '').strip()
    parent_id = request.form.get('parent_id') or None
    description = request.form.get('description', '').strip()
    if not name:
        flash('Название обязательно', 'error')
        return redirect(url_for('main.admin_categories'))
    if parent_id:
        region = Region.query.get(parent_id)
        if not region:
            flash('Выбранный регион не существует', 'error')
            return redirect(url_for('main.admin_categories'))
        existing_city = City.query.filter_by(name=name, region_id=parent_id).first()
        if existing_city:
            flash(f'Город "{name}" уже существует в регионе "{region.name}"', 'error')
            return redirect(url_for('main.admin_categories'))
        try:
            new_city = City(
                name=name,
                region_id=int(parent_id),
                description=description
            )
            db.session.add(new_city)
            db.session.commit()
            flash(f'Город "{name}" добавлен в регион "{region.name}"', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании города: {str(e)}', 'error')
    else:
        existing_region = Region.query.filter_by(name=name, parent_id=None).first()
        if existing_region:
            flash('Такой регион уже существует', 'error')
            return redirect(url_for('main.admin_categories'))
        try:
            new_region = Region(
                name=name,
                description=description,
                parent_id=None
            )
            db.session.add(new_region)
            db.session.commit()
            flash(f'Регион "{name}" добавлен', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('main.admin_categories'))

@main.route('/admin/regions/delete/<int:region_id>', methods=['POST'])
@login_required
def delete_region(region_id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('main.admin_categories'))
    region = Region.query.get_or_404(region_id)
    children = Region.query.filter_by(parent_id=region_id).all()
    if children:
        flash(f'Нельзя удалить регион "{region.name}" — есть подрегионы', 'error')
    else:
        db.session.delete(region)
        db.session.commit()
        flash(f'Регион "{region.name}" удалён', 'success')
    return redirect(url_for('main.admin_categories'))

@main.route('/admin/upload-categories', methods=['POST'])
@login_required
def upload_categories():
    import json
    if 'categories_file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('main.admin_categories'))
    file = request.files['categories_file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('main.admin_categories'))
    if not file.filename.endswith('.json'):
        flash('Только JSON файлы поддерживаются', 'error')
        return redirect(url_for('main.admin_categories'))
    try:
        categories_data = json.load(file)
        Category.query.delete()
        parent_count = 0
        child_count = 0
        for parent_data in categories_data:
            parent_category = Category(
                name=parent_data['name'],
                description=parent_data.get('description', '')
            )
            db.session.add(parent_category)
            db.session.flush()
            parent_count += 1
            for child_data in parent_data.get('children', []):
                child_category = Category(
                    name=child_data['name'],
                    description=child_data.get('description', ''),
                    parent_id=parent_category.id
                )
                db.session.add(child_category)
                child_count += 1
        db.session.commit()
        flash(f'✅ Загружено {parent_count} родительских и {child_count} дочерних категорий!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Ошибка загрузки: {str(e)}', 'error')
    return redirect(url_for('main.admin_categories'))

@main.route('/admin/clear-categories', methods=['POST'])
@login_required
def clear_categories():
    try:
        Product.query.update({Product.category_id: None})
        db.session.commit()
        count = Category.query.count()
        Category.query.delete()
        db.session.commit()
        flash(f'✅ Удалено {count} категорий', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Ошибка очистки: {str(e)}', 'error')
    return redirect(url_for('main.admin_categories'))

@main.route('/admin/cities/add', methods=['POST'])
@login_required
def add_city():
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('main.admin_categories'))
    name = request.form.get('name', '').strip()
    region_id = request.form.get('region_id')
    description = request.form.get('description', '').strip()
    if not name:
        flash('Название города обязательно', 'error')
        return redirect(url_for('main.admin_categories'))
    if not region_id:
        flash('Выберите регион', 'error')
        return redirect(url_for('main.admin_categories'))
    existing = City.query.filter_by(name=name, region_id=region_id).first()
    if existing:
        flash('Такой город уже существует в этом регионе', 'error')
        return redirect(url_for('main.admin_categories'))
    try:
        new_city = City(
            name=name,
            region_id=int(region_id),
            description=description
        )
        db.session.add(new_city)
        db.session.commit()
        flash(f'Город "{name}" добавлен', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('main.admin_categories'))

@main.route('/admin/cities/delete/<int:city_id>', methods=['POST'])
@login_required
def delete_city(city_id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('main.admin_categories'))
    city = City.query.get_or_404(city_id)
    products_count = Product.query.filter_by(city=city.name).count()
    if products_count > 0:
        flash(f'Нельзя удалить город "{city.name}" — в нем есть товары', 'error')
        return redirect(url_for('main.admin_categories'))
    db.session.delete(city)
    db.session.commit()
    flash(f'Город "{city.name}" удалён', 'success')
    return redirect(url_for('main.admin_categories'))

# ========== API ДЛЯ ПОЛУЧЕНИЯ ЛОКАЦИЙ ==========
@main.route('/api/locations')
def get_locations():
    try:
        search = request.args.get('search', '').strip()
        limit = int(request.args.get('limit', 30))
        results = []
        results.append({
            'id': 'all',
            'name': 'Все регионы',
            'type': 'all',
            'display_name': 'Все регионы'
        })
        if not search:
            popular_locations = [
                'Москва',
                'Санкт-Петербург', 
                'Казань',
                'Екатеринбург',
                'Новосибирск',
                'Нижний Новгород',
                'Ростов-на-Дону',
                'Уфа',
                'Красноярск',
                'Воронеж',
                'Пермь',
                'Волгоград',
                'Саратов',
                'Омск',
                'Челябинск',
                'Самара'
            ]
            for loc_name in popular_locations:
                city = City.query.filter_by(name=loc_name).first()
                if city:
                    results.append({
                        'id': f'city_{city.id}',
                        'name': city.name,
                        'type': 'city',
                        'display_name': f"{city.name} ({city.region.name if city.region else 'Неизвестный регион'})"
                    })
                    continue
                region = Region.query.filter_by(name=loc_name).first()
                if region:
                    results.append({
                        'id': f'region_{region.id}',
                        'name': region.name,
                        'type': 'region',
                        'display_name': region.name
                    })
        else:
            search_lower = search.lower()
            regions_start = Region.query.filter(
                Region.name.ilike(f'{search_lower}%')
            ).order_by(Region.name).limit(limit // 2).all()
            regions_contains = Region.query.filter(
                Region.name.ilike(f'%{search_lower}%')
            ).order_by(Region.name).limit(limit // 2).all()
            all_regions = regions_start + [r for r in regions_contains if r not in regions_start]
            all_regions = all_regions[:limit // 2]
            for region in all_regions:
                results.append({
                    'id': f'region_{region.id}',
                    'name': region.name,
                    'type': 'region',
                    'display_name': region.name
                })
            cities_start = City.query.join(Region).filter(
                City.name.ilike(f'{search_lower}%')
            ).order_by(City.name).limit(limit // 2).all()
            cities_contains = City.query.join(Region).filter(
                City.name.ilike(f'%{search_lower}%')
            ).order_by(City.name).limit(limit // 2).all()
            all_cities = cities_start + [c for c in cities_contains if c not in cities_start]
            all_cities = all_cities[:limit // 2]
            for city in all_cities:
                results.append({
                    'id': f'city_{city.id}',
                    'name': city.name,
                    'type': 'city',
                    'display_name': f"{city.name} ({city.region.name if city.region else 'Неизвестный регион'})"
                })
        if search and len(results) <= 1:
            popular_cities_extended = [
                'Архангельск', 'Астрахань', 'Анапа', 'Альметьевск', 'Абакан',
                'Брянск', 'Белгород', 'Барнаул', 'Благовещенск', 'Бийск', 'Братск',
                'Владивосток', 'Волгоград', 'Владимир', 'Вологда', 'Воронеж',
                'Грозный', 'Геленджик',
                'Донецк', 'Дзержинск', 'Димитровград',
                'Екатеринбург', 'Елец', 'Евпатория',
                'Железногорск',
                'Златоуст',
                'Ижевск', 'Иркутск', 'Иваново',
                'Йошкар-Ола',
                'Казань', 'Краснодар', 'Красноярск', 'Калининград', 'Кемерово',
                'Киров', 'Кострома', 'Курск', 'Курган', 'Комсомольск-на-Амуре',
                'Липецк', 'Люберцы',
                'Москва', 'Махачкала', 'Мурманск', 'Магнитогорск', 'Муром',
                'Нижний Новгород', 'Новосибирск', 'Новороссийск', 'Норильск',
                'Набережные Челны', 'Нефтеюганск',
                'Омск', 'Оренбург', 'Орёл', 'Обнинск',
                'Пермь', 'Пенза', 'Псков', 'Петрозаводск', 'Подольск',
                'Ростов-на-Дону', 'Рязань', 'Рыбинск',
                'Санкт-Петербург', 'Самара', 'Саратов', 'Смоленск', 'Сочи',
                'Ставрополь', 'Стерлитамак', 'Сургут', 'Сыктывкар', 'Северодвинск',
                'Тверь', 'Тула', 'Тюмень', 'Таганрог', 'Тольятти', 'Томск',
                'Уфа', 'Ульяновск', 'Улан-Удэ',
                'Феодосия',
                'Хабаровск', 'Химки',
                'Челябинск', 'Чебоксары', 'Чита',
                'Шахты',
                'Щёлково',
                'Элиста', 'Энгельс',
                'Южно-Сахалинск',
                'Ярославль', 'Якутск'
            ]
            search_lower = search.lower()
            found_in_static = False
            for city_name in popular_cities_extended:
                if search_lower in city_name.lower():
                    city_lower = city_name.lower()
                    if city_lower.startswith(search_lower):
                        results.insert(1, {
                            'id': f'static_city_{city_name}',
                            'name': city_name,
                            'type': 'city',
                            'display_name': city_name,
                            'priority': 1
                        })
                    else:
                        results.append({
                            'id': f'static_city_{city_name}',
                            'name': city_name,
                            'type': 'city',
                            'display_name': city_name,
                            'priority': 0
                        })
                    found_in_static = True
        def sort_key(item):
            if item['display_name'] == 'Все регионы':
                return (0, '')
            elif item.get('priority') == 1:
                return (1, item['display_name'])
            else:
                return (2, item['display_name'])
        results.sort(key=sort_key)
        seen = set()
        unique_results = []
        for item in results:
            if item['display_name'] not in seen:
                seen.add(item['display_name'])
                unique_results.append(item)
        return jsonify(unique_results[:limit])
    except Exception as e:
        fallback_results = [
            {'id': 'all', 'name': 'Все регионы', 'type': 'all', 'display_name': 'Все регионы'},
            {'id': 'city_1', 'name': 'Москва', 'type': 'city', 'display_name': 'Москва'},
            {'id': 'city_2', 'name': 'Санкт-Петербург', 'type': 'city', 'display_name': 'Санкт-Петербург'},
            {'id': 'city_3', 'name': 'Казань', 'type': 'city', 'display_name': 'Казань'},
            {'id': 'city_4', 'name': 'Екатеринбург', 'type': 'city', 'display_name': 'Екатеринбург'},
            {'id': 'city_5', 'name': 'Новосибирск', 'type': 'city', 'display_name': 'Новосибирск'},
            {'id': 'city_6', 'name': 'Нижний Новгород', 'type': 'city', 'display_name': 'Нижний Новгород'},
            {'id': 'city_7', 'name': 'Ростов-на-Дону', 'type': 'city', 'display_name': 'Ростов-на-Дону'},
            {'id': 'city_8', 'name': 'Уфа', 'type': 'city', 'display_name': 'Уфа'},
        ]
        if search:
            search_lower = search.lower()
            filtered_results = [fallback_results[0]]
            for item in fallback_results[1:]:
                if search_lower in item['name'].lower():
                    filtered_results.append(item)
            return jsonify(filtered_results)
        return jsonify(fallback_results)

@main.route('/api/regions')
def get_regions():
    regions = Region.query.filter_by(parent_id=None).order_by(Region.name).all()
    result = []
    for region in regions:
        region_data = {
            'id': region.id,
            'name': region.name,
            'cities': []
        }
        cities = City.query.filter_by(region_id=region.id).order_by(City.name).all()
        for city in cities:
            region_data['cities'].append({
                'id': city.id,
                'name': city.name,
                'full_name': f"{city.name} ({region.name})"
            })
        result.append(region_data)
    return jsonify(result)

@main.route('/api/cities/by-region/<int:region_id>')
def get_cities_by_region(region_id):
    cities = City.query.filter_by(region_id=region_id).order_by(City.name).all()
    result = []
    for city in cities:
        result.append({
            'id': city.id,
            'name': city.name,
            'full_name': f"{city.name} (Регион ID: {region_id})"
        })
    import json
    response = current_app.response_class(
        response=json.dumps(result, ensure_ascii=False),
        status=200,
        mimetype='application/json; charset=utf-8'
    )
    return response

@main.route('/update_expired_products')
def update_expired_products():
    expired_products = Product.query.filter(
        Product.status == Product.STATUS_PUBLISHED,
        Product.expires_at < datetime.utcnow()
    ).all()
    updated_count = 0
    for product in expired_products:
        if product.update_status():
            updated_count += 1
    if updated_count > 0:
        db.session.commit()
    return f'Обновлено {updated_count} товаров с истекшим сроком публикации'

@main.route('/product/<int:product_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    product = Product.query.get_or_404(product_id)
    if product in current_user.favorited_products:
        current_user.favorited_products.remove(product)
    else:
        current_user.favorited_products.append(product)
    db.session.commit()
    return redirect(url_for('main.product_detail', product_id=product_id))

@main.route('/messages/<int:user_id>/<int:product_id>')
@login_required
def messages(user_id, product_id):
    flash('Система сообщений находится в разработке', 'info')
    return redirect(url_for('main.product_detail', product_id=product_id))

@main.route('/product/<int:product_id>/report', methods=['POST'])
@login_required
def report_product(product_id):
    product = Product.query.get_or_404(product_id)
    reason = request.form.get('reason')
    if reason:
        flash('Жалоба отправлена. Спасибо за участие!', 'success')
    else:
        flash('Выберите причину жалобы', 'error')
    return redirect(url_for('main.product_detail', product_id=product_id))

@main.route('/favorites')
@login_required
def favorites():
    favorite_products = current_user.favorited_products.all()
    return render_template('favorites.html', products=favorite_products)

@main.route('/user/<int:user_id>/reviews')
def user_reviews(user_id):
    user = User.query.get_or_404(user_id)
    reviews = Review.query.filter(
        Review.seller_id == user_id,
        Review.is_published == True
    ).order_by(Review.created_at.desc()).all()
    total_reviews = len(reviews)
    if total_reviews > 0:
        average_rating = sum(r.rating for r in reviews) / total_reviews
        average_rating = round(average_rating, 1)
        rating_distribution = {1:0, 2:0, 3:0, 4:0, 5:0}
        for review in reviews:
            rating_distribution[review.rating] += 1
    else:
        average_rating = 0
        rating_distribution = {1:0, 2:0, 3:0, 4:0, 5:0}
    return render_template('user_reviews.html',
                         user=user,
                         reviews=reviews,
                         total_reviews=total_reviews,
                         average_rating=average_rating,
                         rating_distribution=rating_distribution)

@main.route('/product/<int:product_id>/add_review', methods=['GET', 'POST'])
@login_required
def add_review(product_id):
    product = Product.query.get_or_404(product_id)
    if current_user.id == product.user_id:
        flash('Вы не можете оставить отзыв на свой товар', 'error')
        return redirect(request.referrer or url_for('main.index'))
    existing_review = Review.query.filter_by(
        seller_id=product.user_id,
        buyer_id=current_user.id,
        product_id=product_id
    ).first()
    if existing_review:
        flash('Вы уже оставляли отзыв на этот товар', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    form = ReviewForm()
    if form.validate_on_submit():
        try:
            review = Review(
                seller_id=product.user_id,
                buyer_id=current_user.id,
                product_id=product_id,
                rating=form.rating.data,
                text=form.text.data
            )
            db.session.add(review)
            db.session.commit()
            flash('Спасибо за ваш отзыв! Он будет опубликован после проверки.', 'success')
            return redirect(url_for('main.product_detail', product_id=product_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении отзыва: {str(e)}', 'error')
    return render_template('add_review.html', 
                         form=form, 
                         product=product)

@main.route('/user/<int:user_id>/add_review_direct', methods=['GET', 'POST'])
@login_required
def add_review_direct(user_id):
    seller = User.query.get_or_404(user_id)
    if current_user.id == seller.id:
        flash('Вы не можете оставить отзыв самому себе', 'error')
        return redirect(url_for('main.user_reviews', user_id=user_id))
    form = ReviewForm()
    if form.validate_on_submit():
        try:
            review = Review(
                seller_id=seller.id,
                buyer_id=current_user.id,
                rating=form.rating.data,
                text=form.text.data
            )
            db.session.add(review)
            db.session.commit()
            flash('Спасибо за ваш отзыв! Он будет опубликован после проверки.', 'success')
            return redirect(request.referrer or url_for('main.product_detail', product_id=...))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении отзыва: {str(e)}', 'error')
    return render_template('add_review_direct.html', 
                         form=form, 
                         seller=seller)

@main.route('/user/<int:user_id>/profile')
def user_profile_modal(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('partials/user_profile_modal.html', user=user)

@main.route('/user/<int:user_id>/reviews_content')
def user_reviews_content(user_id):
    from app.models import User, Review
    user = User.query.get_or_404(user_id)
    reviews = Review.query.filter(
        Review.seller_id == user.id,
        Review.is_published == True
    ).order_by(Review.created_at.desc()).all()
    return render_template('partials/user_reviews_content.html', user=user, reviews=reviews)

@main.route('/user/<int:user_id>/review_form')
def review_form(user_id):
    from app.models import User, Review
    from app.forms import ReviewForm
    seller = User.query.get_or_404(user_id)
    if current_user.is_authenticated:
        existing_review = Review.query.filter_by(
            seller_id=seller.id,
            buyer_id=current_user.id
        ).first()
        if existing_review:
            return '<div class="p-3 text-center"><p class="text-muted">Вы уже оставили отзыв этому пользователю.</p><button class="btn btn-sm btn-secondary" onclick="closeReviewFormModal()">Закрыть</button></div>'
    form = ReviewForm()
    return render_template('partials/review_form.html', seller=seller, form=form)

@main.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    from app.models import Review
    review = Review.query.get_or_404(review_id)
    if review.buyer_id != current_user.id:
        flash('Вы не можете удалить чужой отзыв.', 'danger')
        return redirect(request.referrer or url_for('main.index'))
    db.session.delete(review)
    db.session.commit()
    flash('Ваш отзыв удалён.', 'success')
    return redirect(request.referrer or url_for('main.index'))

@main.route('/api/test-populate-locations')
def test_populate_locations():
    try:
        test_regions = [
            'Москва',
            'Санкт-Петербург', 
            'Республика Татарстан',
            'Московская область',
            'Свердловская область',
            'Краснодарский край',
            'Республика Башкортостан',
            'Нижегородская область',
            'Челябинская область',
            'Новосибирская область',
            'Самарская область',
            'Ростовская область',
            'Красноярский край',
            'Пермский край',
            'Воронежская область'
        ]
        test_cities = [
            {'name': 'Москва', 'region': 'Москва'},
            {'name': 'Санкт-Петербург', 'region': 'Санкт-Петербург'},
            {'name': 'Казань', 'region': 'Республика Татарстан'},
            {'name': 'Набережные Челны', 'region': 'Республика Татарстан'},
            {'name': 'Альметьевск', 'region': 'Республика Татарстан'},
            {'name': 'Балашиха', 'region': 'Московская область'},
            {'name': 'Химки', 'region': 'Московская область'},
            {'name': 'Подольск', 'region': 'Московская область'},
            {'name': 'Королёв', 'region': 'Московская область'},
            {'name': 'Екатеринбург', 'region': 'Свердловская область'},
            {'name': 'Нижний Тагил', 'region': 'Свердловская область'},
            {'name': 'Каменск-Уральский', 'region': 'Свердловская область'},
            {'name': 'Краснодар', 'region': 'Краснодарский край'},
            {'name': 'Сочи', 'region': 'Краснодарский край'},
            {'name': 'Новороссийск', 'region': 'Краснодарский край'},
            {'name': 'Уфа', 'region': 'Республика Башкортостан'},
            {'name': 'Стерлитамак', 'region': 'Республика Башкортостан'},
            {'name': 'Салават', 'region': 'Республика Башкортостан'},
            {'name': 'Нижний Новгород', 'region': 'Нижегородская область'},
            {'name': 'Дзержинск', 'region': 'Нижегородская область'},
            {'name': 'Арзамас', 'region': 'Нижегородская область'},
            {'name': 'Челябинск', 'region': 'Челябинская область'},
            {'name': 'Магнитогорск', 'region': 'Челябинская область'},
            {'name': 'Златоуст', 'region': 'Челябинская область'},
            {'name': 'Новосибирск', 'region': 'Новосибирская область'},
            {'name': 'Бердск', 'region': 'Новосибирская область'},
            {'name': 'Самара', 'region': 'Самарская область'},
            {'name': 'Тольятти', 'region': 'Самарская область'},
            {'name': 'Сызрань', 'region': 'Самарская область'},
            {'name': 'Ростов-на-Дону', 'region': 'Ростовская область'},
            {'name': 'Таганрог', 'region': 'Ростовская область'},
            {'name': 'Шахты', 'region': 'Ростовская область'},
            {'name': 'Красноярск', 'region': 'Красноярский край'},
            {'name': 'Норильск', 'region': 'Красноярский край'},
            {'name': 'Пермь', 'region': 'Пермский край'},
            {'name': 'Березники', 'region': 'Пермский край'},
            {'name': 'Воронеж', 'region': 'Воронежская область'},
            {'name': 'Борисоглебск', 'region': 'Воронежская область'}
        ]
        created_regions = {}
        for region_name in test_regions:
            region = Region.query.filter_by(name=region_name).first()
            if not region:
                region = Region(name=region_name)
                db.session.add(region)
                db.session.flush()
            created_regions[region_name] = region
        for city_data in test_cities:
            region = created_regions.get(city_data['region'])
            if region:
                city = City.query.filter_by(name=city_data['name'], region_id=region.id).first()
                if not city:
                    city = City(
                        name=city_data['name'],
                        region_id=region.id
                    )
                    db.session.add(city)
        db.session.commit()
        return f"✅ Создано {len(created_regions)} регионов и {len(test_cities)} городов"
    except Exception as e:
        db.session.rollback()
        return f"❌ Ошибка: {str(e)}"

@main.route('/api/debug/locations-status')
def debug_locations_status():
    try:
        regions_count = Region.query.count()
        cities_count = City.query.count()
        regions_sample = Region.query.limit(5).all()
        cities_sample = City.query.join(Region).limit(5).all()
        return jsonify({
            'status': 'ok',
            'regions_count': regions_count,
            'cities_count': cities_count,
            'regions_sample': [r.name for r in regions_sample],
            'cities_sample': [{'name': c.name, 'region': c.region.name} for c in cities_sample]
        })
    except Exception as e:
        print(f"Ошибка в /api/locations: {str(e)}")
        return jsonify([
            {'id': 'all', 'name': 'Все регионы', 'type': 'all', 'display_name': 'Все регионы'},
            {'id': 'city_1', 'name': 'Москва', 'type': 'city', 'display_name': 'Москва'},
        ])

@main.route('/debug-upload', methods=['POST'])
@csrf.exempt
def debug_upload():
    print("\n=== DEBUG UPLOAD ===")
    print(f"request.content_length: {request.content_length}")
    print(f"request.content_type: {request.content_type}")
    files = request.files.getlist('test_files')
    print(f"Получено файлов: {len(files)}")
    for i, f in enumerate(files):
        print(f"Файл {i}: {f.filename}")
        print(f"  content_length: {f.content_length}")
        if f and f.filename:
            current_pos = f.tell()
            f.seek(0)
            first_bytes = f.read(10)
            print(f"  Первые 10 байт (hex): {first_bytes.hex()}")
            f.seek(0)
            all_data = f.read()
            print(f"  Прочитано всего байт: {len(all_data)}")
            print(f"  Данные (первые 50): {all_data[:50]}")
            f.seek(current_pos)
    return "OK", 200

@main.route('/privacy-policy')
def privacy_policy():
    return render_template('policy.html')

@main.app_template_filter('deserialize_images')
def deserialize_images_filter(images_field):
    """Jinja-фильтр для безопасной десериализации изображений"""
    return _deserialize_images(images_field)

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ИЗОБРАЖЕНИЯМИ КАТЕГОРИЙ ==========

@main.route('/upload_category_image', methods=['POST'])
@login_required
def upload_category_image():
    """Загрузка изображения для категории"""
    if 'category_image' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    category_id = request.form.get('category_id')
    if not category_id:
        return jsonify({'error': 'Category ID is required'}), 400
    
    file = request.files['category_image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Обрабатываем изображение
    filename, error = process_category_image(file, category_id)
    
    if error:
        return jsonify({'error': error}), 400
    
    # Обновляем категорию в базе
    category = Category.query.get(int(category_id))
    if category:
        # Удаляем старое изображение если есть
        if category.image:
            try:
                # Удаляем все размеры
                base_filename = category.image.rsplit('.', 1)[0]
                ext = category.image.rsplit('.', 1)[1] if '.' in category.image else 'jpg'
                
                sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
                for size in sizes:
                    if size == 'thumbnail':
                        old_filename = category.image
                    else:
                        old_filename = f"{base_filename}_{size}.{ext}"
                    
                    old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories', old_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
            except Exception as e:
                print(f"Error deleting old image: {e}")
        
        category.image = filename
        db.session.commit()
        
        return jsonify({
            'success': True,
            'image_url': url_for('main.get_category_image_by_size', 
                               category_id=category_id, 
                               size='thumbnail'),
            'filename': filename
        })
    
    return jsonify({'error': 'Category not found'}), 404

@main.route('/category/<int:category_id>/image/<size>')
def get_category_image_by_size(category_id, size='thumbnail'):
    """Возвращает изображение категории нужного размера"""
    category = Category.query.get_or_404(category_id)
    
    if not category.image:
        # Возвращаем дефолтное изображение
        return send_from_directory(
            os.path.join(current_app.root_path, 'static', 'icons'),
            'category_default.png'
        )
    
    # Определяем имя файла нужного размера
    base_filename = category.image.rsplit('.', 1)[0]
    ext = category.image.rsplit('.', 1)[1] if '.' in category.image else 'jpg'
    
    # Поддерживаемые размеры
    valid_sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
    if size not in valid_sizes:
        size = 'thumbnail'
    
    # Формируем имя файла
    if size == 'thumbnail':
        filename = category.image  # thumbnail - основное имя
    else:
        filename = f"{base_filename}_{size}.{ext}"
    
    # Проверяем существует ли файл
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories', filename)
    
    if not os.path.exists(filepath):
        # Если файла нужного размера нет, возвращаем thumbnail
        filename = category.image
    
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories'),
        filename
    )

# Старая функция для обратной совместимости - перенаправляет на новую
@main.route('/category_image/<filename>')
def category_image(filename):
    """Отдача изображений категорий (для обратной совместимости)"""
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories'),
        filename
    )