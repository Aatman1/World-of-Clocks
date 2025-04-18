import sys
import requests
import io
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, 
                                QLineEdit, QLabel, QListWidget, QGraphicsView, QGraphicsScene, QFrame, 
                                QTextBrowser, QScrollArea, QSizePolicy, QMessageBox, QInputDialog)
from PyQt6.QtCore import QTimer, Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QFont, QPixmap, QImage, QIcon
from datetime import datetime
import math
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pycountry
import geopandas as gpd
import matplotlib.pyplot as plt

try:
    import requests
except ImportError as e:
    # print(f"Error importing requests: {e}")
    sys.exit(1)
class ForecastWindow(QWidget):
    def __init__(self, location_info):
        super().__init__()
        self.city, self.timezone_str, self.lat, self.lon, self.country_code = location_info
        self.initUI()
        icon = QIcon("Wclock.png")
        self.setWindowIcon(icon)

    def initUI(self):
        self.setWindowTitle("Loading forecast...")
        self.resize(1100, 1000)  # Set initial size, but allow resizing

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.forecast_label = QLabel("Forecast")
        self.forecast_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.forecast_label)

        self.header_label = QLabel("<table style='font-size: 18px; line-height: 1.5; border-spacing: 15px;'>"
                                   "<tr>"
                                   "<th style='padding: 30px; width: 100px;'>Time</th>"
                                   "<th style='padding: 30px; width: 200px;'>Temperature °C (°F)</th>"
                                   "<th style='padding: 30px; width: 250px;'>Weather</th>"
                                   "<th style='padding: 30px; width: 150px;'>Humidity</th>"
                                   "<th style='padding: 30px; width: 200px;'>Wind Speed</th>"
                                   "<th style='padding: 30px; width: 250px;'>Precipitation</th>"
                                   "</tr></table>")
        layout.addWidget(self.header_label)

        self.forecast_text = QTextBrowser()
        self.forecast_text.setStyleSheet("""
            QTextBrowser {
                background-color: #1a1a1a;
                border: none;
                font-size: 18px;
            }
            QScrollBar:vertical {
                background-color: #1a1a1a;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #2C2C2C;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #1a1a1a;
            }
        """)

        # Use QScrollArea to contain the QTextBrowser
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.forecast_text)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #1a1a1a; }")

        # Add scroll_area to layout with stretch factor
        layout.addWidget(scroll_area, 1)  # The '1' sets the stretch factor

        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("margin-bottom: 20px;")
        layout.addWidget(self.icon_label)

        self.get_forecast()
    
    def get_api_key(self):
        api_key = WorldClockComparison.check_api_key()
        if not api_key:
            # Create a dialog to request API key
            api_key, ok = QInputDialog.getText(self, 'OpenWeather API Key Required', 'Please enter your API key:')
            if ok and api_key:
                # Save the key for future use
                with open('key.txt', 'w') as file:
                    file.write(api_key)
                return api_key
            return None
        return api_key
    
    def get_forecast(self):
        api_key = self.get_api_key()
        if not api_key:
            self.forecast_label.setText("Error loading forecast")
            self.forecast_text.setText("No API key provided")
            return
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={self.lat}&lon={self.lon}&appid={api_key}&units=metric"
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.forecast_label.setText("Error loading forecast")
                self.forecast_text.setText("Unauthorized API request. Please check your API key.")
            elif e.response.status_code == 400:
                self.forecast_label.setText("Error loading forecast")
                self.forecast_text.setText("Bad request. Please check the API request format.")
            else:
                self.forecast_label.setText("Error loading forecast")
                self.forecast_text.setText("API request failed: " + str(e))
            return
        except requests.exceptions.RequestException as e:
            self.forecast_label.setText("Error loading forecast")
            self.forecast_text.setText("API request failed: " + str(e))
            return

        try:
            data = response.json()
            if "list" in data:
                # Get the country name from the geopy library
                geolocator = Nominatim(user_agent="world_clock_comparison")
                location = geolocator.reverse((self.lat, self.lon))
                city_name = location.raw['address'].get('city', '')
                country_code = location.raw['address'].get('country_code', '')
                english_country_name = pycountry.countries.get(alpha_2=country_code).name if country_code else ''

                # Get the current time of the location
                tf = TimezoneFinder()
                timezone_str = tf.timezone_at(lng=self.lon, lat=self.lat)
                tz = pytz.timezone(timezone_str)
                current_time = datetime.now(tz)

                # Create a table to display the forecast data
                table = "<table style='font-size: 18px; line-height: 1.5; border-spacing: 15px;'>"
                for hour in data["list"]:
                    forecast_time = datetime.fromtimestamp(hour["dt"], tz)
                    if forecast_time > current_time:
                        temp_celsius = round(hour["main"]["temp"])
                        temp_fahrenheit = round((temp_celsius * 9/5) + 32)
                        weather_icon = self.get_weather_icon(hour["weather"][0]["icon"])

                        wind_speed = hour['wind']['speed']
                        wind_direction = hour['wind']['deg']
                        wind_direction_arrow = self.get_wind_direction_arrow(wind_direction)

                        precipitation_amount = hour.get('rain', {}).get('3h', 0)
                        precipitation_chance = round(hour.get('pop', 0) * 100)

                        table += "<tr>"
                        table += f"<td style='padding: 10px 30px 10px; width: 100px;'>{forecast_time.strftime('%H:%M')}</td>"
                        table += f"<td style='padding: 10px 30px 10px; width: 200px;'>{temp_celsius}°C ({temp_fahrenheit}°F)</td>"
                        table += f"<td style='padding: 10px 30px 10px; width: 250px;'><img src='{weather_icon}' width='48' height='48' style='vertical-align: middle; margin-right: 10px'>{hour['weather'][0]['description']. capitalize()}</td>"
                        table += f"<td style='padding: 10px 30px 10px; width: 150px;'>{hour['main']['humidity']}%</td>"
                        table += f"<td style='padding: 10px 30px 10px; width: 200px;'>{wind_speed} m/s {wind_direction_arrow}</td>"
                        table += f"<td style='padding: 10px 30px 10px; width: 250px;'>{precipitation_amount} mm ({precipitation_chance}%)</td>"
                        table += "</tr>"
                table += "</table>"

                self.forecast_label.setText(f"Weather forecast")
                self.forecast_text.setText(table)
            else:
                self.forecast_label.setText("Error loading forecast")
                self.forecast_text.setText("Invalid API response. Please check the API request format.")
        except Exception as e:
            self.forecast_label.setText("Error loading forecast")
            self.forecast_text.setText("Failed to parse API response: " + str(e))
            
    def get_location_name(self):
        geolocator = Nominatim(user_agent="world_clock_comparison")
        try:
            location = geolocator.reverse(f"{self.lat}, {self.lon}")
            address = location.raw['address']
            city = address.get('city', address.get('town', address.get('village', '')))
            country = address.get('country', '')
            if city and country:
                return f"{city}, {country}"
            elif country:
                return country
            else:
                return f"Lat: {self.lat}, Lon: {self.lon}"
        except Exception as e:
            print(f"Error getting location name: {e}")
            return f"Lat: {self.lat}, Lon: {self.lon}"

    def get_wind_direction_arrow(self, direction):
        if direction >= 337.5 or direction < 22.5:
            return "↑"  # North
        elif direction >= 22.5 and direction < 67.5:
            return "↗"  # North-East
        elif direction >= 67.5 and direction < 112.5:
            return "→"  # East
        elif direction >= 112.5 and direction < 157.5:
            return "↘"  # South-East
        elif direction >= 157.5 and direction < 202.5:
            return "↓"  # South
        elif direction >= 202.5 and direction < 247.5:
            return "↙"  # South-West
        elif direction >= 247.5 and direction < 292.5:
            return "←"  # West
        elif direction >= 292.5 and direction < 337.5:
            return "↖" # North-West
    
    def get_weather_icon(self, icon_code):
        # Map the icon code to a weather icon
        icon_map = {
            "01d": "icons/2682848_sunny_weather_forecast_day_sun.png",  # Sunny
            "01n": "icons/2682847_eclipse_forecast_moon_weather_night_space.png",  # Clear night
            "02d": "icons/2682849_sun_forecast_cloud_day_weather_cloudy.png",  # Partly cloudy
            "02n": "icons/2682846_cloud_cloudy_forecast_weather_night_moon.png",  # Partly cloudy night
            "03d": "icons/2682850_weather_clouds_cloud_cloudy_forecast.png",  # Cloudy
            "03n": "icons/2682846_cloud_cloudy_forecast_weather_night_moon.png",  # Cloudy night
            "04d": "icons/2682850_weather_clouds_cloud_cloudy_forecast.png",  # Overcast
            "04n": "icons/2682850_weather_clouds_cloud_cloudy_forecast.png",  # Overcast night
            "09d": "icons/2682845_cloud_weather_rain_sun_cloudy_forecast.png",  # Light rain
            "09n": "icons/2682843_weather_snow_rain_cloud_moon_night_forecast.png",  # Light rain night
            "10d": "icons/2682835_precipitation_weather_forecast_cloudy_rainy_cloud_rain.png",  # Rain
            "10n": "icons/2682833_weather_night_moon_precipitation_cloud_forecast_rain.png",  # Rain night
            "11d": "icons/2682828_thunder_cloud_light bolt_storm_weather_lightning_rain.png",  # Thunderstorm
            "11n": "icons/2682826_weather_rain_thunderstorm_light_night_bolt_moon.png",  # Thunderstorm night
            "13d": "icons/2682816_snowing_cloudy_forecast_weather_precipitation_cloud_snow.png",  # Snow
            "13n": "icons/2682814_snowing_snow_weather_night_precipitation_cloud_moon.png",  # Snow night
            "50d": "icons/2682821_weather_fog_forecast_mist_foggy.png",  # Fog
            "50n": "icons/2682801_mist_moon_cloudy_fog_weather_night_foggy.png",  # Fog night
        }
        return icon_map.get(icon_code, "❓")  # Return a default icon if the code is not found

