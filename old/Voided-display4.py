from luma.core.interface.serial import spi
from luma.lcd.device import pcd8544
from PIL import Image, ImageDraw, ImageFont

# Konfigurer SPI og koblinger
serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)

# Initialiser skjermen
device = pcd8544(serial)

# Lag et nytt bilde
img = Image.new("1", (device.width, device.height))
draw = ImageDraw.Draw(img)

# Tegn tekst på skjermen
draw.text((10, 10), "Hello, GASSO!", fill=255)

# Vis bildet på skjermen
device.display(img)
