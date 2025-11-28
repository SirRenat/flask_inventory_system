import os
import uuid
from flask import current_app

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

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