from flask import Blueprint, render_template

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
def admin_panel():
    return render_template('admin.html')  # или временная заглушка