#!/usr/bin/env python3

from math import pi, sin, cos
from random import random, randint

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

class TextApp(ShowBase):

    def __init__(self):
        super().__init__(self)
        #self.tutorialScene()

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
        #self.camera.setHpr(0, -20, 0)
        #self.taskMgr.add(self.spinCameraTask, "spinCameraTask")
        self.disableMouse()

        self.rbNodes = []
        self.paused = "pause" in sys.argv

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, 0))
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
            for i in range(5):
                self.addText("Sample %s" % i,
                             random() * 5, -24, random() * 5)

        self.targets = []
        self.createTarget("A", -2, 5, -1)

        self.accept('1', self.debugCamera)
        self.accept('2', self.debugNodes)
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

    def pause(self):
        self.paused = not self.paused

    def toggleGravity(self):
        if self.world.getGravity()[1] > 0:
            self.world.setGravity((0, 0, 0))
        elif self.world.getGravity()[1] == 0:
            self.world.setGravity((0, -10, 0))
        else:
            self.world.setGravity((0, 10, 0))

    def update(self, task):
        dt = globalClock.getDt()
        if not self.paused:
            self.world.doPhysics(dt)
        return task.cont

    def createTarget(self, name, x=0, y=0, z=0):
        shape = BulletSphereShape(0.5)
        ghost = BulletGhostNode('GhostTarget_'+name)
        ghost.addShape(shape)
        ghostNP = self.render.attachNewNode(ghost)
        ghostNP.setPos(x, y, z)
        self.world.attachGhost(ghost)
        self.targets.append(ghost)

    def addText(self, value, x=0, y=0, z=0):
        text = TextNode("text")
        text.setFont(self.font)
        text.setText(value)
        m = text.getTransform()
        m[1][1] = 0.1
        text.setTransform(m)

        node = BulletRigidBodyNode("Text")
        np = self.textNp.attachNewNode(node)
        np.setPos(x, y, z)
        tnp = np.attachNewNode(text)
        tnp.setColor(random(), random(), random(), 1)

        ul, lr = tnp.getTightBounds()
        halfExtents = (lr - ul) / 2
        tnp.setPos(-halfExtents - ul)
        shape = BulletBoxShape(halfExtents)
        node.addShape(shape)
        node.setMass(1)
        node.setLinearSleepThreshold(0)
        node.setFriction(0)
        node.setRestitution(1)
        node.setAngularDamping(0.5)
        node.setLinearDamping(0)

        self.rbNodes.append(node)

        self.world.attachRigidBody(node)

    def spinCameraTask(self, task):
        angleDegrees = abs(task.time * 6.0 % 180 - 90) - 45
        angleRadians = angleDegrees * (pi / 180.0)
        self.camera.setPos(20 * sin(angleRadians),
                           -20 * cos(angleRadians), 10)
        self.camera.setHpr(angleDegrees, 0, 0)
        return Task.cont

app = TextApp()
app.run()
