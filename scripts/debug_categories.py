import os
import json
import sys

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Category

def debug_categories():
    app = create_app()
    
    with app.app_context():
        print("🔍 ДИАГНОСТИКА КАТЕГОРИЙ")
        print("=" * 50)
        
        # Проверяем текущую директорию
        current_dir = os.getcwd()
        print(f"📁 Текущая директория: {current_dir}")
        
        # Проверяем файлы в директории
        files = os.listdir('.')
        print(f"📋 Файлы в директории: {files}")
        
        # Проверяем существование JSON файла
        json_path = 'categories_structure.json'
        if os.path.exists(json_path):
            print(f"✅ Файл {json_path} найден")
            
            # Пробуем прочитать файл
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ JSON файл успешно прочитан")
                print(f"📊 Количество родительских категорий в JSON: {len(data)}")
                
                # Показываем названия категорий из JSON
                print("📁 Категории в JSON файле:")
                for category in data:
                    print(f"  - {category['name']} ({len(category.get('children', []))} подкатегорий)")
                    
            except Exception as e:
                print(f"❌ Ошибка чтения JSON: {e}")
        else:
            print(f"❌ Файл {json_path} не найден!")
            
        # Проверяем текущие категории в базе
        print("\n📊 Текущие категории в базе:")
        categories = Category.query.all()
        print(f"📈 Всего категорий в базе: {len(categories)}")
        
        for cat in categories:
            parent_info = " (родительская)" if cat.parent_id is None else f" (дочерняя, родитель: {cat.parent_id})"
            print(f"  - {cat.name}{parent_info}")
        
        print("=" * 50)

if __name__ == '__main__':
    debug_categories()