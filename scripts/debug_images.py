import os
from app import create_app
from app.models import Product

def debug_image_issue():
    app = create_app()
    
    with app.app_context():
        print("🔍 ДИАГНОСТИКА ПРОБЛЕМЫ С КАРТИНКАМИ")
        print("=" * 50)
        
        # Проверяем папку uploads
        upload_folder = app.config['UPLOAD_FOLDER']
        print(f"📁 UPLOAD_FOLDER: {upload_folder}")
        print(f"📁 Папка существует: {os.path.exists(upload_folder)}")
        
        if os.path.exists(upload_folder):
            files = os.listdir(upload_folder)
            print(f"📊 Файлов в папке: {len(files)}")
            for file in files[:10]:  # Показать первые 10 файлов
                file_path = os.path.join(upload_folder, file)
                print(f"   - {file} (размер: {os.path.getsize(file_path)} байт)")
        
        # Проверяем товары в базе
        products = Product.query.all()
        print(f"\n📦 Товаров в базе: {len(products)}")
        
        for product in products:
            print(f"\n🎯 Товар: {product.title} (ID: {product.id})")
            print(f"   Изображения в БД: {product.images}")
            
            if product.images:
                for img_name in product.images:
                    img_path = os.path.join(upload_folder, img_name)
                    print(f"   📷 {img_name} -> существует: {os.path.exists(img_path)}")
                    
                    # Проверяем URL
                    img_url = f"/static/uploads/{img_name}"
                    print(f"   🔗 URL: {img_url}")
            else:
                print("   ❌ Нет изображений в БД")

if __name__ == "__main__":
    debug_image_issue()