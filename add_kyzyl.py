import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="flask_inventory",
    user="postgres", 
    password="postgres"
)
conn.set_client_encoding('UTF8')

cursor = conn.cursor()

# Сначала найдем ID региона "Республика Тыва"
cursor.execute("SELECT id, name FROM region WHERE name LIKE '%Тыва%' OR name LIKE '%Тува%';")
region = cursor.fetchone()

if region:
    region_id, region_name = region
    print(f"✅ Найден регион: {region_name} (ID: {region_id})")
    
    # Добавляем город Кызыл
    cursor.execute(
        "INSERT INTO city (name, region_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        ('Кызыл', region_id)
    )
    conn.commit()
    print(f"✅ Город 'Кызыл' добавлен для региона {region_name}")
    
    # Проверяем
    cursor.execute("SELECT id, name, region_id FROM city WHERE name = 'Кызыл';")
    kyzyl = cursor.fetchone()
    if kyzyl:
        print(f"✅ Город в базе: ID={kyzyl[0]}, Регион ID={kyzyl[2]}")
else:
    print("❌ Регион 'Республика Тыва' не найден!")
    # Покажите все регионы
    cursor.execute("SELECT id, name FROM region ORDER BY name;")
    regions = cursor.fetchall()
    print("\nВсе регионы:")
    for reg in regions:
        print(f"  ID: {reg[0]}, Название: {reg[1]}")

cursor.close()
conn.close()