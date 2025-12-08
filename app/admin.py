from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, User
from app.models import Region
import json

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
            flash('Редактирование категорий пока недоступно', 'info')
        
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