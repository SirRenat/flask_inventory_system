from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, User, Region, City
import json
from app.utils import save_uploaded_files, process_category_image
import os

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к админке', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_category':
            name = request.form.get('name')
            parent_id = request.form.get('parent_id') or None
            description = request.form.get('description')
            
            if not name:
                flash('Название категории обязательно', 'error')
                return redirect(url_for('admin_bp.admin_categories'))
            
            existing_category = Category.query.filter_by(name=name, parent_id=parent_id).first()
            if existing_category:
                flash('Такая категория уже существует', 'error')
                return redirect(url_for('admin_bp.admin_categories'))
            
            try:
                new_category = Category(
                    name=name,
                    description=description,
                    parent_id=parent_id if parent_id else None
                )
                db.session.add(new_category)
                db.session.commit()
                flash(f'Категория "{name}" успешно добавлена', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении категории: {str(e)}', 'error')
        
        elif action == 'edit_category':
            category_id = request.form.get('category_id')
            name = request.form.get('name')
            parent_id = request.form.get('parent_id') or None
            description = request.form.get('description')
            remove_image = request.form.get('remove_image') == 'on'
            
            if not category_id:
                flash('ID категории не найден', 'error')
                return redirect(url_for('admin_bp.admin_categories'))
                
            category = Category.query.get(category_id)
            if not category:
                flash('Категория не найдена', 'error')
                return redirect(url_for('admin_bp.admin_categories'))
            
            if not name:
                flash('Название категории обязательно', 'error')
                return redirect(url_for('admin_bp.admin_categories'))
            
            # Проверка на цикличность при смене родителя
            if parent_id and str(parent_id) == str(category.id):
                flash('Категория не может быть родительской сама для себя', 'error')
                return redirect(url_for('admin_bp.admin_categories'))
            
            try:
                category.name = name
                category.description = description
                category.parent_id = parent_id if parent_id else None
                
                # Обработка изображения
                if remove_image and category.image:
                    # Удаляем старое изображение
                    try:
                        base_filename = category.image.rsplit('.', 1)[0]
                        ext = category.image.rsplit('.', 1)[1] if '.' in category.image else 'jpg'
                        sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
                        
                        folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories')
                        
                        for size in sizes:
                            fname = category.image if size == 'thumbnail' else f"{base_filename}_{size}.{ext}"
                            path = os.path.join(folder, fname)
                            if os.path.exists(path):
                                os.remove(path)
                    except Exception as e:
                        print(f"Ошибка удаления файла: {e}")
                    
                    category.image = None
                
                # Загрузка нового изображения
                if 'category_image' in request.files:
                    file = request.files['category_image']
                    if file and file.filename:
                        # Сначала удаляем старое если есть (и если не удалили выше)
                        if category.image and not remove_image:
                            try:
                                base_filename = category.image.rsplit('.', 1)[0]
                                ext = category.image.rsplit('.', 1)[1] if '.' in category.image else 'jpg'
                                sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
                                folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories')
                                for size in sizes:
                                    fname = category.image if size == 'thumbnail' else f"{base_filename}_{size}.{ext}"
                                    path = os.path.join(folder, fname)
                                    if os.path.exists(path):
                                        os.remove(path)
                            except Exception as e:
                                print(f"Ошибка удаления старого файла: {e}")

                        # Обрабатываем новое
                        filename, error = process_category_image(file, category.id)
                        if error:
                            flash(f'Ошибка обработки изображения: {error}', 'error')
                        else:
                            category.image = filename
                
                db.session.commit()
                flash(f'Категория "{name}" обновлена', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при редактировании: {str(e)}', 'error')
        
        elif action == 'delete_category':
            category_id = request.form.get('category_id')
            if category_id:
                category = Category.query.get(category_id)
                if category:
                    children = Category.query.filter_by(parent_id=category_id).all()
                    if children:
                        flash(f'Нельзя удалить категорию "{category.name}" - у нее есть дочерние категории', 'error')
                    else:
                        products_in_category = Product.query.filter_by(category_id=category_id).count()
                        if products_in_category > 0:
                            flash(f'Нельзя удалить категорию "{category.name}" - в ней есть товары', 'error')
                        else:
                            db.session.delete(category)
                            db.session.commit()
                            flash(f'Категория "{category.name}" удалена', 'success')
                else:
                    flash('Категория не найдена', 'error')
        
        elif action == 'clear_empty':
            categories = Category.query.all()
            deleted_count = 0
            for cat in categories:
                products_count = Product.query.filter_by(category_id=cat.id).count()
                children_count = Category.query.filter_by(parent_id=cat.id).count()
                
                if products_count == 0 and children_count == 0:
                    db.session.delete(cat)
                    deleted_count += 1
            
            if deleted_count > 0:
                db.session.commit()
                flash(f'Удалено {deleted_count} пустых категорий', 'success')
            else:
                flash('Пустых категорий не найдено', 'info')
        
        return redirect(url_for('admin_bp.admin_categories'))
    
    # ========== ОЧИСТКА НАЗВАНИЙ РЕГИОНОВ ==========
    # Находим регионы с префиксами (типа "01 - Республика Адыгея")
    regions_to_clean = Region.query.filter(Region.name.like('% - %')).all()
    if regions_to_clean:
        for region in regions_to_clean:
            # Убираем префиксы вида "01 - ", "02 -   "
            cleaned_name = region.name.split('-', 1)[-1].strip()
            region.name = cleaned_name
        db.session.commit()
        print(f"DEBUG: Очищены названия {len(regions_to_clean)} регионов")
    
    # Загружаем категории
    categories = Category.query.all()
    parent_categories = Category.query.filter_by(parent_id=None).all()
    total_products = Product.query.count()
    
    # Загружаем регионы
    all_regions = Region.query.all()
    regions = Region.query.filter_by(parent_id=None).all()
    child_regions = Region.query.filter(Region.parent_id.isnot(None)).all()

    return render_template(
            'admin_categories.html',
            categories=categories,
            parent_categories=parent_categories,
            total_products=total_products,
            all_regions=all_regions,      # ← все регионы
            regions=regions,              # ← родительские регионы
            child_regions=child_regions   # ← дочерние регионы
    )

# === РЕГИОНЫ ===
@admin_bp.route('/regions/add', methods=['POST'])
@login_required
def add_region():
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    
    name = request.form.get('name')
    parent_id = request.form.get('parent_id') or None
    description = request.form.get('description')
    
    if not name:
        flash('Название региона обязательно', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    
    existing = Region.query.filter_by(name=name, parent_id=parent_id).first()
    if existing:
        flash('Такой регион уже существует', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    
    try:
        new_region = Region(
            name=name,
            description=description,
            parent_id=parent_id if parent_id else None
        )
        db.session.add(new_region)
        db.session.commit()
        flash(f'Регион "{name}" добавлен', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'error')
    
    return redirect(url_for('admin_bp.admin_categories'))

@admin_bp.route('/regions/delete/<int:region_id>', methods=['POST'])
@login_required
def delete_region(region_id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    
    region = Region.query.get_or_404(region_id)
    children = Region.query.filter_by(parent_id=region_id).all()
    
    if children:
        flash(f'Нельзя удалить регион "{region.name}" — есть подрегионы', 'error')
    else:
        db.session.delete(region)
        db.session.commit()
        flash(f'Регион "{region.name}" удалён', 'success')
    
    return redirect(url_for('admin_bp.admin_categories'))

@admin_bp.route('/regions/clear_empty', methods=['POST'])
@login_required
def clear_empty_regions():
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    
    regions = Region.query.all()
    deleted = 0
    for r in regions:
        children = Region.query.filter_by(parent_id=r.id).count()
        if children == 0:
            db.session.delete(r)
            deleted += 1
    
    if deleted:
        db.session.commit()
        flash(f'Удалено {deleted} пустых регионов', 'success')
    else:
        flash('Пустых регионов не найдено', 'info')
    
    return redirect(url_for('admin_bp.admin_categories'))


# === УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ===
@admin_bp.route('/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к админке', 'error')
        return redirect(url_for('main.index'))
    
    search = request.args.get('search', '').strip()
    query = User.query
    
    if search:
        query = query.filter(
            User.username.ilike(f'%{search}%') |
            User.email.ilike(f'%{search}%') |
            User.company_name.ilike(f'%{search}%') |
            User.contact_person.ilike(f'%{search}%')
        )
    
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users, search=search)

@admin_bp.route('/users/<int:user_id>/impersonate')
@login_required
def impersonate_user(user_id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_users'))
    
    from flask_login import login_user
    user = User.query.get_or_404(user_id)
    login_user(user)
    flash(f'Вы вошли как {user.email}', 'success')
    return redirect(url_for('main.dashboard'))

@admin_bp.route('/users/<int:user_id>/toggle_active', methods=['POST'])
@login_required
def toggle_user_active(user_id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_users'))
    
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = 'активирован' if user.is_active else 'заблокирован'
    flash(f'Пользователь {status}', 'success')
    return redirect(url_for('admin_bp.admin_users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_users'))
    
    if user_id == current_user.id:
        flash('Нельзя удалить себя', 'error')
        return redirect(url_for('admin_bp.admin_users'))
    
    user = User.query.get_or_404(user_id)
    # Удаляем связанные товары
    Product.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удалён', 'success')
    return redirect(url_for('admin_bp.admin_users'))


# === ЗАГРУЗКА И ОЧИСТКА КАТЕГОРИЙ ===
@admin_bp.route('/upload-categories', methods=['POST'])
@login_required
def upload_categories():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к админке', 'error')
        return redirect(url_for('main.index'))
    
    if 'categories_file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    
    file = request.files['categories_file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    
    if not file.filename.endswith('.json'):
        flash('Только JSON файлы поддерживаются', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    
    try:
        categories_data = json.load(file)
        Category.query.delete()
        
        parent_count = 0
        child_count = 0
        
        for parent_data in categories_data:
            parent_category = Category(
                name=parent_data['name'],
                description=parent_data.get('description', '')
            )
            db.session.add(parent_category)
            db.session.flush()
            parent_count += 1
            
            for child_data in parent_data.get('children', []):
                child_category = Category(
                    name=child_data['name'],
                    description=child_data.get('description', ''),
                    parent_id=parent_category.id
                )
                db.session.add(child_category)
                child_count += 1
        
        db.session.commit()
        flash(f'✅ Загружено {parent_count} родительских и {child_count} дочерних категорий!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Ошибка загрузки: {str(e)}', 'error')
    
    return redirect(url_for('admin_bp.admin_categories'))

@admin_bp.route('/upload-locations', methods=['POST'])
@login_required
def upload_locations():
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    if 'locations_file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    file = request.files['locations_file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    file_type = request.form.get('file_type', 'json')
    clear_existing = request.form.get('clear_existing') == 'on'
    try:
        if clear_existing:
            products_count = Product.query.filter(
                (Product.region_id.isnot(None)) | (Product.city_id.isnot(None))
            ).count()
            if products_count > 0:
                flash(f'Нельзя удалить существующие данные - {products_count} товаров связаны с ними', 'error')
                return redirect(url_for('admin_bp.admin_categories'))
            City.query.delete()
            Region.query.delete()
            db.session.flush()
        added_regions = 0
        added_cities = 0
        region_cache = {}
        if file_type == 'csv':
            import csv
            import io
            content = file.read().decode('utf-8')
            for delimiter in [';', ',', '\t']:
                try:
                    csv_reader = csv.reader(io.StringIO(content), delimiter=delimiter)
                    rows = list(csv_reader)
                    if len(rows) > 0 and len(rows[0]) >= 2:
                        break
                except:
                    continue
            if rows and ('регион' in rows[0][0].lower() or 'region' in rows[0][0].lower()):
                rows = rows[1:]
            for row in rows:
                if len(row) >= 2:
                    region_name = row[0].strip()
                    city_name = row[1].strip()
                    if not region_name or not city_name:
                        continue
                    if region_name not in region_cache:
                        region = Region.query.filter_by(name=region_name, parent_id=None).first()
                        if not region:
                            region = Region(name=region_name)
                            db.session.add(region)
                            db.session.flush()
                            added_regions += 1
                        region_cache[region_name] = region
                    else:
                        region = region_cache[region_name]
                    existing_city = City.query.filter_by(
                        name=city_name, 
                        region_id=region.id
                    ).first()
                    if not existing_city:
                        city = City(name=city_name, region_id=region.id)
                        db.session.add(city)
                        added_cities += 1
        elif file_type == 'json':
            import json
            content = file.read().decode('utf-8')
            data = json.loads(content)
            if isinstance(data, dict) and 'regions' in data:
                for region_data in data['regions']:
                    region_name = region_data.get('name', '').strip()
                    cities_list = region_data.get('cities', [])
                    if not region_name:
                        continue
                    if region_name not in region_cache:
                        region = Region.query.filter_by(name=region_name, parent_id=None).first()
                        if not region:
                            region = Region(name=region_name)
                            db.session.add(region)
                            db.session.flush()
                            added_regions += 1
                        region_cache[region_name] = region
                    else:
                        region = region_cache[region_name]
                    for city_name in cities_list:
                        if isinstance(city_name, str) and city_name.strip():
                            city_name_clean = city_name.strip()
                            existing_city = City.query.filter_by(
                                name=city_name_clean, 
                                region_id=region.id
                            ).first()
                            if not existing_city:
                                city = City(name=city_name_clean, region_id=region.id)
                                db.session.add(city)
                                added_cities += 1
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        region_name = item.get('region', '').strip()
                        city_name = item.get('city', '').strip()
                        if not region_name or not city_name:
                            continue
                        if region_name not in region_cache:
                            region = Region.query.filter_by(name=region_name, parent_id=None).first()
                            if not region:
                                region = Region(name=region_name)
                                db.session.add(region)
                                db.session.flush()
                                added_regions += 1
                            region_cache[region_name] = region
                        else:
                            region = region_cache[region_name]
                        existing_city = City.query.filter_by(
                            name=city_name, 
                            region_id=region.id
                        ).first()
                        if not existing_city:
                            city = City(name=city_name, region_id=region.id)
                            db.session.add(city)
                            added_cities += 1
            else:
                flash('❌ Неподдерживаемый формат JSON файла', 'error')
                return redirect(url_for('admin_bp.admin_categories'))
        db.session.commit()
        if added_regions > 0 or added_cities > 0:
            flash(f'✅ Успешно добавлено {added_regions} регионов и {added_cities} городов', 'success')
        else:
            flash('⚠️ Новых регионов и городов не обнаружено', 'info')
    except json.JSONDecodeError as e:
        db.session.rollback()
        flash(f'❌ Ошибка чтения JSON: {str(e)}', 'error')
        print(f"Ошибка JSON: {str(e)}")
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Ошибка загрузки: {str(e)}', 'error')
        print(f"Ошибка загрузки локаций: {str(e)}")
    return redirect(url_for('admin_bp.admin_categories'))

@admin_bp.route('/cities/add', methods=['POST'])
@login_required
def add_city():
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    name = request.form.get('name', '').strip()
    region_id = request.form.get('region_id')
    description = request.form.get('description', '').strip()
    if not name:
        flash('Название города обязательно', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    if not region_id:
        flash('Выберите регион', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    existing = City.query.filter_by(name=name, region_id=region_id).first()
    if existing:
        flash('Такой город уже существует в этом регионе', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    try:
        new_city = City(
            name=name,
            region_id=int(region_id),
            description=description
        )
        db.session.add(new_city)
        db.session.commit()
        flash(f'Город "{name}" добавлен', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('admin_bp.admin_categories'))

@admin_bp.route('/cities/delete/<int:city_id>', methods=['POST'])
@login_required
def delete_city(city_id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    city = City.query.get_or_404(city_id)
    products_count = Product.query.filter_by(city=city.name).count()
    if products_count > 0:
        flash(f'Нельзя удалить город "{city.name}" — в нем есть товары', 'error')
        return redirect(url_for('admin_bp.admin_categories'))
    db.session.delete(city)
    db.session.commit()
    flash(f'Город "{city.name}" удалён', 'success')
    return redirect(url_for('admin_bp.admin_categories'))

@admin_bp.route('/clear-categories', methods=['POST'])
@login_required
def clear_categories():
    if not current_user.is_admin:
        flash('У вас нет прав доступа к админке', 'error')
        return redirect(url_for('main.index'))
    
    try:
        Product.query.update({Product.category_id: None})
        db.session.commit()
        
        count = Category.query.count()
        Category.query.delete()
        db.session.commit()
        flash(f'✅ Удалено {count} категорий', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Ошибка очистки: {str(e)}', 'error')
    
    return redirect(url_for('admin_bp.admin_categories'))

# === ОБРАТНАЯ СВЯЗЬ ===
@admin_bp.route('/contact-requests')
@login_required
def admin_contact_requests():
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('main.index'))
    
    from app.models import ContactRequest
    requests = ContactRequest.query.order_by(ContactRequest.created_at.desc()).all()
    return render_template('admin_contact_requests.html', requests=requests)

@admin_bp.route('/contact-requests/<int:request_id>/toggle-status', methods=['POST'])
@login_required
def toggle_request_status(request_id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'error')
        return redirect(url_for('admin_bp.admin_contact_requests'))
        
    from app.models import ContactRequest
    req = ContactRequest.query.get_or_404(request_id)
    if req.status == 'new':
        req.status = 'read'
    elif req.status == 'read':
        req.status = 'resolved'
    else:
        req.status = 'new'
    db.session.commit()
    flash('Статус обновлен', 'success')
    return redirect(url_for('admin_bp.admin_contact_requests'))