class CountryShapeWidget(QLabel):
    world = None  # Define world attribute as a class variable

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.country_code = ""
        self.setStyleSheet("border-radius: 10px; background-color: #2C2C2C;")

    def update_country(self, country_code):
        if country_code != self.country_code:
            self.country_code = country_code
            country = pycountry.countries.get(alpha_2=country_code)
            country_name = country.name.replace(' ', '-').replace(',', '')            
            if country_name == "Taiwan, Province of China":
                country_name = "Taiwan"
            # print(f"regular name: {country_name}")

            # Try to download the image using the regular country name
            url = f"https://teuteuf-dashboard-assets.pages.dev/data/common/country-shapes/{country_code}.svg"
            flag_url = f"https://flagicons.lipis.dev/flags/4x3/{country_code}.svg"
            try:
                response = requests.get(url)
                flag_response = requests.get(flag_url)
                if response.status_code == 200 and flag_response.status_code == 200:
                    # If the regular country name works, use it
                    img_data = response.content
                    flag_img_data = flag_response.content
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    flag_pixmap = QPixmap()
                    flag_pixmap.loadFromData(flag_img_data)
                    self.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    self.flag_pixmap = flag_pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    pixmap.loadFromData(flag_img_data)
                    self.parent().flag_label.setPixmap(self.flag_pixmap)  # Set the flag pixmap to the flag_label
                    self.update()
                else:
                    print(f"Failed to download image for {country_code}. Status code: {response.status_code}")
                    self.clear()
            except Exception as e:
                print(f"Error updating shape for {country_code}: {e}")
                self.clear()
                
    def update_shape(self):
        if not self.country_code or self.world is None:
            self.clear()
            return

        # Get the country shape
        country = self.world[self.world['ISO_A2'] == self.country_code]
        
        if country.empty:
            self.clear()
            return

        # Create a figure and axis
        fig, ax = plt.subplots(figsize=(2, 2))
        
        # Plot the country shape
        country.plot(ax=ax, color='white', edgecolor='#8553ad')  # Change edgecolor to #8553ad
        
        # Remove axis and set tight layout
        ax.axis('off')
        plt.tight_layout()
        
        # Save the figure to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        
        # Create QPixmap from the buffer
        buf.seek(0)
        img = QImage.fromData(buf.getvalue())
        pixmap = QPixmap.fromImage(img)
        
        # Set the pixmap to the label
        self.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

class ClockWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setFixedSize(150, 150)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.location_abbr = ""
        self.country_code = ""
        self.setStyleSheet("border-radius: 10px; background-color: #2C2C2C;")
        self.time = None
        self.draw_static_elements()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_clock)
        self.update_timer.start(1000)  # Update every second

    def update_clock(self):
        if self.time:
            self.time = datetime.now(self.time.tzinfo)
            self.viewport().update()

    def update_time(self, time, location_abbr, country_code):
        self.time = time
        self.location_abbr = location_abbr
        self.country_code = country_code
        self.viewport().update()
    
    def draw_static_elements(self):
        bg_color = QColor("#2C2C2C")
        fg_color = QColor("#FFFFFF")
        
        # Draw clock face
        self.scene.addEllipse(QRectF(0, 0, 140, 140), QPen(fg_color), QBrush(bg_color))
        
        # Draw hour marks
        for i in range(12):
            angle = i * 30
            x1 = 70 + 65 * math.cos(math.radians(angle))
            y1 = 70 + 65 * math.sin(math.radians(angle))
            x2 = 70 + 60 * math.cos(math.radians(angle))
            y2 = 70 + 60 * math.sin(math.radians(angle))
            self.scene.addLine(x1, y1, x2, y2, QPen(fg_color))

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.time:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            fg_color = QColor("#FFFFFF")
            
            # Draw hands
            self.draw_hand(painter, self.time.hour % 12 * 30 + self.time.minute / 2, 40, 3, fg_color)  # Hour hand
            self.draw_hand(painter, self.time.minute * 6, 55, 2, QColor("#66B2FF"))  # Minute hand
            self.draw_hand(painter, self.time.second * 6, 60, 1, QColor("#FF6666"))  # Second hand

            # Add location abbreviation and flag
            painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            painter.setPen(fg_color)
            text = f"{self.location_abbr} {self.country_code}"
            text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def draw_hand(self, painter, angle, length, width, color):
        painter.save()
        painter.translate(75, 75)
        painter.rotate(angle)
        painter.setPen(QPen(color, width))
        painter.drawLine(0, 0, 0, -length)
        painter.restore()

