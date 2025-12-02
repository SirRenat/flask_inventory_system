# routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, User
from app.utils import save_uploaded_files
from datetime import datetime, timedelta
import os
import uuid
from werkzeug.utils import secure_filename

main = Blueprint('main', __name__, template_folder='../templates')

@main.route('/')
def index():
    category_id = request.args.get('category_id')
    search_term = request.args.get('search', '').strip()
    
    # ТЕПЕРЬ ФИЛЬТРУЕМ ТОЛЬКО ОПУБЛИКОВАННЫЕ ТОВАРЫ
    query = Product.query.filter_by(status=Product.STATUS_PUBLISHED)
    
    # Фильтрация по категории
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Поиск по тексту
    if search_term:
        query = query.filter(
            Product.title.ilike(f'%{search_term}%') | 
            Product.description.ilike(f'%{search_term}%')
        )
    
    # Сортируем по дате создания (новые первыми)
    products = query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    
    return render_template('main.html', 
                         products=products, 
                         categories=categories,
                         search_term=search_term)
                         
@main.route('/dashboard')
@login_required
def dashboard():
    # Показываем все товары пользователя (включая неопубликованные)
    user_products = Product.query.filter_by(user_id=current_user.id).order_by(Product.created_at.desc()).all()
    
    # Обновляем статусы товаров при загрузке дашборда
    for product in user_products:
        if product.update_status():
            db.session.commit()
    
    return render_template('dashboard.html', products=user_products)

