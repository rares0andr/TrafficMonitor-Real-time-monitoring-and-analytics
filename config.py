# Configurare Comună
# Acest fișier conține setările utilizate atât de serverul API cât și de procesorul de trafic.

#VIDEO_SOURCE = "https://www.youtube.com/watch?v=1EiC9bvVGnk" # Jackson Hole
VIDEO_SOURCE = "https://s9.nysdot.skyvdn.com/rtplive/R11_229/chunklist_w794785557.m3u8"

LOCATION_NAME = "I-278 at Adams Street"
# ^ NOTĂ: Modifică acest nume pentru a actualiza titlul de pe Dashboard.

API_ENDPOINT = "http://127.0.0.1:5000/api/raport"
INTERVAL_RAPORTARE = 60
TIMEZONE = 'America/New_York' 
# ^ Timezone-ul camerei (ex: 'Europe/Bucharest', 'America/New_York').
