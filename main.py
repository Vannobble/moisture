# main.py
# ESP32 Publisher: Soil Moisture Sensor + ASCON Encryption + MQTT
# MicroPython

from machine import Pin, I2C, ADC
from time import sleep
import json
from i2c_lcd import I2cLcd
import ascon # Pastikan ini adalah pustaka ASCON yang kompatibel
import network
from umqtt.simple import MQTTClient
import binascii # Digunakan untuk konversi bytes ke hex string

# --- KONFIGURASI WiFi ---
WIFI_SSID = "Redmi Note 10 Pro"
WIFI_PASSWORD = "dosson123"

# --- KONFIGURASI MQTT ---
MQTT_CLIENT_ID = "micropython-soil-demo"
MQTT_BROKER = "broker.hivemq.com"
MQTT_USER = ""
MQTT_PASSWORD = ""
MQTT_TOPIC = "soil-ascon128"

# --- KONFIGURASI SENSOR ---
SENSOR_PIN = 34
adc = ADC(Pin(SENSOR_PIN))
adc.width(ADC.WIDTH_12BIT)
adc.atten(ADC.ATTN_11DB)

# --- NILAI KALIBRASI SENSOR ---
DRY_VALUE = 2650
WET_VALUE = 1200

# --- KONFIGURASI KRIPTOGRAFI ASCON ---
# KEY, NONCE, dan AD harus sama persis dengan sisi penerima (JS/TS).
KEY = b"asconciphertest1"      # 16 bytes (Kunci statis)
NONCE = b"asconcipher1test"     # 16 bytes (Nonce statis - HANYA untuk demo! Nonce harus acak dan unik dalam aplikasi riil!)
ASSOCIATED_DATA = b"ASCON"
VARIANT = "Ascon-128"

# --- KONFIGURASI LCD ---
I2C_ADDR = 0x27
i2c = I2C(1, scl=Pin(22), sda=Pin(21), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, 16, 2)

# --- VARIABEL GLOBAL ---
mqtt_client = None

# ----------------------------------------------------
## 🔑 Helper: ASCON Encrypt (Mengikuti cara kode kedua)
# ----------------------------------------------------
def ascon_encrypt_value(moisture_value):
    """
    Mengikuti cara enkripsi kode kedua:
    - Konversi nilai integer ke bytes
    - Gunakan demo_aead_c untuk enkripsi
    - Return hex string ciphertext+tag saja (tanpa nonce)
    """
    try:
        # Konversi moisture value ke bytes (seperti kode kedua)
        payload_bytes = moisture_value.to_bytes(1, 'big')
        
        # Gunakan demo_aead_c seperti kode kedua
        encrypted_data = ascon.demo_aead_c(
            VARIANT,
            payload_bytes,
            k=KEY,
            n=NONCE,
            a=ASSOCIATED_DATA
        )
        
        # Konversi ke hex string (hanya ciphertext+tag, tanpa nonce)
        payload_hex = binascii.hexlify(encrypted_data).decode('utf-8')
        
        print("📦 Encrypted Payload Structure (Kode Kedua Style):")
        print("    Moisture Value: {}% -> Bytes: {}".format(moisture_value, payload_bytes))
        print("    Hex(CT||Tag): {} ({} chars)".format(payload_hex, len(payload_hex)))
        
        return payload_hex
        
    except Exception as e:
        print("❌ ASCON Encryption error:", e)
        return "ERROR"

