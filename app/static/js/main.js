
// === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
let currentLocation = localStorage.getItem('userLocation') || 'Казань';
let searchTimeout = null;
let selectedCategoryId = localStorage.getItem('selectedCategoryId') || '';

// === ОСНОВНЫЕ ФУНКЦИИ ===
function applyFilters(categoryId = '', searchTerm = '') {
    let url = '/';
    const params = new URLSearchParams();
    if (categoryId) params.append('category_id', categoryId);
    if (searchTerm) params.append('search', searchTerm);
    if (currentLocation && currentLocation !== 'Все регионы') {
        params.append('location', currentLocation);
    }
    if (params.toString()) url += '?' + params.toString();
    window.location.href = url;
}

// === ФУНКЦИИ ДЛЯ КАТЕГОРИЙ ===
function selectCategory(categoryElement, categoryId) {
    // Убираем активный класс у всех категорий
    document.querySelectorAll('.main-category-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Добавляем активный класс выбранной категории
    categoryElement.classList.add('active');
    
    // Сохраняем выбранную категорию
    selectedCategoryId = categoryId;
    localStorage.setItem('selectedCategoryId', categoryId);
    
    // Обновляем селект выбора категории
    const categorySelect = document.getElementById('categoryFilter');
    if (categorySelect) {
        // Находим опцию с нужным значением или с текстом
        let found = false;
        for (let option of categorySelect.options) {
            if (option.value === categoryId || option.text === categoryElement.dataset.categoryName) {
                option.selected = true;
                found = true;
                break;
            }
        }
        // Если не нашли точного соответствия, выбираем "Все категории"
        if (!found && categorySelect.options.length > 0) {
            categorySelect.options[0].selected = true;
        }
    }
    
    // Применяем фильтры
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput ? searchInput.value.trim() : '';
    applyFilters(categoryId, searchTerm);
}

// === ФУНКЦИИ ДЛЯ МОДАЛЬНОГО ОКНА ===
function openLocationModal() {
    const modal = document.getElementById('locationModal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        // Показываем текущую выбранную локацию в поле поиска
        const locationInput = document.getElementById('locationInput');
        if (locationInput) {
            if (currentLocation === 'Все регионы') {
                locationInput.value = '';
            } else {
                locationInput.value = currentLocation;
            }
        }
        // Показываем популярные города
        loadPopularLocations();
        setTimeout(() => {
            if (locationInput) locationInput.focus();
        }, 100);
    }
}

function closeLocationModal() {
    const modal = document.getElementById('locationModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function clearLocationInput() {
    const input = document.getElementById('locationInput');
    input.value = '';
    input.focus();
    loadPopularLocations();
}

// Функция загрузки популярных локаций из API
async function loadPopularLocations() {
    const suggestions = document.getElementById('locationSuggestions');
    // Показываем индикатор загрузки
    suggestions.innerHTML = `
        <div class="suggestion-item" onclick="setLocation('Все регионы')">
            Все регионы
        </div>
        <div class="loading-indicator">Загрузка</div>
    `;
    try {
        const response = await fetch('/api/locations?limit=30');
        const locations = await response.json();
        suggestions.innerHTML = '';
        // 1. Текущий выбранный город, если он есть и это не "Все регионы"
        if (currentLocation && currentLocation !== 'Все регионы') {
            const currentDiv = document.createElement('div');
            currentDiv.className = 'suggestion-item current-location';
            currentDiv.innerHTML = `<strong>${currentLocation}</strong> (текущий)`;
            currentDiv.onclick = function() {
                closeLocationModal();
            };
            suggestions.appendChild(currentDiv);
        }
        // 2. "Все регионы" всегда на видном месте
        const allRegionsDiv = document.createElement('div');
        allRegionsDiv.className = 'suggestion-item all-regions';
        allRegionsDiv.innerHTML = 'Все регионы';
        allRegionsDiv.onclick = function() {
            setLocation('Все регионы');
        };
        suggestions.appendChild(allRegionsDiv);
        // 3. Разделитель
        const separator = document.createElement('div');
        separator.className = 'suggestion-separator';
        separator.innerHTML = 'Другие регионы и города';
        suggestions.appendChild(separator);
        // 4. Остальные локации из API
        for (let location of locations) {
            // Пропускаем "Все регионы" (уже добавили) и текущий город (уже добавили)
            if (location.display_name === 'Все регионы') continue;
            if (location.display_name === currentLocation) continue;
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.innerHTML = location.display_name;
            div.onclick = function() {
                setLocation(location.display_name);
            };
            suggestions.appendChild(div);
        }
    } catch (error) {
        console.error('Ошибка загрузки локаций:', error);
        // Запасной статичный список
        suggestions.innerHTML = `
            <div class="suggestion-item" onclick="setLocation('Все регионы')">
                Все регионы
            </div>
            <div class="suggestion-item" onclick="setLocation('Москва')">
                Москва
            </div>
            <div class="suggestion-item" onclick="setLocation('Санкт-Петербург')">
                Санкт-Петербург
            </div>
            <div class="suggestion-item" onclick="setLocation('Казань')">
                Казань
            </div>
            <div class="suggestion-item no-results">Ошибка загрузки данных</div>
        `;
    }
}

// Функция поиска локаций через API
async function searchLocations(searchTerm) {
    const suggestions = document.getElementById('locationSuggestions');
    if (!searchTerm || searchTerm.trim() === '') {
        // Если поле пустое, показываем популярные
        loadPopularLocations();
        return;
    }
    // Показываем индикатор загрузки
    suggestions.innerHTML = `
        <div class="suggestion-item" onclick="setLocation('Все регионы')">
            Все регионы
        </div>
        <div class="loading-indicator">Поиск</div>
    `;
    try {
        const response = await fetch(`/api/locations?search=${encodeURIComponent(searchTerm)}&limit=30`);
        const locations = await response.json();
        suggestions.innerHTML = '';
        // 1. Всегда показываем "Все регионы"
        const allRegionsDiv = document.createElement('div');
        allRegionsDiv.className = 'suggestion-item all-regions';
        allRegionsDiv.innerHTML = 'Все регионы';
        allRegionsDiv.onclick = function() {
            setLocation('Все регионы');
        };
        suggestions.appendChild(allRegionsDiv);
        // 2. Разделитель
        const separator = document.createElement('div');
        separator.className = 'suggestion-separator';
        separator.innerHTML = 'Результаты поиска';
        suggestions.appendChild(separator);
        // 3. Добавляем найденные локации
        let hasResults = false;
        for (let location of locations) {
            if (location.display_name === 'Все регионы') continue;
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.innerHTML = location.display_name;
            div.onclick = function() {
                setLocation(location.display_name);
            };
            suggestions.appendChild(div);
            hasResults = true;
        }
        // 4. Если результатов нет (кроме "Все регионы")
        if (!hasResults) {
            suggestions.innerHTML += '<div class="suggestion-item no-results">Ничего не найдено</div>';
        }
    } catch (error) {
        console.error('Ошибка поиска локаций:', error);
        suggestions.innerHTML = `
            <div class="suggestion-item" onclick="setLocation('Все регионы')">
                Все регионы
            </div>
            <div class="suggestion-item no-results">Ошибка поиска</div>
        `;
    }
}

// Функция для задержки поиска (debounce)
function debounceSearch() {
    const input = document.getElementById('locationInput');
    const searchTerm = input.value.trim();
    // Очищаем предыдущий таймаут
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    // Устанавливаем новый таймаут
    searchTimeout = setTimeout(() => {
        searchLocations(searchTerm);
    }, 300);
}

function setLocation(location) {
    currentLocation = location.trim();
    localStorage.setItem('userLocation', currentLocation);
    document.getElementById('locationText').textContent = currentLocation;
    closeLocationModal();
    // Применяем фильтры с новым местоположением
    const categorySelect = document.getElementById('categoryFilter');
    const searchInput = document.getElementById('searchInput');
    const categoryId = categorySelect ? categorySelect.value : '';
    const searchTerm = searchInput ? searchInput.value.trim() : '';
    applyFilters(categoryId, searchTerm);
}

// === ИНИЦИАЛИЗАЦИЯ ===
document.addEventListener('DOMContentLoaded', function() {
    // Восстанавливаем выбранную категорию при загрузке
    if (selectedCategoryId) {
        const categoryElement = document.querySelector(`.main-category-item[data-category-id="${selectedCategoryId}"]`);
        if (categoryElement) {
            categoryElement.classList.add('active');
        } else {
            // Если не нашли по id, ищем по имени категории из localStorage
            const categoryName = localStorage.getItem('selectedCategoryName');
            if (categoryName) {
                const categoryElementByName = document.querySelector(`.main-category-item[data-category-name="${categoryName}"]`);
                if (categoryElementByName) {
                    categoryElementByName.classList.add('active');
                    selectedCategoryId = categoryElementByName.dataset.categoryId;
                }
            }
        }
    } else {
        // Если категория не выбрана, активируем "Все категории"
        const allCategories = document.querySelector('.main-category-item[data-category-id=""]');
        if (allCategories) {
            allCategories.classList.add('active');
        }
    }
    
    // Сохраняем имя категории при клике
    document.querySelectorAll('.main-category-item').forEach(item => {
        item.addEventListener('click', function() {
            const categoryName = this.dataset.categoryName;
            if (categoryName) {
                localStorage.setItem('selectedCategoryName', categoryName);
            }
        });
    });
    
    // Устанавливаем текущую локацию
    const locationText = document.getElementById('locationText');
    if (locationText) {
        locationText.textContent = currentLocation;
    }
    
    // Спрашиваем локацию при первом посещении
    const alreadyAsked = localStorage.getItem('locationAsked');
    if (!alreadyAsked) {
        setTimeout(() => {
            openLocationModal();
            localStorage.setItem('locationAsked', 'true');
        }, 1500);
    }
    
    // Обработчики для модального окна
    const locationDisplay = document.getElementById('locationDisplay');
    if (locationDisplay) {
        locationDisplay.addEventListener('click', openLocationModal);
    }
    
    const locationInput = document.getElementById('locationInput');
    if (locationInput) {
        locationInput.addEventListener('input', debounceSearch);
        locationInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                debounceSearch();
            }
        });
    }
    
    // Обработчики для фильтров
    const categorySelect = document.getElementById('categoryFilter');
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.querySelector('.search-btn');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            const categoryId = categorySelect ? categorySelect.value : '';
            const searchTerm = searchInput ? searchInput.value.trim() : '';
            applyFilters(categoryId, searchTerm);
        });
    }
    
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            // При изменении селекта, обновляем активную категорию в блоке картинок
            const selectedValue = this.value;
            document.querySelectorAll('.main-category-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Ищем соответствующий элемент категории
            let found = false;
            document.querySelectorAll('.main-category-item').forEach(item => {
                if (item.dataset.categoryId === selectedValue) {
                    item.classList.add('active');
                    found = true;
                    selectedCategoryId = selectedValue;
                    localStorage.setItem('selectedCategoryId', selectedValue);
                }
            });
            
            // Если не нашли, активируем "Все категории"
            if (!found) {
                const allCategories = document.querySelector('.main-category-item[data-category-id=""]');
                if (allCategories) {
                    allCategories.classList.add('active');
                    selectedCategoryId = '';
                    localStorage.setItem('selectedCategoryId', '');
                }
            }
            
            const searchTerm = searchInput ? searchInput.value.trim() : '';
            applyFilters(selectedValue, searchTerm);
        });
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const categoryId = categorySelect ? categorySelect.value : '';
                applyFilters(categoryId, this.value.trim());
            }
        });
    }
    
    // Закрытие модального окна при клике вне его
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('locationModal');
        if (event.target === modal) {
            closeLocationModal();
        }
    });
    
    // Закрытие модального окна по ESC
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeLocationModal();
        }
    });
    
    // Переключение видов товаров
    const viewButtons = document.querySelectorAll('.view-btn');
    
    function activateView(viewType) {
        const containers = {
            grid: document.getElementById('productsGridView'),
            list: document.getElementById('productsListView'),
            table: document.getElementById('productsTableView')
        };
        
        // Показываем только выбранный вид, скрываем остальные
        for (let key in containers) {
            if (containers[key]) {
                containers[key].style.display = key === viewType ? 'block' : 'none';
            }
        }
        
        // Обновляем активную кнопку
        viewButtons.forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-view') === viewType);
        });
        
        // Сохраняем выбор в localStorage
        localStorage.setItem('mainView', viewType);
    }
    
    viewButtons.forEach(button => {
        button.addEventListener('click', () => {
            const viewType = button.getAttribute('data-view');
            activateView(viewType);
        });
    });
    
    // Инициализация представления при загрузке
    const savedView = localStorage.getItem('mainView') || 'grid';
    activateView(savedView);
    
});
