from flask import Blueprint, jsonify, request, current_app
from app.models import City, Region, Product
import json
import requests

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/dadata/company', methods=['POST'])
def get_dadata_company():
    try:
        data = request.get_json()
        inn = data.get('inn')
        if not inn:
            return jsonify({'error': 'ИНН обязателен'}), 400

        api_key = current_app.config.get('DADATA_API_KEY')
        if not api_key:
            return jsonify({'error': 'API ключ не настроен'}), 500

        url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {api_key}"
        }
        payload = {"query": inn}
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if not result['suggestions']:
            return jsonify({'error': 'Организация не найдена'}), 404

        company = result['suggestions'][0]['data']
        company_name = result['suggestions'][0]['value']
        
        return jsonify({
            'name': company_name,
            'address': company.get('address', {}).get('value'),
            'kpp': company.get('kpp'),
            'ogrn': company.get('ogrn'),
            'management_name': company.get('management', {}).get('name')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/locations')
def get_locations():
    try:
        search = request.args.get('search', '').strip()
        limit = int(request.args.get('limit', 30))
        results = []
        results.append({
            'id': 'all',
            'name': 'Все регионы',
            'type': 'all',
            'display_name': 'Все регионы'
        })
        if not search:
            popular_locations = [
                'Москва',
                'Санкт-Петербург', 
                'Казань',
                'Екатеринбург',
                'Новосибирск',
                'Нижний Новгород',
                'Ростов-на-Дону',
                'Уфа',
                'Красноярск',
                'Воронеж',
                'Пермь',
                'Волгоград',
                'Саратов',
                'Омск',
                'Челябинск',
                'Самара'
            ]
            for loc_name in popular_locations:
                city = City.query.filter_by(name=loc_name).first()
                if city:
                    results.append({
                        'id': f'city_{city.id}',
                        'name': city.name,
                        'type': 'city',
                        'display_name': f"{city.name} ({city.region.name if city.region else 'Неизвестный регион'})"
                    })
                    continue
                region = Region.query.filter_by(name=loc_name).first()
                if region:
                    results.append({
                        'id': f'region_{region.id}',
                        'name': region.name,
                        'type': 'region',
                        'display_name': region.name
                    })
        else:
            search_lower = search.lower()
            regions_start = Region.query.filter(
                Region.name.ilike(f'{search_lower}%')
            ).order_by(Region.name).limit(limit // 2).all()
            regions_contains = Region.query.filter(
                Region.name.ilike(f'%{search_lower}%')
            ).order_by(Region.name).limit(limit // 2).all()
            all_regions = regions_start + [r for r in regions_contains if r not in regions_start]
            all_regions = all_regions[:limit // 2]
            for region in all_regions:
                results.append({
                    'id': f'region_{region.id}',
                    'name': region.name,
                    'type': 'region',
                    'display_name': region.name
                })
            cities_start = City.query.join(Region).filter(
                City.name.ilike(f'{search_lower}%')
            ).order_by(City.name).limit(limit // 2).all()
            cities_contains = City.query.join(Region).filter(
                City.name.ilike(f'%{search_lower}%')
            ).order_by(City.name).limit(limit // 2).all()
            all_cities = cities_start + [c for c in cities_contains if c not in cities_start]
            all_cities = all_cities[:limit // 2]
            for city in all_cities:
                results.append({
                    'id': f'city_{city.id}',
                    'name': city.name,
                    'type': 'city',
                    'display_name': f"{city.name} ({city.region.name if city.region else 'Неизвестный регион'})"
                })
        if search and len(results) <= 1:
            popular_cities_extended = [
                'Архангельск', 'Астрахань', 'Анапа', 'Альметьевск', 'Абакан',
                'Брянск', 'Белгород', 'Барнаул', 'Благовещенск', 'Бийск', 'Братск',
                'Владивосток', 'Волгоград', 'Владимир', 'Вологда', 'Воронеж',
                'Грозный', 'Геленджик',
                'Донецк', 'Дзержинск', 'Димитровград',
                'Екатеринбург', 'Елец', 'Евпатория',
                'Железногорск',
                'Златоуст',
                'Ижевск', 'Иркутск', 'Иваново',
                'Йошкар-Ола',
                'Казань', 'Краснодар', 'Красноярск', 'Калининград', 'Кемерово',
                'Киров', 'Кострома', 'Курск', 'Курган', 'Комсомольск-на-Амуре',
                'Липецк', 'Люберцы',
                'Москва', 'Махачкала', 'Мурманск', 'Магнитогорск', 'Муром',
                'Нижний Новгород', 'Новосибирск', 'Новороссийск', 'Норильск',
                'Набережные Челны', 'Нефтеюганск',
                'Омск', 'Оренбург', 'Орёл', 'Обнинск',
                'Пермь', 'Пенза', 'Псков', 'Петрозаводск', 'Подольск',
                'Ростов-на-Дону', 'Рязань', 'Рыбинск',
                'Санкт-Петербург', 'Самара', 'Саратов', 'Смоленск', 'Сочи',
                'Ставрополь', 'Стерлитамак', 'Сургут', 'Сыктывкар', 'Северодвинск',
                'Тверь', 'Тула', 'Тюмень', 'Таганрог', 'Тольятти', 'Томск',
                'Уфа', 'Ульяновск', 'Улан-Удэ',
                'Феодосия',
                'Хабаровск', 'Химки',
                'Челябинск', 'Чебоксары', 'Чита',
                'Шахты',
                'Щёлково',
                'Элиста', 'Энгельс',
                'Южно-Сахалинск',
                'Ярославль', 'Якутск'
            ]
            search_lower = search.lower()
            
            for city_name in popular_cities_extended:
                if search_lower in city_name.lower():
                    city_lower = city_name.lower()
                    if city_lower.startswith(search_lower):
                        results.insert(1, {
                            'id': f'static_city_{city_name}',
                            'name': city_name,
                            'type': 'city',
                            'display_name': city_name,
                            'priority': 1
                        })
                    else:
                        results.append({
                            'id': f'static_city_{city_name}',
                            'name': city_name,
                            'type': 'city',
                            'display_name': city_name,
                            'priority': 0
                        })
        
        def sort_key(item):
            if item['display_name'] == 'Все регионы':
                return (0, '')
            elif item.get('priority') == 1:
                return (1, item['display_name'])
            else:
                return (2, item['display_name'])
        results.sort(key=sort_key)
        seen = set()
        unique_results = []
        for item in results:
            if item['display_name'] not in seen:
                seen.add(item['display_name'])
                unique_results.append(item)
        return jsonify(unique_results[:limit])
    except Exception as e:
        fallback_results = [
            {'id': 'all', 'name': 'Все регионы', 'type': 'all', 'display_name': 'Все регионы'},
            {'id': 'city_1', 'name': 'Москва', 'type': 'city', 'display_name': 'Москва'},
            {'id': 'city_2', 'name': 'Санкт-Петербург', 'type': 'city', 'display_name': 'Санкт-Петербург'},
            {'id': 'city_3', 'name': 'Казань', 'type': 'city', 'display_name': 'Казань'},
            {'id': 'city_4', 'name': 'Екатеринбург', 'type': 'city', 'display_name': 'Екатеринбург'},
            {'id': 'city_5', 'name': 'Новосибирск', 'type': 'city', 'display_name': 'Новосибирск'},
            {'id': 'city_6', 'name': 'Нижний Новгород', 'type': 'city', 'display_name': 'Нижний Новгород'},
            {'id': 'city_7', 'name': 'Ростов-на-Дону', 'type': 'city', 'display_name': 'Ростов-на-Дону'},
            {'id': 'city_8', 'name': 'Уфа', 'type': 'city', 'display_name': 'Уфа'},
        ]
        if search:
            search_lower = search.lower()
            filtered_results = [fallback_results[0]]
            for item in fallback_results[1:]:
                if search_lower in item['name'].lower():
                    filtered_results.append(item)
            return jsonify(filtered_results)
        return jsonify(fallback_results)

@api_bp.route('/api/regions')
def get_regions():
    regions = Region.query.filter_by(parent_id=None).order_by(Region.name).all()
    result = []
    for region in regions:
        region_data = {
            'id': region.id,
            'name': region.name,
            'cities': []
        }
        cities = City.query.filter_by(region_id=region.id).order_by(City.name).all()
        for city in cities:
            region_data['cities'].append({
                'id': city.id,
                'name': city.name,
                'full_name': f"{city.name} ({region.name})"
            })
        result.append(region_data)
    return jsonify(result)

@api_bp.route('/api/cities/by-region/<int:region_id>')
def get_cities_by_region(region_id):
    cities = City.query.filter_by(region_id=region_id).order_by(City.name).all()
    result = []
    for city in cities:
        result.append({
            'id': city.id,
            'name': city.name,
            'full_name': f"{city.name} (Регион ID: {region_id})"
        })
    response = current_app.response_class(
        response=json.dumps(result, ensure_ascii=False),
        status=200,
        mimetype='application/json; charset=utf-8'
    )
    return response
