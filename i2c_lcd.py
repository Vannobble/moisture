# i2c_lcd.py
# Modul driver LCD 16x2 I2C yang lebih sederhana dan teruji untuk MicroPython

from machine import I2C, Pin
from time import sleep_us, sleep

# Alamat default (Ganti ini jika alamat I2C Anda berbeda)
DEFAULT_ADDR = 0x27

# Konstanta LCD
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_FUNCTIONSET = 0x20
LCD_SETDDRAMADDR = 0x80

# Bendera Kontrol Display
LCD_DISPLAYON = 0x04
LCD_CURSOROFF = 0x00
LCD_BLINKOFF = 0x00

# Bendera Mode Entry
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTDECREMENT = 0x00

# Bendera Pin PCF8574
EN = 0b00000100  # Enable bit
RW = 0b00000010  # Read/Write bit (selalu 0 untuk menulis)
RS = 0b00000001  # Register select bit

class I2cLcd:
    def __init__(self, i2c, addr=DEFAULT_ADDR, cols=16, rows=2, backlight_on=True):
        self.i2c = i2c
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self.backlight = 0b00001000 if backlight_on else 0x00
        
        # Urutan Inisialisasi (4-bit mode)
        self.write_byte(0x03)
        self.write_byte(0x03)
        self.write_byte(0x03)
        self.write_byte(0x02)

        # Function Set: 4-bit mode, 2 baris, font 5x8
        self.command(LCD_FUNCTIONSET | 0x08)
        # Display Control: Display ON, Cursor OFF, Blink OFF
        self.display_control = LCD_DISPLAYCONTROL | LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF
        self.command(self.display_control)
        # Clear Display
        self.command(LCD_CLEARDISPLAY)
        sleep(0.002) # Jeda diperlukan setelah clear
        # Entry Mode Set: Increment kursor, No shift
        self.command(LCD_ENTRYMODESET | LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT)
        self.home()

    def write_byte(self, data):
        """Menulis 4-bit data ke LCD"""
        self.i2c.writeto(self.addr, bytes([data | self.backlight]))
        self.i2c.writeto(self.addr, bytes([data | self.backlight | EN])) # Pulsa EN High
        sleep_us(1)
        self.i2c.writeto(self.addr, bytes([data | self.backlight])) # Pulsa EN Low
        sleep_us(50)

    def command(self, cmd):
        """Mengirim perintah ke LCD (RS=0)"""
        # Upper nibble
        self.write_byte((cmd & 0xF0))
        # Lower nibble
        self.write_byte((cmd << 4) & 0xF0)

    def write_data(self, data):
        """Mengirim data karakter ke LCD (RS=1)"""
        # Upper nibble
        self.write_byte((data & 0xF0) | RS)
        # Lower nibble
        self.write_byte(((data << 4) & 0xF0) | RS)

    def home(self):
        self.command(LCD_RETURNHOME)
        sleep(0.002)

    def clear(self):
        self.command(LCD_CLEARDISPLAY)
        sleep(0.002)

    def goto(self, col, row):
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        # Pastikan baris dalam batas
        if row >= self.rows:
            row = self.rows - 1
        self.command(LCD_SETDDRAMADDR | (col + row_offsets[row]))

    def print(self, string):
        for char in string:
            self.write_data(ord(char))
            
    def backlight_on(self):
        self.backlight = 0b00001000
        self.command(0x00) # Perintah dummy untuk update backlight

    def backlight_off(self):
        self.backlight = 0x00
        self.command(0x00) # Perintah dummy untuk update backlight
