#!/usr/bin/env python3

from math import pi, sin, cos, radians, hypot
from random import random, randint
from collections import defaultdict

from webcolors import hex_to_rgb
from hotqueue import HotQueue

import sys

import pdir

#from direct.showbase.PythonUtil import *
from panda3d.core import loadPrcFileData
#loadPrcFileData("", "want-directtools #t")
#loadPrcFileData("", "want-tk #t")
loadPrcFileData('', 'win-size 1280 720')
loadPrcFileData('', 'framebuffer-multisample 1')
loadPrcFileData('', 'multisamples 4')

from panda3d.core import *
from panda3d.bullet import *

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence

from util3d.cube import makeCube
from util3d.cameratex import CameraTexture, CameraCard

if "help" in sys.argv:
    print("""Command Line Arguments:
    fps:\tdisplay FPS meter
    debug:\tdisplay debug meter
    bullet:\tdisplay bullet RBs
    pause:\tstart with physics paused
    """)
    exit(0)

X_EXTENT = 32
Y_EXTENT = 24
Z_EXTENT = 18

def makeBoundaryBox(render, world):
    boundaryNode = BulletRigidBodyNode("Boundary")
    boundaryNode.setFriction(0)
    boundaryNode.setRestitution(1)
    boundaryNp = render.attachNewNode(boundaryNode)

    cubeNode = makeCube()
    cubeNp = NodePath("cube")
    cubeNp.attachNewNode(cubeNode)

    for pos, shape in (
            ((0, 0,  -Z_EXTENT), Vec3(X_EXTENT, Y_EXTENT,  1)),
            ((0, 0,   Z_EXTENT), Vec3(X_EXTENT, Y_EXTENT,  1)),
            ((0, -Y_EXTENT,  0), Vec3(X_EXTENT,  1, Z_EXTENT)),
            ((0,  Y_EXTENT,  0), Vec3(X_EXTENT,  1, Z_EXTENT)),
            ((-X_EXTENT, 0,  0), Vec3( 1, Y_EXTENT, Z_EXTENT)),
            (( X_EXTENT, 0,  0), Vec3( 1, Y_EXTENT, Z_EXTENT)),
    ):
        boundaryShape = BulletBoxShape(shape)
        boundaryNode.addShape(boundaryShape,
                              TransformState.makePos(pos))
        if pos[1] >= 0:
            np = render.attachNewNode("boundary-cube")
            np.setPos(pos)
            np.setTwoSided(True)
            np.setScale(shape)
            np.setColor((0.5, 0.5, 0.5, 0.5))
            cubeNp.instanceTo(np)
    world.attachRigidBody(boundaryNode)

def makeLight(i=1):
    light = PointLight("Light")
    light.setColor((i, i, i, 1))
    light.setAttenuation((1, 0.01, 0.0001))
    return light

class LaunchableText:
    def __init__(self, parent, world, font=None):
        self.textNode = TextNode("text")
        if font:
            self.textNode.setFont(font)
            m = self.textNode.getTransform()
            m[1][1] = 0.1
            self.textNode.setTransform(m)

        self.halfExtents = (0, 0, 0)

        self.rbNode = BulletRigidBodyNode("Text")
        self.rootNp = parent.attachNewNode(self.rbNode)
        self.textNp = self.rootNp.attachNewNode(self.textNode)
        self.textNp.setScale(2)

        self.rbNode.setFriction(0)
        self.rbNode.setRestitution(1)
        self.rbNode.setAngularDamping(0.3)
        self.rbNode.setLinearDamping(0)
        self.rbNode.setMass(1)
        self.rbNode.setDeactivationEnabled(False)
        self.rbNode.setKinematic(True)

        world.attach(self.rbNode)
        self.world = world

    def destroy(self):
        self.rootNp.detachNode()
        self.world.remove(self.rbNode)

    def setText(self, value):
        if hasattr(self, "bulletShape") and self.bulletShape:
            self.rbNode.removeShape(self.bulletShape)
            self.bulletShape = None

        self.textNode.setText(value)
        self.textNp.setPos(0, 0, 0)
        self.halfExtents = (0, 0, 0)

        if self.textNp.getTightBounds():
            ul, lr = self.textNp.getTightBounds()
            self.halfExtents = (lr - ul) / 2
            self.textNp.setPos(-self.halfExtents - ul)
            
            self.bulletShape = BulletBoxShape(self.halfExtents)
            self.rbNode.addShape(self.bulletShape)

    def getHalfExtents(self):
        return self.halfExtents

    def setColor(self, color):
        self.textNp.setColor(color)    

    def setPos(self, pos):
        self.rootNp.setPos(pos)

    def setHpr(self, hpr):
        self.rootNp.setHpr(hpr)

    def getPos(self):
        return self.rootNp.getPos()

    def getHpr(self):
        return self.rootNp.getHpr()

    def launch(self, linear, angular):
        self.rbNode.setKinematic(False)
        self.rbNode.setLinearVelocity(linear)
        self.rbNode.setAngularVelocity(angular)

