# industri4
Programvare for vår oppgave i Industri 4.0


# deler.py

Denne filen definerer delenes dimensjoner, navn, ID etc. samt bilder dei linkes opp mot

# /images/

Her ligger bildene vi bruker til frontend i .png format

# frontend

Programkoden for fronend programmet. Dette styrer grid og plassering av modulene i rammeverket vårt.
Den genererer koordinater for modulene og lar kunde spesifisere hvor dem skal ligge.

* Trykk på modulnavnet på modulen du ønsker
* Klikk og drag modul
* Roter modul på "T"
* høyreklikk modul for å slette

Ved å trykke "Send", skrives den gitte kombinasjonen av plasserte deler seg til ordre.json filen.

# ordre.json

Her mellomlagres ordreinformasjonen etter frontend, klar for mellomvare til å handtere.

# mellomvare.py

Denne koden styrer kommunikasjon mellom TMflow og Python, samt offset og formidling av ordreinfoen fra ordre.json