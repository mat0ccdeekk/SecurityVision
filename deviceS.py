#coding=utf-8
from picamera.array import PiRGBArray
from picamera import PiCamera
from threading import Thread
from tkinter import *
import numpy as np
import cv2
import socket
import sys
import os
import profile
import time

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
        self.master.title("Periferica Stanza")
        self.pack(fill=BOTH, expand=1)

        self.quitButton = Button(self, text="Esci", state=DISABLED, command=self.client_exit)
        self.quitButton.place(x=10, y=10)

        interiorButton = Button(self, text="Avvia Periferica", command=self.abilita_comandi)
        interiorButton.place(x=60, y=60)

    def abilita_comandi(self):
        self.quitButton.configure(state = "normal")
        self.avvia_thread()

    def client_exit(self):
        self.svuota_directory("/home/pi/Desktop/dataBase/fotoInviate")
        s.close() #chiudo ora il socket che rimane in loop
        print(" ")
        print("Socket terminato!")
        exit()

    def avvia_thread(self):
        global thread
        thread = Thread(name = 'daemon', target = self.avvia_ascolto)
        thread.setDaemon(True)
        thread.start()

    def avvia_ascolto(self):
        PORT=11114
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
        self.avvia_periferica()

    def avvia_periferica(self):
        face_cascade = cv2.CascadeClassifier('dataBase/haarcascade_frontalface_default_face.xml')

        #inizializziamo la picamera
        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.framerate = 64
        rawCapture = PiRGBArray(camera, size=(640, 480))
        time.sleep(0.1)

        tempo = 5
        tempoTotale=0
        inizioSessione=0
        fineSessione=0
        cont = 1

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
            self.manda_foto(conn, nomeFoto)
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
                    conn.send(str.encode("stop", 'UTF-8'))
                except socket.error:
                    print("invio hack fallito")
                break
            cont=cont+1

        #aggiorno le statistiche
        self.aggiorna_statistiche(cont, tSessione, tCaricamento, tInvio, tAck)

        #CHIUDIAMO SOCKET
        s.close()
        camera.close()
        
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)
        cv2.waitKey(1)
        
        #svuoto le directory
        self.svuota_directory("/home/pi/Desktop/dataBase/fotoInviate")

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
        f = open("dataBase/statisticheS.txt", "w")
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
        #riavvio periferica
        self.avvia_thread()

    def svuota_directory(self, nomeDirectory):
        #cerca tutti i file che finiscono per .jpg in nomeDirectory
        file = [f for f in os.listdir(str(nomeDirectory)) if f.endswith(".jpg")]
        #rimuovo tutti i file
        for f in file:
            os.remove(str(nomeDirectory)+"/"+str(f))

root = Tk()
root.geometry("250x150")
app = Window(root)
root.mainloop()
