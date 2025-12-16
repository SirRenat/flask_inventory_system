import os
import uuid
from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename
import uuid

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def _deserialize_images(images_field):
    """Преобразует значение поля images (строка или список) в список имён файлов."""
    if not images_field:
        return []
    if isinstance(images_field, list):
        return [img for img in images_field if img]
    if isinstance(images_field, str):
        return [img.strip() for img in images_field.split(',') if img.strip()]
    return []

def _serialize_images(images_list):
    """Преобразует список имён файлов в строку для хранения в БД."""
    return ','.join(images_list) if images_list else ''

def process_category_image(file, category_id=None):
    """Обрабатывает и сохраняет изображение категории с обрезкой"""
    if file and allowed_file(file.filename):
        try:
            # Открываем изображение
            img = Image.open(file)
            
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Определяем размеры
            width, height = img.size
            
            # Если изображение очень большое, уменьшаем перед обрезкой
            max_dimension = 800
            if width > max_dimension or height > max_dimension:
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                width, height = img.size
            
            # Обрезаем до квадрата (центрированно)
            target_size = min(width, height)
            
            # Координаты для обрезки
            left = (width - target_size) // 2
            top = (height - target_size) // 2
            right = left + target_size
            bottom = top + target_size
            
            img_cropped = img.crop((left, top, right, bottom))
            
            # Создаем несколько размеров
            sizes = {
                'original': (target_size, target_size),  # Оригинальный квадрат
                'large': (200, 200),  # Для десктопа
                'medium': (150, 150), # Для планшетов
                'small': (100, 100),  # Для мобильных
                'thumbnail': (80, 80)  # Для превью (как в блоке категорий)
            }
            
            # Генерируем уникальное имя файла
            unique_filename = str(uuid.uuid4())
            original_filename = secure_filename(file.filename)
            ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
            
            base_filename = f"{unique_filename}_{original_filename.split('.')[0]}"
            
            # Сохраняем все размеры
            saved_filenames = {}
            
            for size_name, (size_width, size_height) in sizes.items():
                # Ресайзим
                img_resized = img_cropped.resize((size_width, size_height), Image.Resampling.LANCZOS)
                
                # Формируем имя файла
                if size_name == 'thumbnail':
                    filename = f"{base_filename}.{ext}"  # Основное имя для thumbnail
                else:
                    filename = f"{base_filename}_{size_name}.{ext}"
                
                # Путь для сохранения
                upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories')
                os.makedirs(upload_folder, exist_ok=True)
                
                filepath = os.path.join(upload_folder, filename)
                
                # Сохраняем с оптимизацией
                if ext in ['jpg', 'jpeg']:
                    img_resized.save(filepath, 'JPEG', quality=85, optimize=True)
                elif ext == 'png':
                    img_resized.save(filepath, 'PNG', optimize=True)
                else:
                    img_resized.save(filepath)
                
                saved_filenames[size_name] = filename
            
            # Возвращаем имя thumbnail-файла (основное)
            return saved_filenames['thumbnail'], None
            
        except Exception as e:
            print(f"Error processing category image: {e}")
            return None, str(e)
    
    return None, "Invalid file format"

def save_uploaded_files(files):
    saved_files = []
    print(f"  🔍 save_uploaded_files: начало, файлов: {len(files)}")
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    print(f"  🔍 Абсолютный путь для сохранения: '{upload_folder}'")
    print(f"  🔍 Текущая рабочая папка: '{os.getcwd()}'")
    
    # Создаем папку с проверкой
    try:
        os.makedirs(upload_folder, exist_ok=True)
        print(f"  ✅ Папка создана/проверена: {upload_folder}")
        print(f"  ✅ Папка существует: {os.path.exists(upload_folder)}")
    except Exception as e:
        print(f"  ❌ Ошибка создания папки: {e}")
        return []
    
    for i, file in enumerate(files):
        print(f"  🔍 Обработка файла {i}:")
        
        if file and file.filename:
            print(f"    📄 Имя файла: '{file.filename}'")
            
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                file_path = os.path.join(upload_folder, filename)
                
                print(f"    📁 Сохраняем как: '{filename}'")
                print(f"    📁 Полный путь: '{file_path}'")
                
                try:
                    file.save(file_path)
                    
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        print(f"    ✅ Файл успешно сохранен! Размер: {file_size} байт")
                        saved_files.append(filename)
                        
                        # Проверим где реально сохранился файл
                        actual_path = os.path.abspath(file_path)
                        print(f"    📍 Реальный путь файла: '{actual_path}'")
                    else:
                        print(f"    ❌ Файл не сохранился!")
                        
                except Exception as e:
                    print(f"    ❌ Ошибка сохранения файла: {e}")
                    
            else:
                print(f"    ❌ Тип файла не разрешен: {file.filename}")
        else:
            print(f"    ❌ Файл {i} пустой или без имени")
    
    print(f"  🔍 save_uploaded_files: конец, сохранено: {saved_files}")
    return saved_files

def get_category_choices(parent_id=None, level=0):
    """
    Рекурсивно получает категории для выпадающего списка с учетом иерархии.
    Возвращает список словарей: {'id', 'name', 'level', 'display_name'}
    """
    from app.models import Category
    
    choices = []
    # Сортировка по алфавиту
    cats = Category.query.filter_by(parent_id=parent_id).order_by(Category.name).all()
    for cat in cats:
        choices.append({
            'id': cat.id,
            'name': cat.name,
            'level': level,
            'display_name': ('— ' * level) + cat.name
        })
        choices.extend(get_category_choices(cat.id, level + 1))
    return choices