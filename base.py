#!/usr/bin/env python3

from math import pi, sin, cos
from random import random, randint

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

if "help" in sys.argv:
    print("""Command Line Arguments:
    fps:\tdisplay FPS meter
    debug:\tdisplay debug meter
    bullet:\tdisplay bullet RBs
    pause:\tstart with physics paused
    """)
    exit(0)

def makeBoundaryBox(render, world):
    boundaryNode = BulletRigidBodyNode("Boundary")
    boundaryNode.setFriction(0)
    boundaryNode.setRestitution(1)
    boundaryNp = render.attachNewNode(boundaryNode)

    cubeNode = makeCube()
    cubeNp = NodePath("cube")
    cubeNp.attachNewNode(cubeNode)

    for pos, shape in (
            ((0, 0,  -18), Vec3(32, 24,  1)),
            ((0, 0,   18), Vec3(32, 24,  1)),
            ((0, -24,  0), Vec3(32,  1, 18)),
            ((0,  24,  0), Vec3(32,  1, 18)),
            ((-32, 0,  0), Vec3( 1, 24, 18)),
            (( 32, 0,  0), Vec3( 1, 24, 18)),
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

        self.rbNode = BulletRigidBodyNode("Text")
        self.rootNp = parent.attachNewNode(self.rbNode)
        self.textNp = self.rootNp.attachNewNode(self.textNode)

        self.rbNode.setFriction(0)
        self.rbNode.setRestitution(1)
        self.rbNode.setAngularDamping(0.3)
        self.rbNode.setLinearDamping(0)
        self.rbNode.setMass(1)
        self.rbNode.setDeactivationEnabled(False)
        self.rbNode.setKinematic(True)

        world.attachRigidBody(self.rbNode)

    def setText(self, value):
        self.textNode.setText(value)

        ul, lr = self.textNp.getTightBounds()
        halfExtents = (lr - ul) / 2
        self.textNp.setPos(-halfExtents - ul)

        if hasattr(self, "bulletShape"):
            self.rbNode.removeShape(self.bulletShape)
        self.bulletShape = BulletBoxShape(halfExtents)
        self.rbNode.addShape(self.bulletShape)

    def setColor(self, color):
        self.textNp.setColor(color)    

    def setPos(self, pos):
        self.rootNp.setPos(pos)

    def setHpr(self, hpr):
        self.rootNp.setHpr(hpr)

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

        light = makeLight(2)
        lightNp = render.attachNewNode(light)
        lightNp.setPos(24, -30, 12)
        self.textNp.setLight(lightNp)

        light = makeLight(2)
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

        self.targets = []
        #self.createTarget("A", -2, 5, -1)

        self.accept('1', self.debugCamera)
        self.accept('2', self.debugNodes)
        self.accept('k', self.disableKinematic)
        self.accept('c', self.oobe)
        self.accept('g', self.toggleGravity)
        self.accept('p', self.pause)

    def debugCamera(self):
        self.enableMouse()
        print(self.camera.getPos(), self.camera.getHpr())

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

    def update(self, task):
        dt = globalClock.getDt()
        if not self.paused:
            self.world.doPhysics(dt)

        msg = self.queue.get()
        processed = 0
        while msg:
            print(msg)
            if msg["props"]["text"]:
                if msg["action"] == "update":
                    self.processUpdate(msg)
                elif msg["action"] == "launch":
                    self.processUpdate(msg)
                    self.processLaunch(msg)
            processed += 1
            if processed < self.msgsPerFrameLimit:
                msg = self.queue.get()
            else:
                msg = None
        return task.cont

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

app = TextApp()
app.run()