# ----------------------------------------------------
## 📡 WiFi / MQTT / Sensor Utils
# ----------------------------------------------------
def connect_wifi():
    """Connect to WiFi network."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print('Connecting to WiFi...')
        lcd.clear()
        lcd.print("Connecting WiFi")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            sleep(1)
            timeout -= 1
            print('.', end='')

    if wlan.isconnected():
        print('\nWiFi connected!')
        print('Network config:', wlan.ifconfig())
        lcd.clear()
        lcd.print("WiFi Connected")
        return True
    else:
        print('\nWiFi connection failed!')
        lcd.clear()
        lcd.print("WiFi Failed")
        return False

def connect_mqtt():
    """Connect to MQTT broker."""
    global mqtt_client

    try:
        print("Connecting to MQTT...")
        lcd.clear()
        lcd.print("MQTT Connecting")

        mqtt_client = MQTTClient(
            client_id=MQTT_CLIENT_ID,
            server=MQTT_BROKER,
            user=MQTT_USER,
            password=MQTT_PASSWORD
        )

        mqtt_client.connect()
        print("Connected to MQTT broker!")
        lcd.clear()
        lcd.print("MQTT Connected")
        sleep(1)
        return True

    except Exception as e:
        print("MQTT connection failed:", e)
        lcd.clear()
        lcd.print("MQTT Error")
        sleep(2)
        return False

def map_value(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def get_moisture_percentage(raw_adc):
    """Menghitung persentase kelembaban sebagai integer."""
    percentage = map_value(raw_adc, DRY_VALUE, WET_VALUE, 0, 100)
    return max(0, min(100, int(percentage)))

def publish_sensor_data(moisture_value, encrypted_hex):
    """Publish sensor data ke MQTT broker - format seperti kode kedua."""
    global mqtt_client

    try:
        # Format JSON seperti kode kedua
        message = json.dumps({
            "data": encrypted_hex,  # Key diubah menjadi "data" seperti kode kedua
            "sensor": "soil_moisture",
            "unit": "%"
        })

        mqtt_client.publish(MQTT_TOPIC, message.encode('utf-8'))
        print("Published to {}: {}% -> {}".format(MQTT_TOPIC, moisture_value, encrypted_hex))
        
        return True

    except Exception as e:
        print("MQTT Publish error:", e)
        # Coba sambungkan ulang
        try:
            connect_mqtt()
        except:
            pass
        return False

def display_lcd(moisture_value, encrypted_hex):
    """Display data on LCD - disesuaikan dengan payload yang lebih pendek."""
    # Ambil 16 karakter pertama dari ciphertext (karena sekarang lebih pendek)
    cipher_part = encrypted_hex[:16] 

    float_line = "ASLI: {}%".format(moisture_value)
    cipher_line = "CT:{}".format(cipher_part)

    lcd.clear()
    lcd.goto(0, 0)
    lcd.print(float_line)
    lcd.goto(0, 1)
    lcd.print(cipher_line)

# ----------------------------------------------------
## 🏁 PROGRAM UTAMA
# ----------------------------------------------------
def main():
    # Initialize LCD
    lcd.backlight_on()
    lcd.clear()
    lcd.print("ASCON MONITOR")
    sleep(2)

    # Connect to WiFi
    wifi_ok = connect_wifi()
    if not wifi_ok:
        lcd.clear()
        lcd.print("WiFi Failed")
        lcd.goto(0, 1)
        lcd.print("Local Mode Only")
        sleep(2)

    # Connect to MQTT (try but continue if fails)
    mqtt_connected = connect_mqtt()

    # Main loop
    try:
        while True:
            raw_adc = adc.read()
            moisture_value = get_moisture_percentage(raw_adc)

            # Encrypt value menggunakan cara kode kedua
            encrypted_hex = ascon_encrypt_value(moisture_value)

            # Display on LCD
            display_lcd(moisture_value, encrypted_hex)

            # Publish to MQTT if connected
            if mqtt_connected and mqtt_client is not None:
                publish_sensor_data(moisture_value, encrypted_hex)
            else:
                print("Local: {}% -> {}...".format(moisture_value, encrypted_hex[:20]))

            sleep(3)

    except KeyboardInterrupt:
        print("Program stopped by user")

    except Exception as e:
        print("Main loop error:", e)
        lcd.clear()
        lcd.print("System Error")

    finally:
        if mqtt_client is not None:
            try:
                mqtt_client.disconnect()
            except:
                pass
        lcd.clear()
        lcd.backlight_off()

if __name__ == "__main__":
    main()
