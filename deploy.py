import os
import subprocess
import shutil
from datetime import datetime

def safe_deploy():
    """Безопасный деплой с сохранением данных"""
    
    print("🚀 БЕЗОПАСНЫЙ ДЕПЛОЙ")
    print("=" * 40)
    
    # 1. Бэкап текущей БД
    if os.path.exists('instance/app.db'):
        backup_name = f"backup_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2('instance/app.db', backup_name)
        print(f"✅ Бэкап БД: {backup_name}")
    
    # 2. Остановите приложение (если запущено)
    print("⏸️ Остановка приложения...")
    # subprocess.run(['sudo', 'systemctl', 'stop', 'your_app_service'])
    
    # 3. Деплой нового кода
    print("📦 Деплой нового кода...")
    # subprocess.run(['git', 'pull'])
    # subprocess.run(['pip', 'install', '-r', 'requirements.txt'])
    
    # 4. Запустите миграцию если нужно
    if os.path.exists('old_production.db'):
        print("🔄 Запуск миграции...")
        subprocess.run(['python', 'migrate_production.py'])
    
    # 5. Запустите приложение
    print("▶️ Запуск приложения...")
    # subprocess.run(['sudo', 'systemctl', 'start', 'your_app_service'])
    
    print("✅ Деплой завершен!")

if __name__ == "__main__":
    safe_deploy()