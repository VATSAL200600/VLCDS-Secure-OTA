import urllib.request
import re

url = "https://micropython.org/download/ESP32_GENERIC_S2/"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
bins = re.findall(r'href="([^"]+\.bin)"', html)
print("Found binaries:")
for b in bins[:5]:
    print(" ", b)

# Download the latest stable
if bins:
    bin_url = bins[0]
    if not bin_url.startswith("http"):
        bin_url = "https://micropython.org" + bin_url
    print("Downloading:", bin_url)
    urllib.request.urlretrieve(bin_url, "d:/PROJECTS/CRY/esp32/micropython_esp32s2.bin")
    print("Downloaded successfully to d:/PROJECTS/CRY/esp32/micropython_esp32s2.bin")
