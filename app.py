# app.py
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import json
import threading
import time
import binascii
import logging
from datetime import datetime

# --- KONFIGURASI KRIPTOGRAFI ---
import ascon  # Pastikan ascon.py ada

KEY = b"asconciphertest1"
NONCE = b"asconcipher1test"
ASSOCIATED_DATA = b"ASCON"
VARIANT = "Ascon-128"

# --- KONFIGURASI MQTT ---
MQTT_CLIENT_ID = f"web-dashboard-subscriber-{int(time.time())}"
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "soil-ascon128"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# --- KONFIGURASI FLASK & SOCKET.IO ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'kunci_rahasia_anda'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# --- SETUP LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- VARIABEL GLOBAL ---
connected_clients = 0
last_data = None

# --- FUNGSI DEKRIPSI ---
def ascon_decrypt_payload(encrypted_hex_string):
    """
    Mendekripsi payload yang diterima dari MQTT
    """
    try:
        encrypted_bytes = binascii.unhexlify(encrypted_hex_string)
        
        # Panggil fungsi dekripsi dari pustaka ASCON
        decrypted_bytes = ascon.demo_aead_p(VARIANT, encrypted_bytes)

        if decrypted_bytes:
            moisture_value = int.from_bytes(decrypted_bytes, 'big')
            
            # Tentukan status berdasarkan nilai kelembaban
            if moisture_value < 20:
                status_text = "CRITICAL: SANGAT KERING"
                status_level = "critical"
            elif moisture_value < 40:
                status_text = "WARNING: KERING"
                status_level = "warning"
            elif moisture_value < 70:
                status_text = "OPTIMAL"
                status_level = "optimal"
            else:
                status_text = "WARNING: TERLALU BASAH"
                status_level = "warning"
            
            return {
                "status": "success", 
                "value": moisture_value, 
                "verification": "TAG_MATCH",
                "status_text": status_text,
                "status_level": status_level,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        else:
            return {
                "status": "error", 
                "message": "Gagal Dekripsi/Tag Mismatch", 
                "verification": "TAG_MISMATCH",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

    except Exception as e:
        logger.error(f"Error dalam dekripsi: {e}")
        return {
            "status": "error", 
            "message": f"Error Dekripsi: {e}", 
            "verification": "PROCESS_FAIL",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    """
    Callback ketika terhubung ke broker MQTT
    """
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        logger.info(f"✅ MQTT Connected & Subscribed to {MQTT_TOPIC}")
        # Kirim status koneksi ke semua klien web
        socketio.emit('mqtt_status', {'status': 'connected', 'topic': MQTT_TOPIC})
    else:
        error_codes = {
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorised"
        }
        error_msg = error_codes.get(rc, f"Unknown error code: {rc}")
        logger.error(f"❌ MQTT Connection failed: {error_msg}")
        socketio.emit('mqtt_status', {'status': 'disconnected', 'error': error_msg})

def on_disconnect(client, userdata, rc):
    """
    Callback ketika terputus dari broker MQTT
    """
    logger.warning("⚠️ MQTT Disconnected")
    socketio.emit('mqtt_status', {'status': 'disconnected'})

def on_message(client, userdata, msg):
    """
    Callback ketika menerima pesan MQTT
    """
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        encrypted_hex = data['data']
        
        logger.info(f"📨 Received MQTT message, length: {len(encrypted_hex)}")
        
        # Panggil fungsi dekripsi
        result = ascon_decrypt_payload(encrypted_hex)
        
        # Simpan data terakhir
        global last_data
        last_data = result
        
        # Kirim hasil dekripsi ke SEMUA klien web melalui SocketIO
        socketio.emit('new_data', result)
        logger.info(f"✅ Data decrypted and sent to clients: {result.get('value', 'N/A')}")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
    except KeyError as e:
        logger.error(f"❌ Missing key in payload: {e}")
    except Exception as e:
        logger.error(f"❌ Error processing MQTT payload: {e}")

# --- MQTT CLIENT MANAGEMENT ---
def create_mqtt_client():
    """
    Membuat dan mengkonfigurasi client MQTT
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Konfigurasi tambahan
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    return client

def start_mqtt_client():
    """
    Menjalankan client MQTT dalam thread terpisah
    """
    mqtt_client = create_mqtt_client()
    
    while True:
        try:
            logger.info(f"🔗 Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            mqtt_client.loop_forever()
            
        except Exception as e:
            logger.error(f"❌ MQTT connection failed: {e}")
            logger.info("🔄 Attempting to reconnect in 10 seconds...")
            time.sleep(10)

# --- FLASK ROUTES ---
@app.route('/')
def index():
    """Route utama untuk dashboard"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Endpoint untuk health check"""
    return {
        "status": "healthy",
        "service": "Soil Moisture Dashboard",
        "timestamp": datetime.now().isoformat(),
        "connected_clients": connected_clients
    }

# --- SOCKET.IO EVENT HANDLERS ---
@socketio.on('connect')
def handle_connect():
    """Handle koneksi client Socket.IO"""
    global connected_clients
    connected_clients += 1
    logger.info(f'🔌 Client connected. Total clients: {connected_clients}')
    
    # Kirim data terakhir jika ada
    if last_data:
        emit('last_data', last_data)
    
    emit('connection_ack', {
        'message': 'Connected to server',
        'clients_count': connected_clients
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle disconnect client Socket.IO"""
    global connected_clients
    connected_clients -= 1
    logger.info(f'🔌 Client disconnected. Total clients: {connected_clients}')

@socketio.on('request_status')
def handle_status_request():
    """Handle request status dari client"""
    emit('system_status', {
        'connected_clients': connected_clients,
        'mqtt_topic': MQTT_TOPIC,
        'last_update': last_data.get('timestamp') if last_data else None
    })

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    try:
        # Jalankan MQTT di thread terpisah
        mqtt_thread = threading.Thread(target=start_mqtt_client)
        mqtt_thread.daemon = True
        mqtt_thread.start()
        
        logger.info("🚀 Starting Flask Server with Socket.IO...")
        logger.info("📊 Soil Moisture Monitoring Dashboard is running!")
        logger.info(f"🌐 Access the dashboard at: http://localhost:5000")
        
        # Jalankan SocketIO server
        socketio.run(
            app, 
            debug=True, 
            port=5000, 
            host='0.0.0.0',
            allow_unsafe_werkzeug=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"💥 Server error: {e}")