class LocationSection(QFrame):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)  # Change to QHBoxLayout
        self.clock = ClockWidget()
        self.country_shape = CountryShapeWidget()
        self.flag_label = QLabel()  # Add a QLabel to display the flag
        self.flag_label.setFixedSize(50, 50)  # Set fixed size to 50x50
        self.info_label = QLabel()
        self.info_label.setFont(QFont("Arial", 14))  # Increase font size to 14
        self.info_label.setStyleSheet("color: #FFFFFF;")
        self.weather_layout = QHBoxLayout()  # Create a new layout for weather info
        self.weather_icon_label = QLabel()  # Create the weather icon label here
        self.weather_label = QLabel()
        self.weather_label.setFont(QFont("Arial", 14))  # Increase font size to 14
        self.weather_label.setStyleSheet("color: #FFFFFF;")
        self.weather_layout.addWidget(self.weather_icon_label)  # Add the weather icon label to the layout
        self.weather_layout.addWidget(self.weather_label)  # Add the weather label to the layout
        self.weather_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins from the weather layout
        self.weather_layout.setSpacing(5)  # Decrease spacing between weather icon and label
        self.layout.addWidget(self.clock)
        self.layout.addWidget(self.country_shape)
        self.layout.addWidget(self.flag_label)
        self.layout.addWidget(self.info_label)
        self.layout.addStretch()  # Add stretch to push weather info to the right
        self.layout.addLayout(self.weather_layout)  # Add the weather layout to the main layout
        self.layout.addSpacing(50)  # Add 10px of space to the right of the weather info
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet("QFrame { border-radius: 15px; background-color: #1E1E1E; }")
        self.layout.setContentsMargins(10, 10, 10, 10)  # Add margins to the layout
        self.layout.setSpacing(10)  # Add spacing between widgets

