from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category
from app.utils import save_uploaded_files

import os
main = Blueprint('main', __name__, template_folder='../templates')

# ДОБАВЬТЕ ЭТОТ ПРОСТОЙ ТЕСТОВЫЙ МАРШРУТ
@main.route('/simple_test')
def simple_test():
    return "SIMPLE TEST WORKS!"
@main.route('/health')
def health():
    return "✅ Приложение работает!"

@main.route('/create-tables')
def create_tables():
    try:
        from app import db
        db.create_all()
        return "✅ Таблицы созданы!"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

@main.route('/')
def index():
    category_id = request.args.get('category_id')
    if category_id:
        # ИСПРАВЛЕНО: убран фильтр по status
        products = Product.query.filter_by(category_id=category_id).all()
    else:
        # ИСПРАВЛЕНО: убран фильтр по status
        products = Product.query.all()
    
    categories = Category.query.all()
    return render_template('main.html', products=products, categories=categories)

@main.route('/dashboard')
@login_required
def dashboard():
    user_products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', products=user_products)

@main.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
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
            images=saved_images
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        flash('Товар успешно добавлен!', 'success')
        return redirect(url_for('main.dashboard'))
    
    categories = Category.query.all()
    return render_template('add_product.html', categories=categories)

# Тестовый маршрут для отладки загрузки файлов
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
        
        # Проверяем конфигурацию
        from flask import current_app
        upload_folder = current_app.config['UPLOAD_FOLDER']
        print(f"🔍 Конфигурация UPLOAD_FOLDER: '{upload_folder}'")
        
        # Проверяем существование папки
        import os
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
    import os
    from flask import current_app
    
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
