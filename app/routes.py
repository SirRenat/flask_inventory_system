from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, User
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload

# Создаем Blueprint ДО определения маршрутов
main = Blueprint('main', __name__, template_folder='../templates')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@main.route('/')
def index():
    category_id = request.args.get('category_id')
    search_term = request.args.get('search', '').strip()
    
    query = Product.query.filter_by(status=Product.STATUS_PUBLISHED)
    
    # ← ИСПРАВЛЕНИЕ: приводим к int, если есть
    if category_id and category_id.isdigit():
        category_id = int(category_id)
        query = query.filter_by(category_id=category_id)
    
    if search_term:
        query = query.filter(
            Product.title.ilike(f'%{search_term}%') | 
            Product.description.ilike(f'%{search_term}%')
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
    
    expired_count = Product.query.filter(
        Product.user_id == current_user.id,
        Product.status == Product.STATUS_PUBLISHED,
        Product.expires_at <= datetime.utcnow()
    ).update({Product.status: Product.STATUS_READY_FOR_PUBLICATION})
    
    if expired_count > 0:
        db.session.commit()
    
    return render_template('dashboard.html', 
                         products=user_products,
                         now=datetime.utcnow())

@main.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.options(
        joinedload(Product.product_category),
        joinedload(Product.owner)
    ).get_or_404(product_id)
    
    if product.status == Product.STATUS_PUBLISHED:
        pass
    else:
        if not current_user.is_authenticated:
            flash('Этот товар недоступен для просмотра', 'error')
            return redirect(url_for('main.index'))
        
        if current_user.id != product.user_id and current_user.role != 'admin':
            flash('Этот товар недоступен для просмотра', 'error')
            return redirect(url_for('main.index'))

     # Проверяем, что товар можно показывать
    can_view = False
    if product.status == Product.STATUS_PUBLISHED:
        can_view = True
    elif current_user.is_authenticated and (current_user.id == product.user_id or current_user.role == 'admin'):
        can_view = True
    
    if not can_view:
        flash('Этот товар недоступен для просмотра', 'error')
        return redirect(url_for('main.index'))
    
    # ← УВЕЛИЧИВАЕМ СЧЁТЧИК ПРОСМОТРОВ
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
            category_id = request.form.get('category_id')
            quantity = request.form.get('quantity', 1)
            manufacturer = request.form.get('manufacturer')
            
            # ВАЛИДАЦИЯ: проверяем все обязательные поля
            if not title:
                flash('Название товара обязательно для заполнения', 'error')
                return redirect(url_for('main.add_product'))
            if not price:
                flash('Цена товара обязательна для заполнения', 'error')
                return redirect(url_for('main.add_product'))

            # Валидация category_id с преобразованием в int
            category_id_str = request.form.get('category_id', '').strip()
            if not category_id_str:
                flash('Категория товара обязательна для выбора', 'error')
                return redirect(url_for('main.add_product'))

            try:
                category_id_int = int(category_id_str)
            except (ValueError, TypeError):
                flash('Некорректный выбор категории', 'error')
                return redirect(url_for('main.add_product'))

            category = Category.query.get(category_id_int)
            if not category:
                flash('Выбранная категория не существует', 'error')
                return redirect(url_for('main.add_product'))
            
            uploaded_files = request.files.getlist('image_files')
            saved_images = []
            
            if uploaded_files and any(f.filename for f in uploaded_files):
                if len(uploaded_files) > 4:
                    flash('Можно загрузить не более 4 фотографий', 'error')
                    return redirect(url_for('main.add_product'))
                
                for file in uploaded_files:
                    if file and file.filename:
                        if not allowed_file(file.filename):
                            flash('Недопустимый тип файла. Разрешены: png, jpg, jpeg, gif, webp', 'error')
                            return redirect(url_for('main.add_product'))
                        
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        saved_images.append(unique_filename)
            
            image_urls = request.form.get('image_urls', '').strip()
            if image_urls and not saved_images:
                url_list = [url.strip() for url in image_urls.split(',') if url.strip()]
                saved_images = url_list[:4]
            
            new_product = Product(
                title=title,
                description=description,
                price=float(price),
                quantity=int(quantity),
                manufacturer=manufacturer,
                category_id=category_id_int,
                user_id=current_user.id,
                images=saved_images if saved_images else None,
                status=Product.STATUS_PUBLISHED,
                vat_included=request.form.get('vat_included') == 'on' 
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
    
    return render_template('add_product.html', categories=categories)

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
            
            product.title = title
            product.description = description
            product.price = float(price)
            product.quantity = int(request.form.get('quantity', 1))
            product.manufacturer = request.form.get('manufacturer')
            product.category_id = int(category_id)
            product.status = int(request.form.get('status'))
            product.vat_included = request.form.get('vat_included') == 'on' 
            
            expires_at_str = request.form.get('expires_at')
            if expires_at_str:
                product.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M')
            
            current_images = product.images if product.images else []
            if isinstance(current_images, str):
                current_images = [img.strip() for img in current_images.split(',') if img.strip()]
            
            removed_images = request.form.get('removed_images', '')
            if removed_images:
                removed_list = [img.strip() for img in removed_images.split(',') if img.strip()]
                current_images = [img for img in current_images if img not in removed_list]
            
            uploaded_files = request.files.getlist('image_files')
            new_images = []
            
            if uploaded_files and any(f.filename for f in uploaded_files):
                if len(uploaded_files) > 4:
                    flash('Можно загрузить не более 4 новых фотографий', 'error')
                    return redirect(url_for('main.edit_product', product_id=product_id))
                
                for file in uploaded_files:
                    if file and file.filename:
                        if not allowed_file(file.filename):
                            flash('Недопустимый тип файла. Разрешены: png, jpg, jpeg, gif, webp', 'error')
                            return redirect(url_for('main.edit_product', product_id=product_id))
                        
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        new_images.append(unique_filename)
            
            if new_images:
                current_images.extend(new_images)
            
            product.images = current_images[:8]
            
            if removed_images:
                for image_filename in removed_list:
                    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename)
                    if os.path.exists(image_path):
                        os.remove(image_path)
            
            db.session.commit()
            flash('Товар успешно обновлен', 'success')
            return redirect(url_for('main.product_detail', product_id=product_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении товара: {str(e)}', 'error')
    
    categories = Category.query.all()
    if not categories:
        flash('Нет доступных категорий', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('edit_product.html', product=product, categories=categories)

@main.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if product.user_id != current_user.id and current_user.role != 'admin':
        flash('У вас нет прав для удаления этого товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    
    try:
        if product.images:
            for image_filename in product.images:
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
        flash('Ошибка при удаления товара', 'error')
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
                new_category = Category(
                    name=name,
                    description=description,
                    parent_id=parent_id if parent_id else None
                )
                db.session.add(new_category)
                db.session.commit()
                flash(f'Категория "{name}" успешно добавлена', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении категории: {str(e)}', 'error')
        
        elif action == 'edit_category':
            category_id = request.form.get('category_id')
            flash('Редактирование категорий пока недоступно', 'info')
        
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
                    db.session.delete(cat)
                    deleted_count += 1
            
            if deleted_count > 0:
                db.session.commit()
                flash(f'Удалено {deleted_count} пустых категорий', 'success')
            else:
                flash('Пустых категорий не найдено', 'info')
        
        return redirect(url_for('main.admin_categories'))
    
    categories = Category.query.all()
    parent_categories = Category.query.filter_by(parent_id=None).all()
    total_products = Product.query.count()
    
    return render_template('admin_categories.html', 
                         categories=categories,
                         parent_categories=parent_categories,
                         total_products=total_products)

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