class WorldClockComparison(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("World Clock Comparison")
        self.setGeometry(100, 100, 1000, 600)
        icon = QIcon("Wclock.png")
        self.setWindowIcon(icon)
        self.setStyleSheet(""" 
            QMainWindow, QWidget { background-color: #121212; color: #FFFFFF; }
            QLineEdit, QPushButton, QListWidget { 
                font-size: 14px; 
                padding: 5px; 
                border-radius: 5px;
                background-color: #2C2C2C;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
            }
            QPushButton { 
                background-color: #0D47A1; 
                font-weight: bold; 
            }
            QPushButton:hover { background-color: #1565C0; }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background-color: #1E1E1E; }
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.api_key_button = QPushButton("Set API Key 🔑")
        self.api_key_button.clicked.connect(self.request_api_key) 

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Enter city name (e.g., 'London', 'New York', 'Tokyo')")
        self.add_button = QPushButton("Add Location")
        self.add_button.clicked.connect(self.add_location)
        self.location_input.returnPressed.connect(self.add_button.click)

        self.format_toggle = QPushButton("12/24 Hr")
        self.format_toggle.clicked.connect(self.toggle_time_format)
        self.use_24_hour = False
        

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.location_input)
        input_layout.addWidget(self.add_button)
        input_layout.addWidget(self.format_toggle)
        input_layout.addWidget(self.api_key_button)
        self.layout.addLayout(input_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.scroll_area)
        self.scroll_area.setStyleSheet("QScrollBar:vertical { width: 0px; } QScrollBar:horizontal { height: 0px; }")

        self.scroll_widget = QWidget()
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        self.locations = []
        self.location_sections = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_times)
        self.timer.start(1000)  # Update every second

        self.geolocator = Nominatim(user_agent="world_clock_comparison")
        self.tf = TimezoneFinder()
        
    
    
    @staticmethod
    def check_api_key():
        try:
            with open('key.txt', 'r') as file:
                api_key = file.read().strip()
                if api_key:
                    return api_key
        except FileNotFoundError:
            pass
        return None
    
    def request_api_key(self):
        api_key, ok = QInputDialog.getText(self, 'OpenWeather API Key Required', 'Please enter your API key:')
        if ok and api_key:
            # Save the key for future use
            with open('key.txt', 'w') as file:
                file.write(api_key)
            return api_key
        return None
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete and self.location_list.hasFocus():
            self.remove_location()
        else:
            super().keyPressEvent(event)

    def update_times(self):
        if not self.location_sections:
            return

        # Update all sections regardless of visibility
        for section in self.location_sections:
            city, timezone_str, lat, lon, country_code = section.location_info
            tz = pytz.timezone(timezone_str)
            current_time = datetime.now(tz)
            section.clock.update_time(current_time, city[:3].upper(), country_code)
            section.country_shape.update_country(country_code)

        # Update other UI elements every 10 seconds
        if datetime.now().second % 10 == 0:
            for i, section in enumerate(self.location_sections):
                city, _, _, _, country_code = section.location_info
                country = pycountry.countries.get(alpha_2=country_code)
                if country:
                    country_name = country.name
                    if country_name == "Taiwan, Province of China":
                        country_name = "Taiwan"
                else:
                    country_name = ''

                time_format = "%Y-%m-%d %H:%M" if self.use_24_hour else "%Y-%m-%d %I:%M %p"
                time_str = datetime.now(pytz.timezone(section.location_info[1])).strftime(time_format)
                info_text = f"{city} ({section.location_info[1].split('/')[0]}, {country_name})\n{time_str}"

                if i > 0:
                    prev_city, prev_tz, _, _, _ = self.location_sections[i-1].location_info
                    prev_time = datetime.now(pytz.timezone(prev_tz))
                    current_time = datetime.now(pytz.timezone(section.location_info[1]))
                    offset1 = prev_time.utcoffset().total_seconds() / 3600
                    offset2 = current_time.utcoffset().total_seconds() / 3600
                    time_diff = offset2 - offset1
                    hours, minutes = divmod(abs(time_diff), 1)
                    hours = int(hours)
                    minutes = int(minutes * 60)
                    direction = "ahead of" if time_diff > 0 else "behind"
                    diff_str = f"{hours}h {minutes}m {direction} {prev_city}"
                    info_text += f"\nΔ {diff_str}"

                section.info_label.setText(info_text)
                self.update_weather(section, section.location_info[2], section.location_info[3])

    def update_weather(self, section, lat, lon):
        api_key = self.check_api_key()
        if not api_key:
            api_key = self.request_api_key()
            if not api_key:
                section.weather_label.setText("No API key provided")
                return
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                section.weather_label.setText("Error loading weather")
            elif e.response.status_code == 400:
                section.weather_label.setText("Bad request. Please check the API request format.")
            else:
                section.weather_label.setText("API request failed: " + str(e))
            return
        except requests.exceptions.RequestException as e:
            section.weather_label.setText("API request failed: " + str(e))
            return

        try:
            data = response.json()
            if "weather" in data and "main" in data and "wind" in data:
                weather_icon = self.get_weather_icon(data["weather"][0]["icon"])
                weather_icon_pixmap = QPixmap(weather_icon)
                weather_icon_pixmap = weather_icon_pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio)  # Increase icon size
                section.weather_icon_label.setPixmap(weather_icon_pixmap)  # Update the weather icon label

                temp_celsius = data['main']['temp']
                temp_fahrenheit = round((temp_celsius * 9/5) + 32)
                weather_text = f"{temp_celsius}°C ({temp_fahrenheit}°F)\nWind: {data['wind']['speed']}m/s\nHumidity: {data['main']['humidity']}%"
                section.weather_label.setText(weather_text)
            else:
                section.weather_label.setText("Error loading weather")
        except Exception as e:
            section.weather_label.setText("Error loading weather: " + str(e))
            
    def get_weather_icon(self, icon_code):
        # Map the icon code to a weather icon
        icon_map = {
            "01d": "icons/2682848_sunny_weather_forecast_day_sun.png",  # Sunny
            "01n": "icons/2682847_eclipse_forecast_moon_weather_night_space.png",  # Clear night
            "02d": "icons/2682849_sun_forecast_cloud_day_weather_cloudy.png",  # Partly cloudy
            "02n": "icons/2682846_cloud_cloudy_forecast_weather_night_moon.png",  # Partly cloudy night
            "03d": "icons/2682850_weather_clouds_cloud_cloudy_forecast.png",  # Cloudy
            "03n": "icons/2682846_cloud_cloudy_forecast_weather_night_moon.png",  # Cloudy night
            "04d": "icons/2682850_weather_clouds_cloud_cloudy_forecast.png",  # Overcast
            "04n": "icons/2682850_weather_clouds_cloud_cloudy_forecast.png",  # Overcast night
            "09d": "icons/2682845_cloud_weather_rain_sun_cloudy_forecast.png",  # Light rain
            "09n": "icons/2682843_weather_snow_rain_cloud_moon_night_forecast.png",  # Light rain night
            "10d": "icons/2682835_precipitation_weather_forecast_cloudy_rainy_cloud_rain.png",  # Rain
            "10n": "icons/2682833_weather_night_moon_precipitation_cloud_forecast_rain.png",  # Rain night
            "11d": "icons/2682828_thunder_cloud_light bolt_storm_weather_lightning_rain.png",  # Thunderstorm
            "11n": "icons/2682826_weather_rain_thunderstorm_light_night_bolt_moon.png",  # Thunderstorm night
            "13d": "icons/2682816_snowing_cloudy_forecast_weather_precipitation_cloud_snow.png",  # Snow
            "13n": "icons/2682814_snowing_snow_weather_night_precipitation_cloud_moon.png",  # Snow night
            "50d": "icons/2682821_weather_fog_forecast_mist_foggy.png",  # Fog
            "50n": "icons/2682801_mist_moon_cloudy_fog_weather_night_foggy.png",  # Fog night
        }
        return icon_map.get(icon_code, "❓")  # Return a default icon if the code is not found

    def toggle_time_format(self):
        self.use_24_hour = not self.use_24_hour
        self.format_toggle.setText("12 hr" if self.use_24_hour else "24 hr")
        self.update_times()

    def add_location(self):
        city = self.location_input.text().strip().capitalize()
        if city:
            try:
                location = self.geolocator.geocode(city)
                if location:
                    timezone_str = self.tf.timezone_at(lng=location.longitude, lat=location.latitude)
                    if timezone_str:
                        country = self.geolocator.reverse((location.latitude, location.longitude)).raw['address']['country_code']
                        country_code = country if country else ''
                        section = LocationSection()
                        section.location_info = (city, timezone_str, location.latitude, location.longitude, country_code)
                        self.location_sections.append(section)
                        self.scroll_layout.addWidget(section)
                        self.location_input.clear()
                    else:
                        self.show_error(f"Could not determine timezone for {city}")
                else:
                    self.show_error(f"Could not find location: {city}")
            except Exception as e:
                self.show_error(f"Error adding location: {str(e)}")

    def remove_location(self, section=None):
        if section is None:
            for section in self.location_sections:
                if section.hasFocus():
                    self.location_sections.remove(section)
                    self.scroll_layout.removeWidget(section)
                    section.deleteLater()
                    self.update_times()
                    break
        else:
            self.location_sections.remove(section)
            self.scroll_layout.removeWidget(section)
            section.deleteLater()
        self.update_times()

    def update_location_order(self):
        for i, section in enumerate(self.location_sections):
            self.clocks_layout.removeWidget(section)
            self.clocks_layout.insertWidget(i, section)
        self.update_times()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            for section in self.location_sections:
                if section.underMouse():
                    # print("Section under mouse:", section)
                    # print("Section location_info:", section.location_info)
                    city, timezone_str, lat, lon, country_code = section.location_info
                    # print(f"Unpacked values - City: {city}, Timezone: {timezone_str}, Lat: {lat}, Lon: {lon}, Country Code: {country_code}")
                    country = pycountry.countries.get(alpha_2=country_code)
                    if country:
                        country_name = country.name
                        if country_name == "Taiwan, Province of China":
                            country_name = "Taiwan"
                    else:
                        country_name = "Unknown"
                    # print(f"Country name: {country_name}")
                    self.forecast_window = ForecastWindow(section.location_info)  # Pass the entire tuple
                    self.forecast_window.setWindowTitle(f"{city}, {country_name}")
                    self.forecast_window.show()
                    break
        if event.button() == Qt.MouseButton.RightButton:
            for section in self.location_sections:
                if section.underMouse():
                    self.remove_location(section)
                    break
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for section in self.location_sections:
                if section.hasFocus():
                    self.remove_location(section)
                    break
        else:
            super().keyPressEvent(event)

    def show_error(self, message):
        error_label = QLabel(message)
        error_label.setStyleSheet("color: #FF6666; font-size: 14px; font-weight: bold;")
        self.layout.addWidget(error_label)
        QTimer.singleShot(3000, error_label.deleteLater)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WorldClockComparison()
    window.show()
    sys.exit(app.exec())