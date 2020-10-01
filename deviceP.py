#coding=utf-8
import RPi.GPIO as GPIO
from picamera.array import PiRGBArray
from picamera import PiCamera 
from tkinter import *
import numpy as np
import cv2
import socket
import sys
import os
import profile
import time

GPIO.setmode(GPIO.BCM) #imposta la modalità per il processore in uso BCM2835
GPIO.setwarnings(False) #disabilita avvertimenti errori

tSessione = []
ttSessione = []
tCaricamento = []
tInvio = []
tAck = []

class Window(Frame):

    def __init__(self, master = None):
        Frame.__init__(self, master)
        self.master = master
        self.init_window()

    def init_window(self):
        self.master.title("Periferica Porta")
        self.pack(fill=BOTH, expand=1)

        quitButton = Button(self, text="Esci", command=self.client_exit)
        quitButton.place(x=10, y=10)

        accessButton = Button(self, text="Verifica Accesso", command=self.verifica_accesso)
        accessButton.place(x=60, y=60)

        ledButton = Button(self, text="Test Led", command=self.test_led)
        ledButton.place(x=80, y=100)

    def client_exit(self):
        exit()

    def verifica_accesso(self):
        face_cascade = cv2.CascadeClassifier('dataBase/haarcascade_frontalface_default_face.xml')

        #inizializziamo la picamera
        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.framerate = 64
        rawCapture = PiRGBArray(camera, size=(640, 480))
        time.sleep(0.1)

        #avvio la connessione
        self.avvia_connessione(11112)

        tempo = 1
        tempoTotale=0
        inizioSessione=0
        fineSessione=0
        cont = 1

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
        print("avvio riconoscimento!")

        #avviamo la picamera
        for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            inizioSessione = time.time()
            image = frame.array
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            cv2.imshow("Frame", image)
            cv2.waitKey(100)
            nomeFoto = "dataBase/fotoInviate/file"+str(inizioSessione)+".jpg"
            cv2.imwrite(nomeFoto, image)
            rawCapture.truncate(0)
            print('Foto salvata')
            self.manda_foto(s1, nomeFoto)
            fineSessione = time.time()
            tempoSessione = fineSessione - inizioSessione
            tSessione.append(tempoSessione)
            print("Tempo sessione "+str(cont)+": "+str(tempoSessione))
            tempoTotale = tempoTotale + tempoSessione
            print("Tempo totale fino alla sessione "+str(cont)+" : "+str(tempoTotale))
            ttSessione.append(tempoTotale)
            if (tempoTotale > tempo) :
                print("stima tempo in eccesso per mandare un altra foto : "+str(tempoTotale - tempo))
                try:
                    s1.send(str.encode("stop", 'UTF-8'))
                except socket.error:
                    print("invio hack fallito")
                break
            cont=cont+1

        #aggiorno le statistiche
        self.aggiorna_statistiche(cont, tSessione, tCaricamento, tInvio, tAck)

        #CHIUDIAMO SOCKET
        s1.close()
        camera.close()
        
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)

        #ricevo led verifica accesso
        self.ricevi_ris()

        #svuoto le directory
        self.svuota_directory("/home/pi/Desktop/dataBase/fotoInviate")

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

    def manda_foto(self, connessione, nomeF):
        totaleCaricamento = 0
        inizioCaricamento = 0
        fineCaricamento = 0
        fineInvio = 0
        inizioInvio = 0
        totaleInvio = 0
        inizioAck = 0
        fineAck = 0
        totaleAck = 0
        risp=''
        while 'ok' not in str(risp):
            try:
                #file binario (no codifica)
                immagine = open(nomeF, 'rb')
                print('Invio file in corso...')
                while 1:
                    inizioCaricamento = time.time()
                    data = immagine.readline(2048)
                    fineCaricamento = time.time()
                    totaleCaricamento = totaleCaricamento + ( fineCaricamento - inizioCaricamento )
                    if not data:
                        connessione.send(str.encode("fine", 'UTF-8'))
                        break
                    inizioInvio = time.time()
                    connessione.send(data)
                    fineInvio = time.time()
                    totaleInvio = totaleInvio + ( fineInvio - inizioInvio )
            except socket.error:
                print('Invio dati fallito')
                sys.exit()
            try:
                inizioAck = time.time()
                print('Attesa risposta file ricevuto')
                #riceviamo dati
                risp = connessione.recv(2048)
                if 'ok' not in str(risp):
                    print('File non inviato')
                print('File inviato')
                fineAck = time.time()
                totaleAck = fineAck - inizioAck
            except socket.error:
                print('Ricezione fallita')
                sys.exit()
            print('Tempo per caricare il file : '+str(totaleCaricamento))
            tCaricamento.append(totaleCaricamento)
            print('Tempo per inviare file : '+str(totaleInvio))
            tInvio.append(totaleInvio)
            print("Tempo ricezione ACK : "+str(totaleAck))
            tAck.append(totaleAck)

    def aggiorna_statistiche(self, cont, tSessione, tCaricamento, tInvio, tAck):
        i=sommaS=sommaC=sommaI=sommaA=0
        while i < cont:
            sommaS = sommaS + tSessione[i]
            sommaC = sommaC + tCaricamento[i]
            sommaI = sommaI + tInvio[i]
            sommaA = sommaA + tAck[i]
            i = i+1
        print("somma sessione "+str(sommaS))
        print("somma caricamento "+str(sommaC))
        print("somma invio "+str(sommaI))
        print("somma hack "+str(sommaA))

        mediaSessione = sommaS/cont
        mediaCaricamento = sommaC/cont
        mediaInvio = sommaI/cont
        mediaAck = sommaA/cont

        j=0
        f = open("dataBase/statisticheP.txt", "w")
        while j < cont:
            f.write("tempo sessione "+str(j)+" : "+str(tSessione[j])+"\n")
            f.write("tempo caricamento "+str(j)+" : "+str(tCaricamento[j])+"\n")
            f.write("tempo invio "+str(j)+" : "+str(tInvio[j])+"\n")
            f.write("tempo ack "+str(j)+" : "+str(tAck[j])+"\n\n")
            j = j+1
            if j == cont :
                f.write("Media")
                f.write("Media sessione "+str(mediaSessione)+"\n\n")
                f.write("Media caricamento "+str(mediaCaricamento)+"\n\n")
                f.write("Media invio "+str(mediaInvio)+"\n\n")
                f.write("Media ack "+str(mediaAck)+"\n\n")
        f.close()            
        print("")
        print("Statistiche aggiornate!")
        print("")

    def ricevi_ris(self):
        self.avvia_ris(11113)
        data=''
        try:
            #riceviamo pacchetti da 512 bytes
            print("download")
            data = conn.recv(512)
            if 'sconosciuto' in str(data):
                print("Nessun volto conosciuto rilevato!")
                print("ACCESSO NEGATO!")
                self.led_rosso()
            elif 'null' in str(data):
                print("Nessun volto rilevato!")
                print("ACCESSO NEGATO!")
                self.led_rosso()
            elif 'vuoto' in str(data):
                print("Database vuoto!")
                print("ACCESSO NEGATO!")
                self.led_rosso()
            else:
                persona = str(data)
                nome = persona.split("'")
                print("rilevato viso di: "+nome[1])
                print("ACCESSO CONSENTITO!")
                self.led_verde()
        except s.socket:
            print('download fallito')
            conn.close()
            s.close()
        #chiudo il socket
        conn.close()
        s.close()

    def svuota_directory(self, nomeDirectory):
        #cerca tutti i file che finiscono per .jpg in nomeDirectory
        file = [f for f in os.listdir(str(nomeDirectory)) if f.endswith(".jpg")]
        #rimuovo tutti i file
        for f in file:
            os.remove(str(nomeDirectory)+"/"+str(f))

    def avvia_ris(self, PORT):
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

        #COMUNICAZIONE
        conn, addr = s.accept()
        print ('Connesso con ' + addr[0] + ':' + str(addr[1]))

    def led_verde(self):
        GPIO.setup(7,GPIO.OUT)
        GPIO.output(7,True)
        time.sleep(5)
        GPIO.output(7,False)

    def led_rosso(self):
        GPIO.setup(9,GPIO.OUT)
        GPIO.output(9,True)
        time.sleep(5) 
        GPIO.output(9,False) 

    def test_led(self):
        print('Avvio test led...')
        #led verde
        print('Accensione led verde')
        time.sleep(1)
        self.led_verde()
        #led rosso
        print('Accensione led rosso')
        time.sleep(1)
        self.led_rosso()
        print('Test terminato!')


root = Tk()
root.geometry("250x150")
app = Window(root)
root.mainloop()