@main.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Проверяем, может ли пользователь видеть товар
    # 1. Опубликованные товары видны всем
    # 2. Неопубликованные товары видны только владельцу или администратору
    # 3. Товары "готов к публикации" видны только владельцу или администратору
    
    if product.status == Product.STATUS_PUBLISHED:
        # Опубликованные товары видны всем
        pass
    else:
        # Для неопубликованных товаров проверяем права
        if not current_user.is_authenticated:
            flash('Этот товар недоступен для просмотра', 'error')
            return redirect(url_for('main.index'))
        
        if current_user.id != product.user_id and current_user.role != 'admin':
            flash('Этот товар недоступен для просмотра', 'error')
            return redirect(url_for('main.index'))
    
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
            
            # НОВЫЕ ПОЛЯ
            quantity = request.form.get('quantity', 1)
            manufacturer = request.form.get('manufacturer')
            
            if not title or not price:
                flash('Название и цена обязательны для заполнения', 'error')
                return redirect(url_for('main.add_product'))
            
            # Обработка загруженных файлов
            uploaded_files = request.files.getlist('image_files')
            saved_images = []
            
            if uploaded_files and any(f.filename for f in uploaded_files):
                if len(uploaded_files) > 4:
                    flash('Можно загрузить не более 4 фотографий', 'error')
                    return redirect(url_for('main.add_product'))
                
                for file in uploaded_files:
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        saved_images.append(unique_filename)
            
            image_urls = request.form.get('image_urls', '').strip()
            if image_urls and not saved_images:
                url_list = [url.strip() for url in image_urls.split(',') if url.strip()]
                saved_images = url_list[:4]
            
            # Создаем новый товар с новыми полями
            new_product = Product(
                title=title,
                description=description,
                price=float(price),
                quantity=int(quantity),
                manufacturer=manufacturer,
                category_id=category_id if category_id else None,
                user_id=current_user.id,
                images=saved_images if saved_images else None,
                status=Product.STATUS_PUBLISHED
            )
            
            db.session.add(new_product)
            db.session.commit()
            
            flash('Товар успешно добавлен! Срок размещения - 30 дней', 'success')
            return redirect(url_for('main.dashboard'))
            
        except ValueError:
            flash('Некорректное значение цены или количества', 'error')
            return redirect(url_for('main.add_product'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении товара: {str(e)}', 'error')
            return redirect(url_for('main.add_product'))
    
    categories = Category.query.all()
    return render_template('add_product.html', categories=categories)

@main.route('/product/<int:product_id>/renew', methods=['POST'])
@login_required
def renew_product(product_id):
    """Продление публикации товара"""
    product = Product.query.get_or_404(product_id)
    
    # Проверяем права доступа
    if product.user_id != current_user.id:
        flash('У вас нет прав для продления этого товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    
    # Проверяем, что товар готов к публикации или снят
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
    """Снятие товара с публикации"""
    product = Product.query.get_or_404(product_id)
    
    # Проверяем права доступа
    if product.user_id != current_user.id:
        flash('У вас нет прав для снятия этого товара с публикации', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    
    # Проверяем, что товар опубликован
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
            # Обработка основных данных
            product.title = request.form.get('title')
            product.description = request.form.get('description')
            product.price = float(request.form.get('price'))
            
            # ОБНОВЛЯЕМ НОВЫЕ ПОЛЯ
            product.quantity = int(request.form.get('quantity', 1))
            product.manufacturer = request.form.get('manufacturer')
            
            product.category_id = request.form.get('category_id') if request.form.get('category_id') else None
            product.status = int(request.form.get('status'))
            
            # Обработка expires_at
            expires_at_str = request.form.get('expires_at')
            if expires_at_str:
                product.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M')
            
            # Обработка изображений (остается без изменений)
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
    return render_template('edit_product.html', product=product, categories=categories)

@main.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Проверяем права доступа
    if product.user_id != current_user.id and current_user.role != 'admin':
        flash('У вас нет прав для удаления этого товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    
    try:
        # Удаляем изображения товара из файловой системы
        if product.images:
            for image_filename in product.images:
                if isinstance(image_filename, str) and not image_filename.startswith('http'):
                    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        print(f"🗑️ Удалено изображение: {image_filename}")
        
        # Удаляем товар из базы данных
        db.session.delete(product)
        db.session.commit()
        
        flash('Товар успешно удален', 'success')
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка при удалении товара: {e}")
        flash('Ошибка при удалении товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))

@main.route('/test_upload', methods=['GET', 'POST'])
def test_upload():
    if request.method == 'POST':
        print("=" * 50)
        print("🔍 ТЕСТ ЗАГРУЗКИ - НАЧАЛО")
        
        # Пробуем получить файлы из разных полей
        uploaded_files = request.files.getlist('images')  # Старое поле
        image_files = request.files.getlist('image_files')  # Новое поле
        
        print(f"🔍 Получено файлов из поля 'images': {len(uploaded_files)}")
        print(f"🔍 Получено файлов из поля 'image_files': {len(image_files)}")
        
        # Используем новое поле
        files_to_process = image_files if image_files else uploaded_files
        
        # Проверяем каждый файл
        for i, file in enumerate(files_to_process):
            if file and file.filename:
                file.seek(0, 2)  # Переходим в конец файла
                file_size = file.tell()
                file.seek(0)  # Возвращаемся в начало
                print(f"🔍 Файл {i}: '{file.filename}', размер: {file_size} байт")
            else:
                print(f"🔍 Файл {i}: ПУСТОЙ или без имени")
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        print(f"🔍 Конфигурация UPLOAD_FOLDER: '{upload_folder}'")
        
        # Проверяем существование папки
        print(f"🔍 Папка существует: {os.path.exists(upload_folder)}")
        
        # Показываем что в папке ДО сохранения
        if os.path.exists(upload_folder):
            files_before = os.listdir(upload_folder)
            print(f"🔍 Файлов в папке ДО сохранения: {len(files_before)}")
            for f in files_before[:5]:  # Показываем только первые 5
                print(f"   - {f}")
        
        # Пробуем сохранить файлы
        saved_files = []
        for file in files_to_process:
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                file.save(file_path)
                saved_files.append(unique_filename)
        
        print(f"🔍 Сохранено файлов: {len(saved_files)}")
        
        # Показываем что в папке ПОСЛЕ сохранения
        if os.path.exists(upload_folder):
            files_after = os.listdir(upload_folder)
            print(f"🔍 Файлов в папке ПОСЛЕ сохранения: {len(files_after)}")
            new_files = set(files_after) - set(files_before)
            for f in new_files:
                full_path = os.path.join(upload_folder, f)
                print(f"   - {f} (существует: {os.path.exists(full_path)})")
        
        print("🔍 ТЕСТ ЗАГРУЗКИ - КОНЕЦ")
        print("=" * 50)
        
        return f'''
        <h2>Результат теста</h2>
        <p>Получено файлов: {len(files_to_process)}</p>
        <p>Сохранено файлов: {len(saved_files)}</p>
        <p>Проверьте консоль Python для подробной информации</p>
        <a href="/test_upload">Еще раз</a>
        '''
    
    return '''
    <h2>Тест загрузки файлов - УЛУЧШЕННАЯ ВЕРСИЯ</h2>
    <form method="POST" enctype="multipart/form-data">
        <h3>Тест нового поля (image_files):</h3>
        <input type="file" name="image_files" multiple>
        <h3>Тест старого поля (images):</h3>
        <input type="file" name="images" multiple>
        <br><br>
        <button type="submit">Тест загрузки</button>
    </form>
    '''

@main.route('/debug_products')
def debug_products():
    products = Product.query.all()
    result = []
    for product in products:
        images = product.images
        if isinstance(images, str):
            images = [img.strip() for img in images.split(',') if img.strip()]
        
        result.append({
            'id': product.id,
            'title': product.title,
            'images': images,
            'has_images': bool(images and len(images) > 0),
            'image_count': len(images) if images else 0,
            'category': product.category.name if product.category else 'No category'
        })
    return {'products': result}

@main.route('/check_uploads')
def check_uploads():
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    result = {
        'config_path': upload_folder,
        'folder_exists': os.path.exists(upload_folder),
        'files': []
    }
    
    if os.path.exists(upload_folder):
        files = os.listdir(upload_folder)
        result['file_count'] = len(files)
        
        for filename in files[:20]:  # Ограничиваем вывод
            full_path = os.path.join(upload_folder, filename)
            result['files'].append({
                'name': filename,
                'exists': os.path.exists(full_path),
                'size': os.path.getsize(full_path) if os.path.exists(full_path) else 0,
                'full_path': full_path
            })
    
    return result

@main.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    """Обслуживает загруженные файлы из папки uploads"""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    # Проверяем существование файла
    file_path = os.path.join(upload_folder, filename)
    if os.path.exists(file_path):
        return send_from_directory(upload_folder, filename)
    else:
        return "File not found", 404

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Обновление данных пользователя
        current_user.username = request.form.get('username')
        current_user.company_name = request.form.get('company_name')
        current_user.inn = request.form.get('inn')
        current_user.legal_address = request.form.get('legal_address')
        current_user.contact_person = request.form.get('contact_person')
        current_user.position = request.form.get('position')
        current_user.phone = request.form.get('phone')
        current_user.industry = request.form.get('industry')
        current_user.about = request.form.get('about')
        
        # Если указан новый пароль
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

@main.route('/admin/categories')
@login_required
def admin_categories():
    """Админка управления категориями"""
    categories = Category.query.all()
    parent_categories = Category.query.filter_by(parent_id=None).all()
    
    return render_template('admin_categories.html', 
                         categories=categories,
                         parent_categories=parent_categories)

@main.route('/admin/upload-categories', methods=['POST'])
@login_required
def upload_categories():
    """Загрузка категорий из JSON файла"""
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
        # Читаем и парсим JSON
        categories_data = json.load(file)
        
        # Очищаем старые категории
        Category.query.delete()
        
        # Создаем новые категории
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
    """Очистка всех категорий"""
    
    try:
        # Сначала обнуляем category_id у всех продуктов
        Product.query.update({Product.category_id: None})
        db.session.commit()
        
        # Затем удаляем категории
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
    """Обновление статусов просроченных товаров"""
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