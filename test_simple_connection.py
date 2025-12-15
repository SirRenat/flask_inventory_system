import socket
import subprocess
import platform
import sys
import time

def network_comprehensive_diagnosis():
    """Полная диагностика сетевых проблем"""
    
    print("=" * 70)
    print("ПОЛНАЯ ДИАГНОСТИКА СЕТЕВЫХ ПРОБЛЕМ")
    print("=" * 70)
    
    target_server = 'mail.asauda.ru'
    
    # 1. Проверка базовых сетевых настроек
    print("\n1. БАЗОВЫЕ СЕТЕВЫЕ НАСТРОЙКИ:")
    
    # Проверка DNS
    print("   Проверка DNS...")
    try:
        ip_list = []
        for info in socket.getaddrinfo(target_server, 0, 0, 0, 0):
            ip_list.append(info[4][0])
        unique_ips = list(set(ip_list))
        print(f"   ✅ DNS разрешен: {target_server} -> {', '.join(unique_ips)}")
    except Exception as e:
        print(f"   ❌ Ошибка DNS: {e}")
    
    # Проверка доступности интернета
    print("   Проверка интернет-соединения...")
    test_sites = [
        ("Google DNS", "8.8.8.8", 53),
        ("Google", "google.com", 80),
        ("Yandex", "ya.ru", 80)
    ]
    
    for name, host, port in test_sites:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            if host.replace('.', '').isdigit():
                result = sock.connect_ex((host, port))
            else:
                # Для доменов получаем IP
                ip = socket.gethostbyname(host)
                result = sock.connect_ex((ip, port))
            
            if result == 0:
                print(f"   ✅ {name} доступен")
            else:
                print(f"   ❌ {name} недоступен (код: {result})")
        except Exception as e:
            print(f"   ❌ {name}: {str(e)[:50]}")
        finally:
            sock.close()
    
    # 2. Подробная проверка целевого сервера
    print(f"\n2. ПОДРОБНАЯ ПРОВЕРКА {target_server}:")
    
    # Получаем все IP адреса сервера
    try:
        print("   Поиск всех IP адресов сервера...")
        for res in socket.getaddrinfo(target_server, None):
            af, socktype, proto, canonname, sa = res
            print(f"   Найден адрес: {sa[0]} (тип: {af})")
    except Exception as e:
        print(f"   Ошибка поиска адресов: {e}")
    
    # 3. Проверка через разные методы
    print("\n3. ПРОВЕРКА РАЗНЫМИ МЕТОДАМИ:")
    
    # Метод 1: Raw socket с разными таймаутами
    print("   Метод 1: Raw socket подключения...")
    for port in [465, 587, 25, 80, 443]:
        for timeout in [2, 5, 10]:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                start = time.time()
                result = sock.connect_ex((target_server, port))
                elapsed = time.time() - start
                
                if result == 0:
                    print(f"     ✅ Порт {port}: ОТКРЫТ ({elapsed:.2f} сек)")
                    sock.close()
                    break
                else:
                    if timeout == 10:  # Показываем только для максимального таймаута
                        print(f"     ❌ Порт {port}: ошибка {result}")
            except socket.timeout:
                if timeout == 10:
                    print(f"     ⏱ Порт {port}: ТАЙМАУТ ({timeout} сек)")
            except Exception as e:
                if timeout == 10:
                    print(f"     ❌ Порт {port}: {str(e)[:50]}")
            finally:
                try:
                    sock.close()
                except:
                    pass
    
    # 4. Проверка системных сетевых настроек
    print("\n4. СИСТЕМНЫЕ СЕТЕВЫЕ НАСТРОЙКИ:")
    
    if platform.system() == "Windows":
        print("   Проверка Windows сетевых настроек...")
        
        # Проверка прокси
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
            
            proxy_enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
            if proxy_enable:
                proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0]
                print(f"   ⚠ Включен прокси-сервер: {proxy_server}")
            else:
                print("   ✅ Прокси-сервер отключен")
                
            winreg.CloseKey(key)
        except Exception as e:
            print(f"   Ошибка проверки реестра: {e}")
    
    # 5. Проверка через системные утилиты
    print("\n5. ПРОВЕРКА СИСТЕМНЫМИ УТИЛИТАМИ:")
    
    commands = [
        ("Ping", ["ping", "-n", "3", target_server]),
        ("Route", ["route", "print"]),
        ("IP Config", ["ipconfig", "/all"]),
    ]
    
    for name, cmd in commands:
        print(f"   {name}:")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            # Выводим только первые 5 строк для ping и route
            lines = result.stdout.split('\n')
            if name == "Ping":
                for line in lines[:8]:
                    if line.strip():
                        print(f"     {line}")
            elif name == "IP Config":
                # Ищем интересные строки
                interesting = []
                for line in lines:
                    if any(x in line.lower() for x in ['dns', 'gateway', 'proxy', 'vpn', 'tunnel']):
                        interesting.append(line.strip())
                for line in interesting[:10]:
                    print(f"     {line}")
        except Exception as e:
            print(f"     Ошибка: {e}")
    
    # 6. Специальные тесты для Windows
    print("\n6. СПЕЦИАЛЬНЫЕ ТЕСТЫ ДЛЯ WINDOWS:")
    
    # Проверка Winsock
    print("   Проверка Winsock...")
    try:
        result = subprocess.run(["netsh", "winsock", "show", "catalog"],
                              capture_output=True, text=True, timeout=10)
        print("     Winsock каталог проверен")
    except Exception as e:
        print(f"     Ошибка: {e}")
    
    print("\n" + "=" * 70)
    print("ВОЗМОЖНЫЕ ПРИЧИНЫ И РЕШЕНИЯ:")
    print("=" * 70)
    
    solutions = [
        "ВОЗМОЖНАЯ ПРИЧИНА 1: Блокировка на уровне провайдера",
        "Решение:",
        "  1. Позвоните провайдеру, спросите о блокировке портов 465, 587, 25",
        "  2. Попробуйте подключиться через мобильный интернет (телефон как точка доступа)",
        "",
        "ВОЗМОЖНАЯ ПРИЧИНА 2: Антивирус/брандмауэр третьих производителей",
        "Решение:",
        "  1. Полностью отключите Касперский/Avast/Norton и т.д.",
        "  2. Перезагрузите компьютер после отключения",
        "",
        "ВОЗМОЖНАЯ ПРИЧИНА 3: VPN/Прокси-туннели",
        "Решение:",
        "  1. Отключите все VPN подключения",
        "  2. Сбросьте настройки сети:",
        "     - Откройте cmd как Администратор",
        "     - Выполните: netsh winsock reset",
        "     - Выполните: netsh int ip reset",
        "     - Выполните: ipconfig /flushdns",
        "     - Перезагрузите компьютер",
        "",
        "ВОЗМОЖНАЯ ПРИЧИНА 4: Проблема с самим сервером mail.asauda.ru",
        "Решение:",
        "  1. Проверьте сервер с другого компьютера/сети",
        "  2. Свяжитесь с администратором сервера",
        "  3. Используйте временно другой SMTP сервер:",
        "     - smtp.gmail.com:587 (с паролем приложения)",
        "     - smtp.yandex.ru:587",
        "     - smtp.mail.ru:587",
        "",
        "ВОЗМОЖНАЯ ПРИЧИНА 5: Корпоративные ограничения",
        "Решение:",
        "  1. Обратитесь к системному администратору вашей организации",
        "  2. Используйте корпоративный прокси если требуется",
    ]
    
    for line in solutions:
        print(line)

