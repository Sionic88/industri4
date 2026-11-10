import socket
import json
import os
import time
import select
import deler

#kommunikasjon=============================
HOST = "0.0.0.0"
START_PORT = 5000

ROBOT_IP = "10.0.12.101"
LISTEN_PORT = 5890

# Tid til oppkobling og bekreftelser (sekunder)
CONNECT_TIMEOUT = 30
INIT_TIMEOUT = 30
TMSCT_TIMEOUT = 10
ROBOT_OK_TIMEOUT = 300

#Variabler
x_mm = 0.0
y_mm = 0.0
rotasjon = 0
ID = ""

ROBOT_CELL_MM = 60

net_start = False
ok = False

# Buffer for meldinger som kan komme oppdelt / samlet over TCP
listen_buffer = b""
ok_ventende = False

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
print(f"Robot tilkoblet fra {address}")

#sende net_start signal=========================

connection.sendall(b"net_start")
print("net_start sendt til robot")

#Motta net_start tilbake fra Network Send====================
# TMflow kan sende på den eksisterende TCP-forbindelsen eller
# opprette en ny tilkobling til port 5000. Begge deler håndteres.

frist = time.monotonic() + INIT_TIMEOUT
aktive_forbindelser = [connection]
start_buffer = {}

while not net_start:
    tid_igjen = frist - time.monotonic()
    if tid_igjen <= 0:
        raise TimeoutError("Fikk ikke net_start tilbake fra Network Send")

    klare, _, _ = select.select([server] + aktive_forbindelser, [], [], tid_igjen)

    if not klare:
        continue

    for sock in klare:
        if sock is server:
            ny_connection, ny_adresse = server.accept()
            aktive_forbindelser.append(ny_connection)
            print(f"Svarforbindelse fra robot: {ny_adresse}")
            continue

        data = sock.recv(4096)

        if not data:
            aktive_forbindelser.remove(sock)
            start_buffer.pop(sock, None)
            sock.close()
            continue

        start_buffer[sock] = start_buffer.get(sock, b"") + data
        if b"net_start" in start_buffer[sock].lower():
            net_start = True
            print("net_start bekreftet fra Network Send")
            break

        if len(start_buffer[sock]) > 4096:
            raise ValueError("Uventet oppstartsdata fra TMflow")

# Init er fullført. Listen-kommunikasjonen bruker en egen socket.
for sock in aktive_forbindelser:
    sock.close()
server.close()

#INITIATE - KOBLE TIL LISTEN====================
# Forsøk flere ganger mens TMflow starter Listen-serveren.

start_tid = time.monotonic()

while True:
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.settimeout(3)

    try:
        listen_socket.connect((ROBOT_IP, LISTEN_PORT))
        break

    except (OSError, socket.timeout) as feil:
        listen_socket.close()

        if time.monotonic() - start_tid >= CONNECT_TIMEOUT:
            raise ConnectionError(
                f"Kunne ikke koble til {ROBOT_IP}:{LISTEN_PORT} "
                f"innen {CONNECT_TIMEOUT} sekunder"
            ) from feil

        print("Listen ikke klar, prøver igjen...")
        time.sleep(1)

print("tilkoblet robotens Listen-port")

#==========================================
# LES KOMPLETT PAKKE FRA LISTEN (TMSCT/TMSTA/CPERR)
#==========================================

def motta_listen_pakke(timeout):
    global listen_buffer

    frist = time.monotonic() + timeout

    while b"\r\n" not in listen_buffer:
        tid_igjen = frist - time.monotonic()
        if tid_igjen <= 0:
            raise socket.timeout("Ingen komplett pakke fra Listen")

        listen_socket.settimeout(tid_igjen)
        data = listen_socket.recv(4096)

        if not data:
            raise ConnectionError("Roboten lukket Listen-forbindelsen")

        listen_buffer += data

        if len(listen_buffer) > 16384:
            raise ValueError("For stor eller ufullstendig Listen-pakke")

    pakke, listen_buffer = listen_buffer.split(b"\r\n", 1)

    # Kontroller standardformatet $HEADER,LEN,DATA,*CHECKSUM
    if not pakke.startswith(b"$") or b"*" not in pakke:
        raise ValueError(f"Ugyldig TMflow-pakke: {pakke!r}")

    body, mottatt_checksum = pakke[1:].rsplit(b"*", 1)
    checksum = 0
    for byte in body:
        checksum ^= byte

    try:
        riktig_checksum = int(mottatt_checksum, 16)
    except ValueError as feil:
        raise ValueError("Ugyldig sjekksum i Listen-pakke") from feil

    if checksum != riktig_checksum:
        raise ValueError(f"Feil sjekksum i Listen-pakke: {pakke!r}")

    try:
        header, lengde, nyttedata = body.split(b",", 2)
        if not nyttedata.endswith(b","):
            raise ValueError("Mangler skilletegn før sjekksum")
        nyttedata = nyttedata[:-1]

        if len(nyttedata) != int(lengde):
            raise ValueError("Feil datalengde i Listen-pakke")

        innhold = nyttedata.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as feil:
        raise ValueError(f"Kunne ikke tolke TMflow-pakken: {pakke!r}") from feil

    if header == b"CPERR":
        return "CPERR", "", innhold

    if header not in (b"TMSCT", b"TMSTA"):
        raise ValueError(f"Ukjent TMflow-melding: {header!r}")

    nummer, melding = innhold.split(",", 1)
    return header.decode("ascii"), nummer, melding


