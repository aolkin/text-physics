import cv2
import io
import os
import time
import sys

from redis import Redis

from panda3d.core import CardMaker, Texture, PNMImage

from direct.stdpy import threading, thread

PIPE_FILE = "panda_camera_pipe.pnm"

class CameraReader:
    def __init__(self, index=1, pipe=PIPE_FILE):
        self.cap = cv2.VideoCapture(index)
        self.pipe = pipe
        self.redis = Redis()
        self.redis.delete("camera-lock")

    def getFrame(self):
        ret, frame = self.cap.read()

        if ret:
            with self.redis.lock("camera-lock"):
                return cv2.imwrite(self.pipe, frame)
        return ret

class CameraTexture:
    def __init__(self, pipe=PIPE_FILE):
        self.tex = Texture("CameraTexture")
        self.pipe = pipe
        self.redis = Redis()
        self.redis.delete("camera-lock")
        self.image = None
        self.thread = thread.start_new_thread(self.readImage, ())

    def readImage(self):
        while True:
            with self.redis.lock("camera-lock"):
                newImage = PNMImage(self.pipe)
                self.image = newImage
            time.sleep(0.06)

    def update(self):
        if self.image:
            self.tex.load(self.image)

    def getTexture(self):
        return self.tex

class CameraCard:
    def __init__(self, parent):
        self.tex = CameraTexture()
        cm = CardMaker("CameraCard")
        self.cardNp = parent.attachNewNode(cm.generate())
        self.cardNp.setTexture(self.tex.getTexture())

    def __getattr__(self, name):
        return getattr(self.cardNp, name)

    def update(self):
        return self.tex.update()

if __name__ == "__main__":
    camera = CameraReader(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    while True:
        ret = camera.getFrame()
        print(time.time())
        time.sleep(0.05)
