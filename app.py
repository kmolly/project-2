from flask import Flask, request, render_template
import requests

API_KEY = 'SwZliheDI2SF4A1melDzrsOwzvu8WlVW'

app = Flask(__name__)


def get_coordinates(city_name):
    """Gets coordinates (latitude and longitude) for a given city name.

    Args:
        city_name: The name of the city to geocode.

    Returns:
        A dictionary with keys 'lat' and 'lon' for latitude and longitude.

    Raises:
        ValueError: If the city is not found.
    """
    geocode_url = 'https://nominatim.openstreetmap.org/search'
    params = {
        'q': city_name,
        'format': 'json',
        'limit': 1
    }
    response = requests.get(geocode_url, params=params)
    data = response.json()
    if data:
        return {
            'lat': float(data[0]['lat']),
            'lon': float(data[0]['lon'])
        }
    else:
        raise ValueError(f"City {city_name} not found.")


def get_weather_data(latitude, longitude):
    """Gets weather data for given latitude and longitude from AccuWeather.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A dictionary containing the weather data.
    """
    # Get Location Key
    location_url = (
        'http://dataservice.accuweather.com/locations/v1/cities/geoposition/search'
    )
    params = {
        'apikey': API_KEY,
        'q': f'{latitude},{longitude}',
        'language': 'ru-ru'
    }
    response = requests.get(location_url, params=params)
    data = response.json()
    location_key = data['Key']

    # Get current conditions
    weather_url = (
        f'http://dataservice.accuweather.com/currentconditions/v1/{location_key}'
    )
    params = {
        'apikey': API_KEY,
        'language': 'ru-ru',
        'details': 'true'
    }
    response = requests.get(weather_url, params=params)
    weather_data = response.json()
    return weather_data[0]


def check_bad_weather(temperature, wind_speed, precipitation_probability, humidity):
    """Determines whether the weather conditions are adverse.

    Args:
        temperature: The temperature in degrees Celsius.
        wind_speed: The wind speed in km/h.
        precipitation_probability: The probability of precipitation (percentage).
        humidity: The relative humidity (percentage).

    Returns:
        True if the weather conditions are considered adverse, False otherwise.
    """
    if temperature < 0 or temperature > 35:
        return True
    if wind_speed > 50:
        return True
    if precipitation_probability > 70:
        return True
    if humidity > 80:
        return True
    return False


def extract_weather_params(weather_info):
    """Extracts necessary weather parameters from the weather data.

    Args:
        weather_info: The weather data dictionary.

    Returns:
        A tuple containing temperature, wind_speed, precipitation_probability, humidity.
    """
    temperature = weather_info['Temperature']['Metric']['Value']
    humidity = weather_info['RelativeHumidity']
    wind_speed = weather_info['Wind']['Speed']['Metric']['Value']
    precipitation_probability = weather_info.get('PrecipitationProbability', 0)
    return temperature, wind_speed, precipitation_probability, humidity


@app.route('/')
def home():
    """Renders the home page."""
    return render_template('index.html')


@app.route('/result', methods=['POST'])
def result():
    """Processes the form submission and renders the result page."""
    start_point = request.form['start_point']
    end_point = request.form['end_point']

    try:
        # Get coordinates
        start_coords = get_coordinates(start_point)
        end_coords = get_coordinates(end_point)

        # Get weather data
        start_weather_info = get_weather_data(start_coords['lat'], start_coords['lon'])
        end_weather_info = get_weather_data(end_coords['lat'], end_coords['lon'])

        # Extract necessary parameters
        start_params = extract_weather_params(start_weather_info)
        end_params = extract_weather_params(end_weather_info)

        # Evaluate weather conditions
        start_bad = check_bad_weather(*start_params)
        end_bad = check_bad_weather(*end_params)

        # Pass data to the template
        return render_template(
            'result.html',
            start_point=start_point,
            end_point=end_point,
            start_bad=start_bad,
            end_bad=end_bad
        )
    except Exception as e:
        return render_template('error.html', error_message=str(e))


if __name__ == '__main__':
    app.run(debug=True)
