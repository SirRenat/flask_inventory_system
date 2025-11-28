from app import create_app, db
from app.models import User, Category, Product
import json
from werkzeug.security import generate_password_hash
from flask import render_template

# Сначала создаем приложение
app = create_app()
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Добавь эту строку
app.jinja_env.auto_reload = True

# Затем все остальное в контексте приложения
with app.app_context():
    # ДОБАВЬТЕ ЭТОТ КОД ДЛЯ ПРОВЕРКИ
    import os
    print("=" * 50)
    print("🔍 ДИАГНОСТИКА ПУТЕЙ:")
    print(f"Текущая рабочая папка: {os.getcwd()}")
    print(f"Папка проекта: {os.path.dirname(os.path.abspath(__file__))}")

    # Проверим конфигурацию
    upload_folder = app.config['UPLOAD_FOLDER']
    print(f"UPLOAD_FOLDER из конфига: {upload_folder}")
    print(f"Папка существует: {os.path.exists(upload_folder)}")
    
    # Создаем папку принудительно
    os.makedirs(upload_folder, exist_ok=True)
    print(f"Папка создана/проверена: {upload_folder}")
    
    # Покажем что в папке
    if os.path.exists(upload_folder):
        files = os.listdir(upload_folder)
        print(f"Файлов в папке: {len(files)}")
        for f in files[:5]:  # первые 5 файлов
            print(f"  - {f}")
    print("=" * 50)

def create_default_categories():
    """Создает готовую структуру категорий для неликвидов из JSON файла"""
    try:
        with open('categories_structure.json', 'r', encoding='utf-8') as f:
            categories_structure = json.load(f)
    except FileNotFoundError:
        print("❌ Файл categories_structure.json не найден")
        # Создаем базовые категории вручную
        categories_structure = [
            {
                "name": "Электроника",
                "description": "Электронные устройства и компоненты",
                "children": [
                    {"name": "Смартфоны", "description": "Мобильные телефоны"},
                    {"name": "Ноутбуки", "description": "Портативные компьютеры"},
                    {"name": "Компьютеры", "description": "Стационарные ПК и комплектующие"}
                ]
            },
            {
                "name": "Одежда", 
                "description": "Одежда и аксессуары",
                "children": [
                    {"name": "Мужская одежда", "description": ""},
                    {"name": "Женская одежда", "description": ""},
                    {"name": "Детская одежда", "description": ""}
                ]
            }
        ]
    
    def create_categories(parent_id=None, categories_list=None):
        for category_data in categories_list:
            # Проверяем, существует ли уже категория с таким именем
            existing_category = Category.query.filter_by(name=category_data['name'], parent_id=parent_id).first()
            if not existing_category:
                category = Category(
                    name=category_data['name'],
                    description=category_data.get('description', ''),
                    parent_id=parent_id
                )
                db.session.add(category)
                db.session.flush()  # Получаем ID созданной категории
                print(f"✅ Создана категория: {category_data['name']}")
                
                # Рекурсивно создаем дочерние категории
                if 'children' in category_data:
                    create_categories(category.id, category_data['children'])
    
    if Category.query.count() == 0:
        create_categories(None, categories_structure)
        db.session.commit()
        print('✅ Структура категорий создана')
    else:
        print('ℹ️ Категории уже существуют в базе данных')

# ROUTES - теперь app определена

@app.route('/')
def index():
    import os
    with open('templates/main.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/raw')
def raw():
    response = render_template('main.html')
    return f"""
    <h1>RAW RESPONSE</h1>
    <pre>{response[:1000]}</pre>
    """

@app.route('/check_content')
def check_content():
    with open('templates/main.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_old_css = 'static/css/style.css' in content
    return f"""
    <h1>Проверка main.html</h1>
    <p>Содержит старый CSS: <b>{has_old_css}</b></p>
    <p>Размер: {len(content)} символов</p>
    <pre>{content[:500]}</pre>
    """

@app.route('/simple')
def simple():
    import os
    with open('templates/test_simple.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/nelikvidy')
def nelikvidy_interface():
    try:
        products = Product.query.filter_by(active=True).order_by(Product.created_date.desc()).limit(10).all()
        return render_template('main.html', products=products)
    except Exception as e:
        print(f"Ошибка загрузки товаров: {e}")
        return render_template('main.html', products=None)

@app.route('/direct')
def direct():
    import os
    with open('templates/main.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/debug')
def debug():
    return f"""
    <pre>
    Папка шаблонов: {app.template_folder}
    Рабочая папка: {os.getcwd()}
    Существует templates: {os.path.exists('templates')}
    Список файлов в templates: {os.listdir('templates') if os.path.exists('templates') else 'НЕТ'}
    </pre>
    """

def setup_database():
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        
        # Создаем структуру категорий если её нет
        create_default_categories()
        
        # Создаем первого администратора если его нет
        admin_email = 'admin@example.com'
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            hashed_password = generate_password_hash('admin123')
            admin_user = User(
                company_name='Администратор системы',
                email=admin_email,
                password_hash=hashed_password,
                phone='+7 (999) 123-45-67',
                inn='1234567890',
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print('✅ Создан администратор: admin@example.com / admin123')
        
        print("✅ База данных готова к работе")

# Вызываем setup при запуске
setup_database()

if __name__ == '__main__':
    app.run(debug=True, port=5000)  