def test_from_other_locations():
    """Тестирование из разных мест"""
    
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ ИЗ РАЗНЫХ МЕСТ (чтобы локализовать проблему)")
    print("=" * 70)
    
    test_points = [
        ("1. ДРУГОЙ КОМПЬЮТЕР В ЭТОЙ ЖЕ СЕТИ", ""),
        ("2. ТЕЛЕФОН КАК ТОЧКА ДОСТУПА", "Подключите телефон как Wi-Fi точку доступа"),
        ("3. КАФЕ/ОБЩЕСТВЕННЫЙ WI-FI", "Сходите в кафе с ноутбуком"),
        ("4. ДОМАШНЯЯ СЕТЬ", "Проверьте с домашнего интернета"),
    ]
    
    for test_name, instruction in test_points:
        print(f"\n{test_name}:")
        print(f"  {instruction}")
        print("  Откройте браузер и перейдите на:")
        print(f"  https://check-host.net/check-tcp?host=mail.asauda.ru:465")
        print("  Или установите Python на другом устройстве и запустите:")
        print("  python -c \"import socket; s=socket.socket();")
        print(f"  s.settimeout(5); print(s.connect_ex(('mail.asauda.ru',465)))\"")
    
    print("\n" + "=" * 70)
    print("БЫСТРОЕ ВРЕМЕННОЕ РЕШЕНИЕ ДЛЯ FLASK:")
    print("=" * 70)
    
    temp_solution = '''# В config.py используйте временные настройки:

# Вариант 1: Используйте другой порт если 465 не работает
MAIL_PORT = 587  # вместо 465
MAIL_USE_TLS = True  # вместо MAIL_USE_SSL = True

# Вариант 2: Используйте другой SMTP сервер
MAIL_SERVER = 'smtp.gmail.com'  # Gmail
# или
MAIL_SERVER = 'smtp.yandex.ru'  # Yandex
# или
MAIL_SERVER = 'smtp.mail.ru'    # Mail.ru

# Для Gmail нужно создать пароль приложения:
# 1. Зайдите в настройки аккаунта Google
# 2. Безопасность -> Пароли приложений
# 3. Создайте пароль для "Почта"
'''
    
    print(temp_solution)

if __name__ == "__main__":
    network_comprehensive_diagnosis()
    test_from_other_locations()