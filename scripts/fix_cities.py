import psycopg2
import sys

# Данные подключения
conn = psycopg2.connect(
    host="localhost",
    database="flask_inventory",
    user="postgres",
    password="postgres"
)
conn.set_client_encoding('UTF8')

cursor = conn.cursor()

# Удаляем старые данные
cursor.execute("DELETE FROM city;")

# Добавляем города
cities = [
    ('Уфа', 2),
    ('Саранск', 13)
]

for city_name, region_id in cities:
    cursor.execute(
        "INSERT INTO city (name, region_id) VALUES (%s, %s)",
        (city_name, region_id)
    )
    print(f"Добавлен город: {city_name} для региона {region_id}")

conn.commit()

# Проверяем
cursor.execute("SELECT id, name, region_id FROM city ORDER BY id;")
cities = cursor.fetchall()
print("\nГорода в базе:")
for city in cities:
    print(f"ID: {city[0]}, Название: {city[1]}, Регион ID: {city[2]}")

cursor.close()
conn.close()