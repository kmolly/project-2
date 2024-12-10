from flask import Flask, request, render_template
import requests

# API-ключ для AccuWeather
API_KEY = 'SwZliheDI2SF4A1melDzrsOwzvu8WlVW'

# Создание экземпляра приложения Flask
app = Flask(__name__)

# Вспомогательная функция: Получение координат города
def get_coordinates(city_name):
    """
    Получает широту и долготу для заданного названия города с использованием API OpenStreetMap.
    """
    geocode_url = 'https://nominatim.openstreetmap.org/search'
    params = {'q': city_name, 'format': 'json', 'limit': 1}
    response = requests.get(geocode_url, params=params)
    data = response.json()
    
    if not data:
        raise ValueError(f"Город '{city_name}' не найден.")
    return {'lat': float(data[0]['lat']), 'lon': float(data[0]['lon'])}

# Вспомогательная функция: Получение данных о погоде по координатам
def get_weather_data(latitude, longitude):
    """
    Получает данные о погоде для указанных координат с использованием API AccuWeather.
    """
    # Получение ключа местоположения
    location_url = 'http://dataservice.accuweather.com/locations/v1/cities/geoposition/search'
    params = {'apikey': API_KEY, 'q': f'{latitude},{longitude}', 'language': 'ru-ru'}
    location_response = requests.get(location_url, params=params)
    location_data = location_response.json()

    if 'Key' not in location_data:
        raise ValueError("Не удалось получить ключ местоположения из ответа API AccuWeather.")
    
    # Получение текущих погодных условий
    location_key = location_data['Key']
    weather_url = f'http://dataservice.accuweather.com/currentconditions/v1/{location_key}'
    params = {'apikey': API_KEY, 'language': 'ru-ru', 'details': 'true'}
    weather_response = requests.get(weather_url, params=params)
    weather_data = weather_response.json()

    if not weather_data:
        raise ValueError("Данные о погоде не найдены.")
    return weather_data[0]

# Вспомогательная функция: Проверка неблагоприятных погодных условий
def check_bad_weather(temperature, wind_speed, precipitation_probability, humidity):
    """
    Определяет, являются ли погодные условия неблагоприятными.
    """
    return (
        temperature < 0 or temperature > 35 or
        wind_speed > 50 or
        precipitation_probability > 70 or
        humidity > 80
    )

# Вспомогательная функция: Извлечение параметров погоды
def extract_weather_params(weather_info):
    """
    Извлекает температуру, скорость ветра, вероятность осадков и влажность из данных о погоде.
    """
    temperature = weather_info['Temperature']['Metric']['Value']
    wind_speed = weather_info['Wind']['Speed']['Metric']['Value']
    humidity = weather_info['RelativeHumidity']
    precipitation_probability = weather_info.get('PrecipitationProbability', 0)
    return temperature, wind_speed, precipitation_probability, humidity

# Маршрут: Главная страница
@app.route('/')
def home():
    """
    Рендеринг главной страницы.
    """
    return render_template('index.html')

# Маршрут: Обработка сравнения погоды
@app.route('/result', methods=['POST'])
def result():
    """
    Обрабатывает данные из формы, выполняет вычисления и отображает страницу с результатами.
    """
    start_point = request.form.get('start_point')  # Начальная точка маршрута
    end_point = request.form.get('end_point')      # Конечная точка маршрута

    try:
        # Получение координат
        start_coords = get_coordinates(start_point)
        end_coords = get_coordinates(end_point)

        # Получение данных о погоде
        start_weather = get_weather_data(start_coords['lat'], start_coords['lon'])
        end_weather = get_weather_data(end_coords['lat'], end_coords['lon'])

        # Извлечение параметров погоды
        start_params = extract_weather_params(start_weather)
        end_params = extract_weather_params(end_weather)

        # Проверка неблагоприятных условий
        start_bad = check_bad_weather(*start_params)
        end_bad = check_bad_weather(*end_params)

        # Рендеринг страницы с результатами
        return render_template(
            'result.html',
            start_point=start_point,
            end_point=end_point,
            start_bad=start_bad,
            end_bad=end_bad
        )
    except Exception as e:
        # Обработка ошибок и рендеринг страницы с ошибкой
        return render_template('error.html', error_message=str(e))

# Запуск приложения Flask
if __name__ == '__main__':
    app.run(debug=True)