# 🌱 Soil Moisture Dashboard (Ascon-128 Encrypted MQTT)

Dashboard ini digunakan untuk menampilkan data soil moisture yang dikirim melalui protokol MQTT dalam bentuk **payload terenkripsi ASCON-128**.  
Server Flask akan menerima payload dari broker MQTT → menampilkan **raw data (payload asli)** → mendekripsi → lalu mengirimkan data ke dashboard web melalui **Socket.IO**.

🌐 **Akses Dashboard Online**: [https://moisture-display.up.railway.app/](https://moisture-display.up.railway.app/)

---

## 🚀 Features

- 🔒 Dekripsi payload sensor menggunakan **ASCON-128 AEAD**
- 📡 Subscriber MQTT otomatis (HiveMQ public broker)
- 🔗 Real-time update menggunakan **Flask-SocketIO**
- 🌐 Dashboard web dengan auto-refresh data
- 🧩 Menampilkan **raw payload sebelum didekripsi**
- 📝 Log lengkap untuk debugging
- ☁️ **Deployed online** via Railway

---

## 📁 Struktur Proyek

```
.
├── app.py                 # Server utama Flask + MQTT + Socket.IO
├── ascon.py               # Implementasi Ascon (AEAD)
├── requirements.txt       # Dependency Python
├── runtime.txt           # Python version specification
└── templates/
    └── index.html         # Dashboard utama
```

---

## 📦 Dependencies

Project ini menggunakan Python **3.8 atau lebih baru**.

**requirements.txt**:
```txt
flask==2.3.3
flask-socketio==5.3.6
paho-mqtt==1.6.1
eventlet==0.33.3
ascon==0.2.0
gunicorn==21.2.0
```

---

## 🌐 Akses Dashboard

**Dashboard sudah tersedia online** di:
```arduino
https://moisture-display.up.railway.app/
```

Dashboard akan otomatis menerima:
- **raw MQTT payload** (raw_data)
- **hasil dekripsi** (new_data)
- **status koneksi** daemon MQTT

---

## 📡 Format Data MQTT

Payload yang dikirim oleh device HARUS berupa JSON:

```json
{
    "id": 13,
    "data": "fba1637956fc9c27af8e3d89ad7032b4dbfc0123456789abcdef"
}
```

Field `data` adalah ciphertext + tag dalam bentuk hex (minimal 32 karakter).

---

## 🔓 Proses Dekripsi

Pada penerimaan pesan MQTT:

1. **Menampilkan raw payload**:
```python
socketio.emit('raw_data', {"raw_payload": payload_str})
```

2. **Mendekripsi**:
```python
result = ascon_decrypt_payload(encrypted_hex)
```

3. **Mengirim ke front-end**:
```python
socketio.emit('new_data', result)
```

---

## 🧪 Testing MQTT

Gunakan MQTT client untuk mengirim data test:

**Topic**: `soil-ascon128`  
**Broker**: `broker.hivemq.com`  
**Port**: `1883`

**Contoh payload test**:
```json
{
    "id": 1,
    "data": "0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

Dashboard online akan langsung menampilkan **RAW PAYLOAD** dan hasil dekripsi.

---

## 🛠 Troubleshooting

### ❌ Tidak menerima data?
- Pastikan topic MQTT sesuai: `soil-ascon128`
- Periksa koneksi internet device
- Pastikan payload dalam format JSON valid
- Cek broker HiveMQ status

### ❌ Dekripsi gagal?
- Kunci Ascon harus sama antara device dan server
- Pastikan ciphertext + tag lengkap (minimal 32 karakter hex)
- Format hex harus valid

### ❌ Dashboard tidak bisa diakses?
- Cek status deployment di [Railway](https://railway.app)
- Refresh browser dan clear cache
- Pastikan menggunakan HTTPS

### ❌ Socket.IO connection error?
- Pastikan browser mendukung WebSocket
- Cek browser console untuk error detail
- Refresh halaman

---

## ⚙️ Konfigurasi Server

### Kunci ASCON-128
Kunci enkripsi/dekripsi yang digunakan server:

```python
ASCON_KEY = b'0123456789abcdef'  # 16 bytes untuk ASCON-128
ASCON_NONCE = b'0123456789abcdef'  # 16 bytes nonce
```

### MQTT Configuration
- **Topic**: `soil-ascon128`
- **Broker**: `broker.hivemq.com`
- **Port**: `1883`
- **Protocol**: MQTT v3.1.1

---

## 📊 Format Data Hasil Dekripsi

Setelah berhasil didekripsi, data akan berformat:

```json
{
    "sensor_id": 1,
    "soil_moisture": 65.5,
    "temperature": 28.3,
    "humidity": 75.2,
    "timestamp": "2024-01-15T10:30:00Z",
    "battery": 85.0
}
```

---

## 🚀 Deployment

Project ini di-deploy menggunakan **Railway**. Untuk deployment serupa:

1. Connect repository ke Railway
2. Set environment variables jika diperlukan
3. Deploy otomatis dari main branch

---

## 📝 Lisensi

Proyek ini bebas digunakan untuk pembelajaran, riset, atau integrasi IoT pribadi.

---

## 👤 Author

**Doshansel Sihombing**  
Universitas Brawijaya — Computer Engineering

---

<div align="center">
  
**🌐 Akses Dashboard: [https://moisture-display.up.railway.app/](https://moisture-display.up.railway.app/)**

**⭐ Jangan lupa beri star jika project ini membantu! ⭐**

</div>
