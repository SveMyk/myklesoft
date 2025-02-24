import time
import spidev
import RPi.GPIO as GPIO
from luma.lcd.device import pcd8544
from luma.core.interface.serial import spi
from luma.core.render import canvas
from PIL import ImageFont

# Sett GPIO nummereringsmodus
GPIO.setmode(GPIO.BCM)  
GPIO.setwarnings(False)  # For å unngå advarsler

# Sett opp pinner
RST = 17  # GPIO 17
CE = 8    # SPI CE0
DC = 25   # GPIO 25

# Initialiser SPI
serial = spi(port=0, device=0, gpio=GPIO, gpio_DC=DC, gpio_RST=RST)
lcd = pcd8544(serial, rotate=0)

# Sett kontrast og klar skjermen
lcd.contrast(60)
lcd.clear()

# Bruk standard font
font = ImageFont.load_default()

# Tegn testtekst
with canvas(lcd) as draw:
    draw.text((10, 20), "Test!", font=font, fill=255)

print("Testmelding sendt til skjermen.")
time.sleep(5)
