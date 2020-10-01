#coding=utf-8
from picamera.array import PiRGBArray
from picamera import PiCamera
from threading import Thread
from tkinter import *
import os
import cv2
import numpy as np
from PIL import Image
import socket
import sys
import time

class Window(Frame):
    
    def __init__(self, master = None):
        Frame.__init__(self, master)
        self.master = master
        self.init_window()

    def init_window(self):
        self.master.title("Controllore")
        self.pack(fill=BOTH, expand=1)

        self.quitButton = Button(self, text="Esci", state=DISABLED, command=self.client_exit)
        self.quitButton.place(x=10, y=10)

        controllerButton = Button(self, text="Avvia Controllore", command=self.abilita_comandi)
        controllerButton.place(x=90, y=50)

        self.databaseButton = Button(self, text="Opzioni personale", state=DISABLED, command=self.opzioni_database)
        self.databaseButton.place(x=87, y=100)
        
        self.personalButton = Button(self, text="Verifica Personale", state=DISABLED, command=self.verifica_personale)
        self.personalButton.place(x=85, y=150)

    def abilita_comandi(self):
        self.quitButton.configure(state = "normal")
        self.databaseButton.configure(state = "normal")
        self.personalButton.configure(state = "normal")
        self.avvia_thread()

    def avvia_thread(self):
        global thread
        thread = Thread(name = 'daemon', target = self.avvia_ascolto)
        thread.setDaemon(True)
        thread.start()

    def client_exit(self):
        self.svuota_directory("/home/pi/Desktop/dataBase/fotoRicevute")
        self.svuota_directory("/home/pi/Desktop/dataBase/fotoBN")
        s.close() #chiudo ora il socket che rimane in loop
        print(" ")
        print("Socket terminato!")
        print("Controllore spento!")
        exit()

    def avvia_ascolto(self):
        PORT=11112
        HOST = ''   
        global s, conn

        #CREAZIONE SOCKET 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #per riutilizzare la connessione senza fallire bind uso SO_REUSEADDRS
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print ('Socket creato : '+socket.gethostname())        
        try:
            s.bind((HOST, PORT))
        except socket.error:
            print ('Bind fallito')
            sys.exit()
        print ('Socket bind completato')
        s.listen(1)
        print ('Socket in ascolto')

        conn, addr = s.accept()
        print ('Connesso con ' + addr[0] + ':' + str(addr[1]))
        self.avvia_controllore()

    def avvia_controllore(self):
        #RICEZIONE DATI
        data="0"
        fotoFile = ''
        listaFoto = []
        while 'stop' not in str(data):
            fotoFile = "dataBase/fotoRicevute/file"+str(time.time())+".jpg"
            listaFoto.append(fotoFile)
            #creiamo file jpg
            immagine = open(fotoFile, 'wb')
            print('Download...')
            while 1:
                try:
                    #riceviamo pacchetti da 512 bytes
                    data = conn.recv(512)
                    if 'fine' in str(data) or 'stop' in str(data):
                        break
                    #memorizziamo dati immagine
                    immagine.write(data)
                except socket.error:
                    print('download fallito')
                    s.close()
            #INVIO ACK di conferma 
            try:
                conn.send(bytes("ok", 'UTF-8'))
            except:
                print('Invio fallito')
                s.close()
            print('File ricevuto')
            
        #ricezione foto completata
        del(listaFoto[-1])
        print(listaFoto)
        print('FINE')

        #CHIUDIAMO SOCKET
        immagine.close()
        s.close()

        #inizio riconoscimento
        face_cascade = cv2.CascadeClassifier('dataBase/haarcascade_frontalface_default_face.xml')
        d = {}
        i=0
        cont=0
        listaFoto2 = []
        while i < len(listaFoto) :
            template = cv2.imread(listaFoto[i])
            i=i+1
            templateGray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(templateGray, 1.3, 5)
            for (x,y,w,h) in faces:
                cv2.rectangle(template,(x,y),(x+w,y+h),(255,0,0),2)
                cont=cont+1
                print("Sono stati individuati : "+str(cont)+" volti")
                cv2.imwrite("dataBase/fotoBN/Foto"+str(cont)+".jpg",templateGray[y:y+h, x:x+w])
                listaFoto2.append("dataBase/fotoBN/Foto"+str(cont)+".jpg")
            cv2.imshow("Frame", template)
            cv2.waitKey(250)
            
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)

        self.carica_personale(d)
        persone = d.keys()
        lun = len(persone)

        if(cont==0):
            self.manda_ris('null', False) #non ha trovato facce
            print("nessun volto rilevato")
        elif(lun > 1):
            rec = cv2.face.createLBPHFaceRecognizer();
            rec.load("dataBase/trainingData.yml")
            i=0
            Id=0
            nome=""
            while i < len(listaFoto2) :            
                template = cv2.imread(listaFoto2[i])
                gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                Id,conf=rec.predict(gray)
                if(conf<100 and Id in persone):
                    print (conf)
                    nome = d[Id]
                    print("Rilevato viso di " +nome)
                    print("Accesso consentito")
                    #led verde
                    self.manda_ris(nome, True)
                    break
                else:
                    nome = "sconosciuto"
                    print("Nessun volto conosciuto rilevato")
                    #led rosso
                    self.manda_ris(nome, False)
                cv2.imshow("Frame", template)
                cv2.waitKey(250)
                i=i+1
        else:
            self.manda_ris("vuoto", False) #database vuoto
        
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)

        #svuoto liste
        listaFoto = []
        listaFoto2 = []

        #svuoto le directory
        self.svuota_directory("/home/pi/Desktop/dataBase/fotoRicevute")
        self.svuota_directory("/home/pi/Desktop/dataBase/fotoBN")

        #riavvio ascolto controllore
        self.avvia_thread()

    def manda_ris(self, valore, led):
        self.avvia_connessione(11113)
        colore = 'rosso'
        if (led == True):
            colore = 'verde'
        try:
            s1.send(str.encode(str(valore), 'UTF-8'))
            print("inviato led" +str(colore)+" per: "+str(valore))
        except socket.error:
            print('invio risultato fallito')
            sys.exit()
        finally:
            s1.close()
        print('invio risultato riuscito')

    def svuota_directory(self, nomeDirectory):
        #cerca tutti i file che finiscono per .jpg in nomeDirectory
        file = [f for f in os.listdir(str(nomeDirectory)) if f.endswith(".jpg")]
        #rimuovo tutti i file
        for f in file:
            os.remove(str(nomeDirectory)+"/"+str(f))

    def avvia_connessione(self, PORT):        
        #creiamo un oggetto socket TCP/IP per una comunicazione full-duplex
        global s1
        try:
            s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except:
            print('Creazione socket fallita')
            sys.exit()
        print('Socket creato')
        #NOME SERVER
        HOST = '127.0.0.1'
        #HOST = '192.168.1.70'
        #INDIRIZZO IP SERVER
        try:
            remote_ip = socket.gethostbyname( HOST )
        except socket.gaierror:
            print('Connessione fallita')
            sys.exit()
        print('Indirizzo IP di '+HOST+' : '+remote_ip)

        #apriamo una connessione TCP: socket.connect(hostname,port)
        s1.connect((remote_ip, PORT))
        print('Socket connesso al server : '+HOST+' IP : '+remote_ip)

    def opzioni_database(self):
        d = {}
        self.carica_personale(d)
        self.stampa_dizionario(d)
        print("Seleziona funzione: ")
        print("A: AGGIUNGI PERSONA")
        print("B: ELIMINA PERSONA")
        print("C: ELIMINA DATABASE")
        print("D: TORNA A CONTROLLORE")
        print(" ")
        opzione = input("OPZIONE: ")
        if (opzione == 'A' or opzione == 'a'):
            self.aggiungi_persona()
        elif (opzione =='B' or opzione == 'b'):
            self.elimina_persona()
        elif (opzione == 'C' or opzione == 'c'):
            self.elimina_database()
        elif (opzione == 'D' or opzione == 'd'):
            print("fine opzioni")   
        else:
            print("Comando errato!")
            self.opzioni_database()
        

    def aggiungi_persona(self):
        d={}
        face_cascade = cv2.CascadeClassifier('dataBase/haarcascade_frontalface_default_face.xml')

        #carico dizionario
        self.carica_personale(d)

        #verifica presenza nel database
        flag=False
        while (flag==False):
            print(" ")
            nome = input("inserisci nome e cognome: ")
            persone = d.values()
            if(nome not in persone):
                flag=True
            else:
                print("persona già in database... riprova")

        #assegnazione id persona
        listaKey = d.keys()
        nKey = len(listaKey)
        num = 1
        while num <= nKey :
            if(num not in listaKey):
                d[num] = nome #aggiungo persona al database
                break
            num = num+1
            
        #izializziamo la picamera
        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.framerate = 32
        rawCapture = PiRGBArray(camera, size=(640, 480))
        time.sleep(0.1)

        #procedura riconoscimento volto
        print("")
        print("avvicinare il volto alla camera...")
        time.sleep(1)
        print("3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print(" ")
        print('Rilevamento di 20 volti...')
        print(" ")

        #avviamo la picamera e creo database di volti
        cont = 0
        for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            #creazione immagine in array numpy
            image = frame.array
            #conversione immagine in scala di grigi
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            #troviamo il volto, faces memorizza le coordinate del volto usando il file xml
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x,y,w,h) in faces:
                #salviamo il volto ritagliato in scala di grigi
                cv2.imwrite("dataBase/dataBaseVolti/User."+str(num)+"."+str(cont+1)+".jpg",gray[y:y+h, x:x+w])
                cont=cont+1
                print('volto numero '+str(cont))
                rawCapture.truncate(0)
                cv2.rectangle(image,(x,y),(x+w,y+h),(255,0,0),2)
                cv2.waitKey(100)

            #mostriamo i frame
            cv2.imshow("Frame", image)
            rawCapture.truncate(0)
            cv2.waitKey(1)
            if(cont>=20):
                print('Fine rilevamento!')
                break

        #creo database binario
        self.crea_databaseBinario()
        
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)

        camera.close()
        self.salva_personale(d)
        d = {}
        domanda = input("Vuoi aggiungere un'altra persona? Y/N :")
        if(domanda == 'Y' or domanda == 'y'):
            self.aggiungi_persona()
        else:
            print("")
            print("fine opzioni")

    def crea_databaseBinario(self):
        recognizer = cv2.face.createLBPHFaceRecognizer();
        path='dataBase/dataBaseVolti'
        Ids, faces=self.prendi_immagine(path)
        recognizer.train(faces, np.array(Ids))
        recognizer.save('dataBase/trainingData.yml')

    def prendi_immagine(self, path):
        imagePaths=[os.path.join(path,f) for f in os.listdir(path)]
        faces=[]
        IDs=[]
        for imagePath in imagePaths:
            faceImg=Image.open(imagePath).convert('L');
            faceNp=np.array(faceImg,'uint8')
            ID=int(os.path.split(imagePath)[-1].split('.')[1])
            faces.append(faceNp)
            #print(ID)
            IDs.append(ID)
            cv2.imshow("training",faceNp)
            cv2.waitKey(10)
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)
        return IDs, faces

    def elimina_persona(self):
        #elimino da file personale
        d = {}
        self.carica_personale(d)
        num = input("Inserisci ID persona da eliminare: ")
        Id = int(num)
        if (Id not in d):
            print("")
            print("Errore! Persona non presente nel database!")
            d = {}
            time.sleep(1)
            self.opzioni_database()
        else:
            persona = d.pop(Id) #rimuove e restituisce valore
            self.salva_personale(d)
        #elimino da databaseVolti
        n = 1
        nomeDirectory = "/home/pi/Desktop/dataBase/dataBaseVolti"
        while n <= 20:
            #trovo foto
            file = [f for f in os.listdir(str(nomeDirectory)) if f.endswith("User."+str(Id)+"."+str(n)+".jpg")]
            #rimuovo foto
            for f in file:
                os.remove(str(nomeDirectory)+"/"+str(f))
                n = n+1
        lun = len(d.keys())
        if lun > 1:
            #creo database binario
            self.crea_databaseBinario()
        else:
            #eliminata ultima persona nel database
            os.remove("/home/pi/Desktop/dataBase/trainingData.yml")
        print(str(persona)+" è stato/a rimosso/a con successo!")
        print("")
        domanda = input("Vuoi eliminare un'altra persona? Y/N :")
        if(domanda == 'Y' or domanda == 'y'):
            self.elimina_persona()
        else:
            print("")
            print("fine opzioni")
            

    def elimina_database(self):
        #elimino da file personale
        d = {}
        d[100] = 'full'
        self.salva_personale(d)
        d = {}
        #elimino da databaseVolti
        self.svuota_directory("/home/pi/Desktop/dataBase/dataBaseVolti")
        os.remove("/home/pi/Desktop/dataBase/trainingData.yml")
        print("Database eliminato con successo!")
        
        
    def carica_personale(self, d):
        p = ""
        f = open("dataBase/personale.txt", "r")
        while(p != "100 full\n"):
            p = f.readline()
            if (p == ""):
                d[100]="full"
            persona = p.split(" ")
            if(persona[0] != "100"):
                num = int(persona[0])
                nome = persona[1]+" "+persona[2]
                n = nome.split("\n")
                name = n[0]
                d[num] = name #aggiungo al dizionario

        f.close()
        d[100] = "full"

    def salva_personale(self, d):
        self.stampa_dizionario(d)
        f = open("dataBase/personale.txt", "w")
        for x in d.keys():
            f.write(str(x)+" "+str(d[x])+"\n")
        f.close()
        print("Nuovo personale salvato!")
        print(" ")

    def stampa_dizionario(self, d): #stampa il dizionario ordinato per chiavi
        print("")
        print("Lista personale: [ID = NOME] ")
        print("")
        lista = d.keys()
        ordinata = set(lista)
        for k in ordinata:
            print ('['+ str(k) + ' = ' + str(d[k]) + ']')
        print("")

    def verifica_personale(self):
        d = {}
        self.carica_personale(d)
        persone = d.keys()
        lun = len(persone)

        #verifico se dizionario è vuoto
        if ( lun > 1 ):
            #creiamo un oggetto socket TCP/IP per una comunicazione full-duplex
            try:
                sp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            except:
                print('Creazione socket fallita')
                sys.exit()
            print('Socket creato')
            #NOME SERVER
            HOST = ''
            PORTA = 11114
            #INDIRIZZO IP SERVER
            try:
                remote_ip = socket.gethostbyname( HOST )
            except socket.gaierror:
                print('Connessione fallita')
                sys.exit()
            print('Indirizzo IP di '+HOST+' : '+remote_ip)

            #apriamo una connessione TCP: socket.connect(hostname,port)
            sp.connect((remote_ip, PORTA))
            print('Socket connesso al server : '+HOST+' IP : '+remote_ip)
        
            #RICEZIONE DATI
            data="0"
            fotoFile = ''
            listaFoto = []
            while 'stop' not in str(data):
                fotoFile = "dataBase/fotoRicevute/file"+str(time.time())+".jpg"
                listaFoto.append(fotoFile)
                #creiamo file jpg
                immagine = open(fotoFile, 'wb')
                print('Download...')
                while 1:
                    try:
                        #riceviamo pacchetti da 512 bytes
                        data = sp.recv(512)
                        if 'fine' in str(data) or 'stop' in str(data):
                            break
                        #memorizziamo dati immagine
                        immagine.write(data)
                    except socket.error:
                        print('download fallito')
                        sp.close()
                #INVIO ACK di conferma 
                try:
                    sp.send(bytes("ok", 'UTF-8'))
                except:
                    print('Invio ACK fallito')
                    sp.close()
                print('File ricevuto')
            
            #ricezione foto completata
            del(listaFoto[-1])
            print(listaFoto)
            print('FINE')

            #CHIUDIAMO SOCKET
            immagine.close()
            sp.close()

            #inizio riconoscimento
            face_cascade = cv2.CascadeClassifier('dataBase/haarcascade_frontalface_default_face.xml')
            i=0
            cont=0
            listaFoto2 = []
            listaRilevati = []
            while i < len(listaFoto) :
                template = cv2.imread(listaFoto[i])
                i=i+1
                templateGray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(templateGray, 1.3, 5)
                for (x,y,w,h) in faces:
                    cv2.rectangle(template,(x,y),(x+w,y+h),(255,0,0),2)
                    cont=cont+1
                    print("Sono stati individuati : "+str(cont)+" volti")
                    cv2.imwrite("dataBase/fotoBN/Foto"+str(cont)+".jpg",templateGray[y:y+h, x:x+w])
                    listaFoto2.append("dataBase/fotoBN/Foto"+str(cont)+".jpg")
                cv2.imshow("Frame", template)
                cv2.waitKey(250)
            
            cv2.destroyAllWindows()
            cv2.waitKey(1)
            cv2.waitKey(1)
            cv2.waitKey(1)
            cv2.waitKey(1)

            if(cont==0):
                print("nessun personale rilevato")
            else:
                rec = cv2.face.createLBPHFaceRecognizer();
                rec.load("dataBase/trainingData.yml")
                i=0
                Id=0
                nome=""
                while i < len(listaFoto2) :            
                    template = cv2.imread(listaFoto2[i])
                    gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    Id,conf=rec.predict(gray)
                    if(conf<100 and Id in persone and nome not in listaRilevati):
                        nome = d[Id]
                        listaRilevati.append(nome)
                    i=i+1
                    print("...")
                print("lista personale rilevato: " +str(listaRilevati))
        
            cv2.destroyAllWindows()
            cv2.waitKey(1)
            cv2.waitKey(1)
            cv2.waitKey(1)
            cv2.waitKey(1)

            #svuoto liste
            listaFoto = []
            listaFoto2 = []

            #svuoto le directory
            self.svuota_directory("/home/pi/Desktop/dataBase/fotoRicevute")
            self.svuota_directory("/home/pi/Desktop/dataBase/fotoBN")

        else:
            print("")
            print("Database vuoto!")
        #svuoto dizionario    
        d = {}

root = Tk()
root.geometry("300x230")
app = Window(root)
root.mainloop()
