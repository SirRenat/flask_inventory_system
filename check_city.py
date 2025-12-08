import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="flask_inventory", 
    user="postgres",
    password="postgres"
)
conn.set_client_encoding('UTF8')

cursor = conn.cursor()

# 1. Проверьте все города
cursor.execute("SELECT id, name, region_id FROM city ORDER BY id;")
cities = cursor.fetchall()
print("Все города в базе:")
for city in cities:
    print(f"  ID: {city[0]}, Название: '{city[1]}', Регион ID: {city[2]}")

# 2. Проверьте конкретно Кызыл
cursor.execute("SELECT id, name, region_id FROM city WHERE name = %s", ('Кызыл',))
kyzyl = cursor.fetchone()
if kyzyl:
    print(f"\n✅ Город Кызыл найден:")
    print(f"   ID: {kyzyl[0]}, Регион ID: {kyzyl[2]}")
else:
    print("\n❌ Город Кызыл не найден!")

# 3. Проверьте API endpoint
print(f"\n🌐 API endpoint: /api/cities/by-region/{kyzyl[2] if kyzyl else '?'}")

cursor.close()
conn.close()