#Vent til TMflow faktisk har gått inn i første Listen-node=====
# TMSTA 00 bekrefter Listen-status, uten at Listen trenger å
# sende net_start en gang til.

frist = time.monotonic() + INIT_TIMEOUT
listen_klar = False

while time.monotonic() < frist and not listen_klar:
    listen_socket.sendall(b"$TMSTA,2,00,*41\r\n")
    slutt = min(time.monotonic() + 2, frist)

    while time.monotonic() < slutt and not listen_klar:
        try:
            type_pakke, nummer, melding = motta_listen_pakke(
                slutt - time.monotonic()
            )
        except socket.timeout:
            break

        if type_pakke == "CPERR":
            raise RuntimeError(f"TMflow-protokollfeil under init: {melding}")

        if type_pakke == "TMSTA" and nummer == "00":
            if melding.startswith("true,"):
                listen_klar = True
                print("TMflow bekrefter at Listen er aktiv")
            elif melding.startswith("false,"):
                break

    if not listen_klar:
        time.sleep(0.3)

if not listen_klar:
    raise TimeoutError("TMflow kom ikke inn i Listen-noden")

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
    global ok_ventende

    x_tcp, y_tcp = beregn_offset(modul)

    rotasjon = modul["rotation"]
    ID = str(modul["id"])

    script = (
        f'var_g_x_mm={x_tcp}\r\n'
        f'var_g_y_mm={y_tcp}\r\n'
        f'var_g_rotasjon={rotasjon}\r\n'
        f'var_g_ID="{ID}"\r\n'
        'ScriptExit()'
    )

    packet = lag_tmsct_packet("1", script)

    listen_socket.sendall(packet)

    print(
        f"Modul sendt: ID={ID}, "
        f"X={x_tcp}, Y={y_tcp}, "
        f"Rotasjon={rotasjon}"
    )

    # Kontroller at TMflow godtar scriptet før vi venter på ferdig plassering.
    frist = time.monotonic() + TMSCT_TIMEOUT

    while True:
        tid_igjen = frist - time.monotonic()
        if tid_igjen <= 0:
            raise TimeoutError("Ingen TMSCT-kvittering fra roboten")

        type_pakke, nummer, melding = motta_listen_pakke(tid_igjen)

        if type_pakke == "CPERR":
            raise RuntimeError(f"TMflow-protokollfeil: {melding}")

        # En rask robot kan rekke tilbake til Listen før vi leser kvitteringen.
        if type_pakke == "TMSCT" and nummer == "0" and melding == "ok":
            ok_ventende = True
            continue

        if type_pakke == "TMSCT" and nummer == "1":
            if melding == "OK":
                print("TMSCT OK - variablene er godtatt")
                return

            raise RuntimeError(f"TMflow avviste scriptet: {melding}")


#Vent på ok fra robot==============================

def vent_pa_ok():
    global ok, ok_ventende

    ok = False

    print("Venter på OK fra robot..")

    if ok_ventende:
        ok_ventende = False
        ok = True
        print("OK mottatt - robot klar for neste modul")
        return

    frist = time.monotonic() + ROBOT_OK_TIMEOUT

    while not ok:
        tid_igjen = frist - time.monotonic()
        if tid_igjen <= 0:
            raise TimeoutError("Ingen ferdigmelding fra roboten")

        type_pakke, nummer, melding = motta_listen_pakke(tid_igjen)

        if type_pakke == "CPERR":
            raise RuntimeError(f"TMflow-protokollfeil: {melding}")

        # Inngangsmelding fra Listen når TMflow er klar på nytt.
        if type_pakke == "TMSCT" and nummer == "0" and melding == "ok":
            ok = True
            print("OK mottatt - robot klar for neste modul")

        elif (type_pakke == "TMSCT" and nummer == "1"
              and melding != "OK"):
            raise RuntimeError(f"TMflow meldte scriptfeil: {melding}")


# Vent til Listen faktisk er klar for neste modul
def vent_til_listen_klar():

    print("Kontrollerer at Listen er klar...")

    frist = time.monotonic() + 15

    while time.monotonic() < frist:

        # Spør TMflow om Listen er aktiv
        listen_socket.sendall(b"$TMSTA,2,00,*41\r\n")

        slutt = min(time.monotonic() + 1, frist)

        while time.monotonic() < slutt:

            try:
                type_pakke, nummer, melding = motta_listen_pakke(
                    slutt - time.monotonic()
                )
            except socket.timeout:
                break

            if type_pakke == "CPERR":
                raise RuntimeError(f"TMflow-feil: {melding}")

            if type_pakke == "TMSTA" and nummer == "00":

                if melding.strip().lower() == "true,ok":
                    print("Listen er klar for neste modul")
                    return

                break

        time.sleep(0.2)

    raise TimeoutError("Listen ble ikke klar for neste modul")


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
        vent_til_listen_klar()

    #Alle moduler er plassert
    print("Ordre ferdig")
