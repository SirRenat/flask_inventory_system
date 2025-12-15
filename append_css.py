
import os

style_path = r'c:\Users\Orbital\flask_inventory_system\app\static\css\style.css'
fix_path = r'c:\Users\Orbital\flask_inventory_system\app\static\css\contact_fix_final.css'

try:
    with open(fix_path, 'r', encoding='utf-8') as f:
        new_css = f.read()

    with open(style_path, 'a', encoding='utf-8') as f:
        f.write('\n' + new_css)
    
    print("Successfully appended CSS.")
except Exception as e:
    print(f"Error appending CSS: {e}")
