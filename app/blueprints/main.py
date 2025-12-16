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

main = Blueprint('main', __name__, template_folder='../../templates')

try:
    from app.forms import ReviewForm
except ImportError:
    class ReviewForm:
        def __init__(self, *args, **kwargs):
            pass
        def validate_on_submit(self):
            return False

from app.utils import allowed_file, _deserialize_images, _serialize_images, process_category_image

@main.app_template_filter('deserialize_images')
def deserialize_images_filter(images_field):
    """Jinja-фильтр для безопасной десериализации изображений"""
    return _deserialize_images(images_field)

@main.route('/privacy-policy')
def privacy_policy():
    return render_template('policy.html')

@main.route('/help')
def help():
    return render_template('help.html')



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
    
    # Используем иерархический список категорий (список словарей)
    from app.utils import get_category_choices
    categories = get_category_choices()
    
    # Для плиток категорий (только верхний уровень)
    root_categories = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    
    return render_template('main.html', 
                         products=products, 
                         categories=categories,
                         root_categories=root_categories,
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
    is_favorited = False
    if product in current_user.favorited_products:
        current_user.favorited_products.remove(product)
        is_favorited = False
    else:
        current_user.favorited_products.append(product)
        is_favorited = True
    
    db.session.commit()
    
    # Return JSON if requested (for AJAX)
    if request.is_json or request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({'success': True, 'is_favorited': is_favorited})
        
    return redirect(request.referrer or url_for('main.index'))

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
            os.path.join(current_app.root_path, 'static', 'images'),
            'no-image.png'
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
        # Если файла нужного размера нет, пробуем вернуть оригинал (thumbnail)
        filename = category.image
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories', filename)
        
        # Если и оригинала нет, возвращаем заглушку
        if not os.path.exists(filepath):
            return send_from_directory(
                os.path.join(current_app.root_path, 'static', 'images'),
                'no-image.png'
            )
    
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

@main.route('/contact', methods=['POST'])
def contact():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    contact_info = data.get('contact_info')
    category = data.get('category')
    message = data.get('message')
    
    if not contact_info or not message:
        return jsonify({'success': False, 'message': 'Заполните обязательные поля'}), 400
        
    try:
        from app.models import ContactRequest
        new_request = ContactRequest(
            contact_info=contact_info,
            category=category,
            message=message
        )
        db.session.add(new_request)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
