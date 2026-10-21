import socket
import json
import os
import time
import deler

#kommunikasjon=============================
HOST = "0.0.0.0"
START_PORT = 5000

ROBOT_IP = "10.0.12.101"
LISTEN_PORT = 5890

#Variabler
x_mm = 0.0
y_mm = 0.0
rotasjon = 0
ID = ""

ROBOT_CELL_MM = 60

net_start = False
ok = False

#==========================================
#INITATE FASEN=============================
#==========================================

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

server.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)

server.bind((HOST, START_PORT))

server.listen(1)
print("venter på tilkobling til robot...")

connection, address = server.accept()
print(f"Robot tilkoblet fra{address}")

#INITIATE - KOBLE TIL LISTEN====================

listen_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

listen_socket.settimeout(10)

listen_socket.connect(
    (ROBOT_IP, LISTEN_PORT)
)

print("tilkoblet robotens Listen-port")

#sende net_start signal=========================

connection.sendall(b"net_start")
print("net_start sendt til robot")

#motta net_start signal========================

listen_socket.settimeout(20)

try:
    data = listen_socket.recv(4096)

    if not data:
        raise ConnectionError("Roboten lukket forbindelse")

    response = data.decode("utf-8", errors="replace")

    if "net_start" in response:
        net_start = True
        print("net_start bekreftet fra robot")

    else:
        print("Uventet svar fra robot", response)

except socket.timeout:
    print("Timeout - ingen net_start fra robot")

#Kontroller initialiseringen=================================

if not net_start:
    print("Initialiseringen mislyktes")
    raise SystemExit

print("Initialiseringen fullført - klar for ordre")

#==========================================
#==============FUNKSJONER==================
#==========================================

#Leser ordre===============================

def hent_moduler():

    with open("ordre.json", "r") as fil:
        ordre = json.load(fil)

    moduler = ordre["modules"]

    return moduler

#overvåker nye ordre========================

def vent_pa_ny_ordre(sist_endret):

    print("venter på ny ordre..")

    while True:

        try:
            endret = os.stat("ordre.json").st_mtime_ns

            if endret != sist_endret:

                moduler = hent_moduler()

                print(f"Ny ordre mottatt: {len(moduler)} moduler")

                return moduler, endret
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        time.sleep(0.5)


#Beregn offset=================================================

def beregn_offset(modul):

    module_data = deler.modules[modul["id"]]

    bredde = module_data["width_mm"]
    hoyde = module_data["height_mm"]

    rotasjon = modul["rotation"]

    #Bytt bredde og høyde ved 90/270 grader
    if rotasjon in (90, 270):
        bredde, hoyde = hoyde, bredde

    #beregn offset fra sentrum av første gridcelle
    offset_x = (bredde - ROBOT_CELL_MM) / 2
    offset_y = (hoyde - ROBOT_CELL_MM) / 2

    #Beregn koordinat til modulens sentrum
    x_tcp = modul["x_mm"] + offset_x
    y_tcp = modul["y_mm"] + offset_y

    return x_tcp, y_tcp


#SORTERE MODULER ETTER AVSTAND FRA ORIGO=======================

def sorter_moduler(moduler):

    def avstand_fra_origo(modul):

        x_tcp, y_tcp = beregn_offset(modul)

        return x_tcp**2 + y_tcp**2

    moduler.sort(key=avstand_fra_origo)

    return moduler


#Lage TMSC-pakke================================

def lag_tmsct_packet(script_id, script):

    data = f"{script_id},{script}"

    length = len(data.encode("utf-8"))

    body = f"TMSCT,{length},{data},"

    checksum = 0

    for byte in body.encode("utf-8"):
        checksum ^= byte

    packet = f"${body}*{checksum:02X}\r\n"

    return packet.encode("utf-8")

#Sende modul til robot===========================

def send_modul(modul):

    x_tcp, y_tcp = beregn_offset(modul)

    rotasjon = modul["rotation"]
    ID = str(modul["id"])

    script = (
        f'g_x_mm={x_tcp}\r\n'
        f'g_y_mm={y_tcp}\r\n'
        f'g_rotasjon={rotasjon}\r\n'
        f'g_ID="{ID}"\r\n'
        'ScriptExit()'
    )

    packet = lag_tmsct_packet("1", script)

    listen_socket.sendall(packet)

    print(
        f"Modul sendt: ID={ID}, "
        f"X={x_tcp}, Y={y_tcp}, "
        f"Rotasjon={rotasjon}"
    )


#Vent på ok fra robot==============================

def vent_pa_ok():

    global ok

    ok = False

    print("Venter på OK fra robot..")

    response = b""

    while len(response) < 2:
        data = connection.recv(2 - len(response))

        if not data:
            raise ConnectionError("Roboten mistet forbindelsen")

        response += data

    if response.decode("utf-8").lower() == "ok":

        ok = True

        print("OK mottatt - robot klar for neste modul")

    else:
        raise ValueError(f"Uventet svar fra robot: {response}")


#======================================
#HOVEDLØKKEN===========================
#======================================

#Registrer eksisterende ordre
sist_endret = (
    os.stat("ordre.json").st_mtime_ns
    if os.path.exists("ordre.json")
    else None
)

while True:
    #Vent på ny ordre
    moduler, sist_endret = vent_pa_ny_ordre(sist_endret)

    #sorter moduler fra avstand
    moduler = sorter_moduler(moduler)

    print(f"Starter ordre med {len(moduler)} moduler")

    #send moduler en og en

    for modul in moduler:
        send_modul(modul)

        vent_pa_ok()

    #Alle moduler er plassert
    print("Ordre ferdig")
