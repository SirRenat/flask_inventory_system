import json
import os
import sys

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Category

def load_categories():
    app = create_app()
    
    with app.app_context():
        try:
            # Загружаем данные из JSON файла
            with open('categories_structure.json', 'r', encoding='utf-8') as f:
                categories_data = json.load(f)
            
            print("📂 Загружаем структуру категорий из JSON файла...")
            
            # УДАЛЯЕМ СТАРЫЕ КАТЕГОРИИ (если нужно)
            print("🔄 Очищаем старые категории...")
            Category.query.delete()
            db.session.commit()
            
            # Счетчики
            parent_count = 0
            child_count = 0
            
            # Обрабатываем каждую родительскую категорию
            for parent_data in categories_data:
                # Создаем родительскую категорию
                parent_category = Category(
                    name=parent_data['name'],
                    description=parent_data.get('description', '')
                )
                db.session.add(parent_category)
                db.session.flush()  # Получаем ID
                parent_count += 1
                print(f"✅ Родительская категория: {parent_data['name']}")
                
                # Создаем дочерние категории
                for child_data in parent_data.get('children', []):
                    child_category = Category(
                        name=child_data['name'],
                        description=child_data.get('description', ''),
                        parent_id=parent_category.id
                    )
                    db.session.add(child_category)
                    child_count += 1
                    print(f"   ↳ Дочерняя категория: {child_data['name']}")
            
            # Сохраняем в базу
            db.session.commit()
            
            print("\n🎉 Категории успешно загружены!")
            print(f"📊 Статистика:")
            print(f"   Родительских категорий: {parent_count}")
            print(f"   Дочерних категорий: {child_count}")
            print(f"   Всего категорий: {parent_count + child_count}")
            
            # Показываем полную структуру
            print("\n📁 Структура категорий:")
            parent_categories = Category.query.filter_by(parent_id=None).all()
            for parent in parent_categories:
                print(f"├── {parent.name}")
                children = Category.query.filter_by(parent_id=parent.id).all()
                for child in children:
                    print(f"│   └── {child.name}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки категорий: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == '__main__':
    load_categories()