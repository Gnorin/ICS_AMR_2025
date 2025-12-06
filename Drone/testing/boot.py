import network

wlan = network.WLAN()                   # create station interface (the default, see below for an access point interface)
wlan.active(True)                       # activate the interface
wlan.scan()                             # scan for access points
wlan.isconnected()                      # check if the station is connected to an AP
wlan.connect('Pixel 7 FH', '1a2b3c4d')  # connect to an AP
wlan.ipconfig('addr4')                  # get the interface's IPv4 addresses

ap = network.WLAN(network.WLAN.IF_AP)   # create access-point interface
ap.config(ssid='ESP-AP')                # set the SSID of the access point
ap.config(max_clients=10)               # set how many clients can connect to the network
ap.active(True)                         # activate the interface