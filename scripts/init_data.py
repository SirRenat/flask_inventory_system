# init_data.py
from app import create_app, db
from app.models import User, Category
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    print("📦 ИНИЦИАЛИЗАЦИЯ ДАННЫХ")
    print("=" * 50)
    
    # 1. Администратор
    admin_email = 'admin@example.com'
    admin_password = 'admin123'
    
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            email=admin_email,
            company_name='Администратор системы',
            password_hash=generate_password_hash(admin_password),
            inn='0000000000',
            legal_address='г. Москва',
            contact_person='Администратор',
            position='Администратор',
            phone='+79999999999',
            industry='IT',
            username='admin',
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Администратор создан")
        print(f"   Email: {admin_email}")
        print(f"   Пароль: {admin_password}")
    else:
        print(f"📊 Администратор уже существует")
    
    # 2. Категории
    categories = [
        'Электроника',
        'Оборудование', 
        'Мебель',
        'Стройматериалы',
        'Канцелярия',
        'Химия и моющие средства',
        'Инструменты',
        'Офисная техника'
    ]
    
    created = 0
    for name in categories:
        category = Category.query.filter_by(name=name).first()
        if not category:
            category = Category(name=name)
            db.session.add(category)
            created += 1
    
    if created > 0:
        db.session.commit()
        print(f"✅ Создано категорий: {created}")
    else:
        print(f"📊 Все категории уже существуют")
    
    # 3. Итог
    print("\n📈 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"  👤 Пользователей: {User.query.count()}")
    print(f"  📁 Категорий: {Category.query.count()}")
    
    print("\n🎉 Данные инициализированы!")
    print("=" * 50)