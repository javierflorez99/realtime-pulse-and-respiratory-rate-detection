import os
import shutil
import time

import face_recognition
import cv2
import numpy as np

from database import createDB
from model.getPulse import getPulse


class FaceRecognition:
    def __init__(self, con, customLog):
        super().__init__()
        self.known_face_encodings = []
        self.known_face_names = []
        self.process_this_frame = True
        self.face_locations = []
        self.face_names = []
        self.setUpUsers(con, customLog)
        self.frameCount = 0
        self.pulse = "Procesando..."
        self.heartBeatCount = 250
        self.heartBeatTimes = [time.time()] * self.heartBeatCount
        self.heartBeatValues = [0] * self.heartBeatCount
        self.frame_rate = 30
        self.prev = 0

    def setUpUsers(self, con, customLog):
        """
        Establece la lista de usuarios.
        """
        info = createDB.getAllInfo(con)
        pathToTemp = "../temp/"
        if not os.path.exists(pathToTemp):
            os.makedirs(pathToTemp)
        for name, image in info.items():
            with open(pathToTemp + str(name) + ".jpeg", "wb") as f:
                f.write(image)
        filelist = [file for file in os.listdir(pathToTemp) if file.endswith('.jpeg')]
        for fileName in filelist:
            user_image = face_recognition.load_image_file(pathToTemp + fileName)
            user_face_encoding = face_recognition.face_encodings(user_image)

            if not user_face_encoding:
                customLog.appendPlainText("No puede encontrar rostros en la imagen")
                continue
            else:
                user_face_encoding = user_face_encoding[0]

            self.known_face_encodings.append(user_face_encoding)
            self.known_face_names.append(fileName)

        shutil.rmtree(pathToTemp)

    def resize(self, frame):
        """
        Cambio de forato para una detección más rápida de los rostros en la cámara
        """
        self.small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

    def bgrToRgb(self):
        self.rgb_small_frame = self.small_frame[:, :, ::-1]

    def rgbToGrey(self):
        return cv2.cvtColor(self.small_frame, cv2.COLOR_RGB2GRAY)

    def findFace(self):
        self.face_locations = face_recognition.face_locations(self.rgb_small_frame)
        face_encodings = face_recognition.face_encodings(self.rgb_small_frame, self.face_locations)
        self.face_names = []
        for face in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face)
            name = "Desconocido"
            face_distances = face_recognition.face_distance(self.known_face_encodings, face)
            if np.any(face_distances):
                best_match_index = np.argmin(face_distances)
            else:
                best_match_index = None
            if best_match_index is not None and matches[best_match_index]:
                name = self.known_face_names[best_match_index]
            self.face_names.append(name.replace('.jpeg', ''))

    def initFaceRecognition(self, frame):
        self.resize(frame)
        self.bgrToRgb()
        if self.process_this_frame:
            self.findFace()
        self.process_this_frame = not self.process_this_frame
        self.displayResults(frame)

    def displayResults(self, frame):
        gx, gy, gw, gh = 100, 100, 100, 100
        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            top_fhead = top
            bottom_fhead = int(top + (bottom - top) / 50)
            left_fhead = int(left + (right - left) / 2 - (right - left) / 50)
            right_fhead = int(right - (right - left) / 2 + (right - left) / 50)

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left_fhead, top_fhead), (right_fhead, bottom_fhead), (0, 255, 0), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            cv2.rectangle(frame, (left - 1, bottom), (right + 1, bottom + 36), (0, 0, 255), cv2.FILLED)

            # Coordenadas del capturador de color
            gx = ((right - left) / 2) + left - (right - left) / 4
            gy = bottom - ((bottom - top) / 5)

            gh = (bottom - top) / 2
            gw = (right - left) / 2

        cropImg = self.rgbToGrey()[int(gy - gh):int(gy), int(gx):int(gx + gw)]

        self.heartBeatValues = self.heartBeatValues[1:] + [np.average(self.rgb_small_frame)]
        self.heartBeatTimes = self.heartBeatTimes[1:] + [time.time()]

        if not self.frameCount % 250:

            newPulse = getPulse(self.heartBeatTimes, self.heartBeatValues, self.pulse)
            if newPulse is not None:
                self.pulse = int(newPulse)

        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            font = cv2.FONT_HERSHEY_DUPLEX

            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
            cv2.putText(frame, str(self.pulse), (left + 6, bottom + 35), font, 1.0, (255, 255, 255), 1)
