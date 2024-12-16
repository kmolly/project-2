from flask import Flask, request, render_template
import requests
import os
import logging
from datetime import datetime, timedelta
import time


API_KEY = 'SwZliheDI2SF4A1melDzrsOwzvu8WlVW'

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_CALLS = 50  # calls
RATE_LIMIT_PERIOD = 3600  # seconds
last_calls = []

def check_rate_limit():
    """Implements a rolling window rate limiter."""
    current_time = datetime.now()
    # Remove calls outside the window
    global last_calls
    last_calls = [call_time for call_time in last_calls 
                 if current_time - call_time < timedelta(seconds=RATE_LIMIT_PERIOD)]
    
    if len(last_calls) >= RATE_LIMIT_CALLS:
        raise Exception("Rate limit exceeded. Please try again later.")
    
    last_calls.append(current_time)

def get_coordinates(city_name):
    """Gets coordinates (latitude and longitude) for a given city name."""
    if not isinstance(city_name, str) or not city_name.strip():
        raise ValueError("Invalid city name")
    
    city_name = city_name.strip()
    
    try:
        geocode_url = 'https://nominatim.openstreetmap.org/search'
        params = {
            'q': city_name,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'WeatherCheckApp/1.0'  # Required by OpenStreetMap
        }
        response = requests.get(geocode_url, 
                              params=params, 
                              headers=headers, 
                              timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if not data:
            raise ValueError(f"City {city_name} not found.")
            
        return {
            'lat': float(data[0]['lat']),
            'lon': float(data[0]['lon'])
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting coordinates for {city_name}: {str(e)}")
        raise Exception("Unable to get location coordinates. Please try again later.")

def get_weather_data(latitude, longitude):
    """Gets weather data for given latitude and longitude from AccuWeather."""
    check_rate_limit()
    
    try:
        # Get Location Key
        location_url = (
            'http://dataservice.accuweather.com/locations/v1/cities/geoposition/search'
        )
        params = {
            'apikey': API_KEY,
            'q': f'{latitude},{longitude}',
            'language': 'ru-ru'
        }
        response = requests.get(location_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if 'Key' not in data:
            raise ValueError("Invalid location data received from AccuWeather")
            
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
        response = requests.get(weather_url, params=params, timeout=10)
        response.raise_for_status()
        
        weather_data = response.json()
        if not weather_data:
            raise ValueError("No weather data received from AccuWeather")
            
        return weather_data[0]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting weather data: {str(e)}")
        raise Exception("Unable to fetch weather data. Please try again later.")

def check_bad_weather(temperature, wind_speed, precipitation_probability, humidity):
    """Determines whether the weather conditions are adverse."""
    try:
        temperature = float(temperature)
        wind_speed = float(wind_speed)
        precipitation_probability = float(precipitation_probability)
        humidity = float(humidity)
    except (TypeError, ValueError):
        raise ValueError("Invalid weather parameters provided")


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
    """Extracts necessary weather parameters from the weather data."""
    try:
        temperature = weather_info['Temperature']['Metric']['Value']
        humidity = weather_info['RelativeHumidity']
        wind_speed = weather_info['Wind']['Speed']['Metric']['Value']
        precipitation_probability = weather_info.get('PrecipitationProbability', 0)
        return temperature, wind_speed, precipitation_probability, humidity
    except KeyError as e:
        logger.error(f"Missing weather parameter: {str(e)}")
        raise ValueError("Invalid weather data format")

@app.route('/')
def home():
    """Renders the home page."""
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    """Processes the form submission and renders the result page."""
    try:
        start_point = request.form.get('start_point', '').strip()
        end_point = request.form.get('end_point', '').strip()

        if not start_point or not end_point:
            raise ValueError("Please provide both start and end points")

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

        return render_template(
            'result.html',
            start_point=start_point,
            end_point=end_point,
            start_bad=start_bad,
            end_bad=end_bad,
            start_weather=start_weather_info,
            end_weather=end_weather_info
        )
    except ValueError as e:
        return render_template('error.html', error_message=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return render_template('error.html', 
                             error_message="An unexpected error occurred. Please try again later.")

if __name__ == '__main__':
    app.run(debug=True)  # Set debug=False in production