class TextApp(ShowBase):
    def __init__(self):
        super().__init__(self)

        self.queue = HotQueue("text-updates")
        self.msgsPerFrameLimit = 10

        self.setBackgroundColor(0, 0, 0)
        self.setFrameRateMeter("fps" in sys.argv)
        self.setSceneGraphAnalyzerMeter("debug" in sys.argv)

        debugNode = BulletDebugNode('Debug')
        debugNode.showWireframe(True)
        debugNode.showConstraints(True)
        debugNode.showBoundingBoxes(False)
        debugNode.showNormals(False)
        debugNP = self.render.attachNewNode(debugNode)
        if "bullet" in sys.argv: debugNP.show()

        self.font = self.loader.loadFont(
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf')
        self.font.setPixelsPerUnit(60)
        self.font.setPageSize(512, 512)
        self.font.setRenderMode(TextFont.RMSolid)

        self.camera.setPos(0, -90, 0)
        self.disableMouse()

        self.paused = "pause" in sys.argv

        self.world = BulletWorld()
        if "gravity" in sys.argv:
            self.world.setGravity(Vec3(0, 0, -3))
        self.world.setDebugNode(debugNP.node())
        self.taskMgr.add(self.update, 'update')

        self.boundsNp = self.render.attachNewNode("BoundaryBox")
        makeBoundaryBox(self.boundsNp, self.world)

        self.textNp = self.render.attachNewNode("TextNodes")

        self.updateCamera = True
        self.cameraCard = CameraCard(self.render)
        self.cameraCard.setScale(Vec3(-16, 1, 9) * 4)
        self.cameraCard.setTwoSided(True)
        self.cameraCard.setPos((8 * 4, 22, -4.5 * 4))

        light = makeLight(1)
        lightNp = render.attachNewNode(light)
        lightNp.setPos(24, -30, 12)
        self.textNp.setLight(lightNp)

        light = makeLight(1)
        lightNp = render.attachNewNode(light)
        lightNp.setPos(-24, -30, -12)
        self.textNp.setLight(lightNp)

        ambient = PointLight("Ambient")
        ambient.setColor((.5, .5, .5, 1))
        ambientNp = render.attachNewNode(ambient)
        self.boundsNp.setLight(ambientNp)

        self.render.setShaderAuto()
        self.render.setAntialias(AntialiasAttrib.MAuto)

        if "sample" in sys.argv:
            self.sampleTexts = []
            for i in range(5):
                self.sampleTexts.append(self.addText("Sample %s" % i,
                                                     (random() * 10 - 5,
                                                      random() * 10 - 5,
                                                      random() * 10 - 5)))
            self.accept('l', self.sampleLaunch)

        self.launchers = defaultdict(
            lambda: LaunchableText(self.textNp, self.world, self.font))
        self.floaters = []

        self.targets = []
        #self.createTarget("A", -2, 5, -1)

        self.accept('1', self.debugNodes)
        self.accept('k', self.disableKinematic)
        self.accept('c', self.oobe)
        self.accept('g', self.toggleGravity)
        self.accept('p', self.pause)
        self.accept('b', self.toggleCameraBg)

    def debugNodes(self):
        print("\n".join(["{}\tGravity: {}\tLinear: {}\tAngular: {}".format(
            i, i.getGravity(), i.getLinearVelocity(), i.getAngularVelocity())
                         for i in self.world.getRigidBodies()]))

    def sampleLaunch(self):
        for i in self.sampleTexts:
            i.launch((random() * 10 - 5, random() * 10 - 5, random() * 10 - 5),
                     (random() * 10 - 5, random() * 10 - 5, random() * 10 - 5))
            
    def disableKinematic(self):
        for i in self.world.getRigidBodies():
            i.setKinematic(not i.isKinematic())

    def pause(self):
        self.paused = not self.paused
        print("Physics simulation is {} paused.".format(
            "now" if self.paused else "no longer"))

    def toggleGravity(self):
        if self.world.getGravity()[2] > 0:
            self.world.setGravity((0, 0, 0))
        elif self.world.getGravity()[2] == 0:
            self.world.setGravity((0, 0, -5))
        else:
            self.world.setGravity((0, 0, 5))
        print("New Gravity: ", self.world.getGravity())

    def toggleCameraBg(self):
        if self.cameraCard.parent:
            self.cameraCard.detachNode()
        else:
            self.cameraCard.reparentTo(self.render)
        
    def update(self, task):
        msg = self.queue.get()
        processed = 0
        while msg:
            print(msg)
            if msg["action"] == "leave":
                self.launchers[msg["client_id"]].destroy()
                del self.launchers[msg["client_id"]]
            elif msg["action"] == "update":
                self.processUpdate(msg)
            elif msg["action"] == "launch":
                self.processUpdate(msg)
                self.processLaunch(msg)
            processed += 1
            if processed < self.msgsPerFrameLimit:
                msg = self.queue.get()
            else:
                msg = None

        self.updateCamera = not self.updateCamera
        self.updateCamera and self.cameraCard.update()

        dt = globalClock.getDt()
        if not self.paused:
            self.world.doPhysics(dt)
        return task.cont

    def processUpdate(self, msg):
        props = msg["props"]
        text = self.launchers[msg["client_id"]]
        text.setText(props["text"])
        text.setColor(Vec3(*hex_to_rgb(props["color"])) / 256)

        props["y"] *= -1
        props["z"] *= -1
        if abs(props["x"]) != 1 and abs(props["y"]) != 1:
            if abs(props["x"]) > abs(props["y"]):
                props["x"] = 1 if props["x"] > 0 else -1
            else:
                props["y"] = 1 if props["y"] > 0 else -1;

        x = props["x"] * X_EXTENT * .95
        y = props["z"] * Y_EXTENT * .92
        z = props["y"] * Z_EXTENT * .90
        if abs(props["x"]) == 1:
            x += text.getHalfExtents()[0] * -props["x"]
        if abs(props["y"]) == 1:
            z += text.getHalfExtents()[0] * -props["y"]
            props["planarAngle"] += 90 * props["y"]
        text.setPos(Point3(x, y, z))

        if abs(props["x"]) == 1:
            hpr = Vec3(props["zAngle"], 0, props["planarAngle"])
        else:
            hpr = Vec3(0, -props["zAngle"], props["planarAngle"])
        text.setHpr(hpr)

    def processLaunch(self, msg):
        props = msg["props"]
        text = self.launchers[msg["client_id"]]
        
        hpr = text.getHpr()
        if abs(props["x"]) == 1:
            velocity = Vec3(
                -props["x"] * cos(radians(hpr[0])) * cos(radians(hpr[2])),
                -props["x"] * sin(radians(hpr[0])),
                -props["x"] * -sin(radians(hpr[2])))
        else:
            velocity = Vec3(
                cos(radians(hpr[2])),
                -sin(radians(hpr[1])),
                -cos(radians(hpr[1])) * sin(radians(hpr[2])))

        angular = Vec3(random(), random(), random())
        text.launch(velocity * (props["launchStrength"] * 10 + 3),
                    angular * props["launchStrength"] * 5)

        self.floaters.append(text)
        del self.launchers[msg["client_id"]]

    def createTarget(self, name, x=0, y=0, z=0):
        shape = BulletSphereShape(0.5)
        ghost = BulletGhostNode('GhostTarget_'+name)
        ghost.addShape(shape)
        ghostNP = self.render.attachNewNode(ghost)
        ghostNP.setPos(x, y, z)
        self.world.attachGhost(ghost)
        self.targets.append(ghost)

    def addText(self, value, pos=Point3(0, 0, 0)):
        text = LaunchableText(self.textNp, self.world, self.font)
        text.setText(value)
        text.setPos(pos)
        return text

if __name__ == "__main__":
    app = TextApp()
    app.run()
