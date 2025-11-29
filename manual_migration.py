from app import create_app, db
from app.models import User, Product, Category

app = create_app()

with app.app_context():
    # Создаем таблицы с новой структурой
    db.create_all()
    print("✅ Таблицы созданы с новой структурой")
    
    # Создаем администратора
    admin_email = 'admin@example.com'
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            email=admin_email,
            company_name='Администратор системы',
            inn='0000000000',
            legal_address='г. Москва',
            contact_person='Администратор',
            position='Системный администратор',
            phone='+79990000000',
            industry='it',
            username='admin',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Администратор создан")
    
    print("🎉 Миграция завершена успешно!")