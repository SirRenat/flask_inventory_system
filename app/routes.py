from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category
from app.utils import save_uploaded_files
from datetime import datetime, timedelta
import os

main = Blueprint('main', __name__, template_folder='../templates')

@main.route('/')
def index():
    category_id = request.args.get('category_id')
    search_term = request.args.get('search', '').strip()
    
    # ВРЕМЕННО: показываем все товары до завершения миграции
    query = Product.query
    # ПОТОМ ВЕРНУТЬ: query = Product.query.filter_by(status=Product.STATUS_PUBLISHED)
    
    # Фильтрация по категории
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Поиск по тексту
    if search_term:
        query = query.filter(
            Product.title.ilike(f'%{search_term}%') | 
            Product.description.ilike(f'%{search_term}%')
        )
    
    products = query.all()
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
    if not product.can_be_viewed_by_public and (not current_user.is_authenticated or current_user.id != product.user_id):
        flash('Этот товар недоступен для просмотра', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('product_detail.html', product=product)

@main.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = float(request.form['price'])
        category_id = request.form.get('category_id')
        
        uploaded_files = request.files.getlist('images')
        if len(uploaded_files) > 4:
            flash('Можно загрузить не более 4 фотографий', 'error')
            return redirect(url_for('main.add_product'))
        
        saved_images = save_uploaded_files(uploaded_files)
        
        new_product = Product(
            title=title,
            description=description,
            price=price,
            user_id=current_user.id,
            category_id=category_id if category_id else None,
            images=saved_images,
            status=Product.STATUS_PUBLISHED,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        flash('Товар успешно добавлен! Срок размещения - 30 дней', 'success')
        return redirect(url_for('main.dashboard'))
    
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
    
    # Проверка прав доступа
    if product.user_id != current_user.id and not current_user.is_admin():
        flash('У вас нет прав для редактирования этого товара', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    
    if request.method == 'POST':
        try:
            # Обработка данных формы
            product.title = request.form.get('title')
            product.description = request.form.get('description')
            product.price = float(request.form.get('price'))
            product.category_id = request.form.get('category_id') if request.form.get('category_id') else None
            product.status = int(request.form.get('status'))
            
            # Обработка expires_at
            expires_at_str = request.form.get('expires_at')
            if expires_at_str:
                product.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M')
            else:
                product.expires_at = None
                
            product.is_active = 'is_active' in request.form
            
            # Обработка изображений
            images_input = request.form.get('images', '').strip()
            if images_input:
                # Если введены новые URL изображений
                product.images = images_input
            # Если поле images пустое - сохраняем текущие изображения
            # Не перезаписываем product.images если поле пустое
            
            # Обработка загруженных файлов
            uploaded_files = request.files.getlist('image_files')
            if uploaded_files and any(f.filename for f in uploaded_files):
                saved_images = save_uploaded_files(uploaded_files)
                if saved_images:
                    # Добавляем новые изображения к существующим
                    current_images = product.images if product.images else []
                    if isinstance(current_images, str):
                        # Если images хранится как строка, преобразуем в список
                        current_images = [img.strip() for img in current_images.split(',') if img.strip()]
                    product.images = current_images + saved_images
            
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
        
        uploaded_files = request.files.getlist('images')
        print(f"🔍 Получено файлов из запроса: {len(uploaded_files)}")
        
        # Проверяем каждый файл
        for i, file in enumerate(uploaded_files):
            if file and file.filename:
                # Читаем содержимое файла
                file_data = file.read()
                file.seek(0)  # Возвращаем указатель
                print(f"🔍 Файл {i}: '{file.filename}', размер: {len(file_data)} байт")
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
            for f in files_before:
                print(f"   - {f}")
        else:
            print(f"🔍 Папка '{upload_folder}' не существует!")
        
        # Пробуем сохранить файлы
        saved_files = save_uploaded_files(uploaded_files)
        print(f"🔍 Функция save_uploaded_files вернула: {saved_files}")
        
        # Показываем что в папке ПОСЛЕ сохранения
        if os.path.exists(upload_folder):
            files_after = os.listdir(upload_folder)
            print(f"🔍 Файлов в папке ПОСЛЕ сохранения: {len(files_after)}")
            for f in files_after:
                full_path = os.path.join(upload_folder, f)
                print(f"   - {f} (существует: {os.path.exists(full_path)})")
        else:
            print(f"🔍 Папка '{upload_folder}' все еще не существует!")
        
        print("🔍 ТЕСТ ЗАГРУЗКИ - КОНЕЦ")
        print("=" * 50)
        
        return f'''
        <h2>Результат теста</h2>
        <p>Получено файлов: {len(uploaded_files)}</p>
        <p>Сохранено файлов: {saved_files}</p>
        <p>Проверьте консоль Python для подробной информации</p>
        <a href="/test_upload">Еще раз</a>
        '''
    
    return '''
    <h2>Тест загрузки файлов - УЛУЧШЕННАЯ ВЕРСИЯ</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="images" multiple>
        <button type="submit">Тест загрузки</button>
    </form>
    '''

@main.route('/debug_products')
def debug_products():
    products = Product.query.all()
    result = []
    for product in products:
        result.append({
            'id': product.id,
            'title': product.title,
            'images': product.images,
            'has_images': bool(product.images and len(product.images) > 0),
            'image_count': len(product.images) if product.images else 0,
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
        
        for filename in files:
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
    print(f"🔍 Запрос файла: {filename}")
    print(f"📁 Папка: {upload_folder}")
    
    # Проверяем существование файла
    file_path = os.path.join(upload_folder, filename)
    if os.path.exists(file_path):
        print(f"✅ Файл найден: {filename} ({os.path.getsize(file_path)} байт)")
        return send_from_directory(upload_folder, filename)
    else:
        print(f"❌ Файл не найден: {filename}")
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
    from app.models import Category
    
    categories = Category.query.all()
    parent_categories = Category.query.filter_by(parent_id=None).all()
    
    return render_template('admin_categories.html', 
                         categories=categories,
                         parent_categories=parent_categories)

@main.route('/admin/upload-categories', methods=['POST'])
@login_required
def upload_categories():
    """Загрузка категорий из JSON файла"""
    from app.models import Category
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
    from app.models import Category
    
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