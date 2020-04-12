#!/usr/bin/env python3

from math import pi, sin, cos
from random import random, randint

from panda3d.core import loadPrcFileData
#loadPrcFileData("", "want-directtools #t")
#loadPrcFileData("", "want-tk #t")

from panda3d.core import Point3, Vec3
from panda3d.core import TextNode, TextFont, AntialiasAttrib

from panda3d.bullet import *

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence

class TextApp(ShowBase):

    def __init__(self):
        super().__init__(self)
        #self.tutorialScene()

        self.setBackgroundColor(0, 0, 0)

        debugNode = BulletDebugNode('Debug')
        debugNode.showWireframe(True)
        debugNode.showConstraints(True)
        debugNode.showBoundingBoxes(False)
        debugNode.showNormals(False)
        debugNP = self.render.attachNewNode(debugNode)
        debugNP.show()

        self.font = self.loader.loadFont(
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf')
        self.font.setPixelsPerUnit(60)
        self.font.setPageSize(512, 512)
        self.font.setRenderMode(TextFont.RMSolid)

        self.camera.setPos(0, -20, 10)
        self.camera.setHpr(0, -20, 0)
        #self.taskMgr.add(self.spinCameraTask, "spinCameraTask")
        self.disableMouse()

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -.1))
        self.world.setDebugNode(debugNP.node())
        self.taskMgr.add(self.update, 'update')

        self.camera.setPos(0, -20, 0)
        self.disableMouse()

        for i in range(5):
            self.addText("Sample %s" % i, random() * 5, random() * 5, 2)

        self.targets = []
        self.createTarget("A", -2, 5, -1)

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

        shape = BulletBoxShape(Vec3(0.5, 0.5, 0.5))
        node = BulletRigidBodyNode("Text")
        node.setMass(1)
        node.addShape(shape)
        
        np = self.render.attachNewNode(node)
        np.setPos(x, y, z)

        tnp = np.attachNewNode(text)
        tnp.setColor(random(), random(), random(), 1)
        #tnp.setAntialias(AntialiasAttrib.MMultisample)


        self.world.attachRigidBody(node)


    def update(self, task):
        dt = globalClock.getDt()
        self.world.doPhysics(dt)
        return task.cont

    def tutorialScene(self):
        # Load the environment model.
        self.scene = self.loader.loadModel("models/environment")
        # Reparent the model to render.
        self.scene.reparentTo(self.render)
        # Apply scale and position transforms on the model.
        self.scene.setScale(0.25, 0.25, 0.25)
        self.scene.setPos(-8, 42, 0)

        # Load and transform the panda actor.
        self.pandaActor = Actor("models/panda-model",
                                {"walk": "models/panda-walk4"})
        self.pandaActor.setScale(0.005, 0.005, 0.005)
        self.pandaActor.reparentTo(self.render)
        # Loop its animation.
        self.pandaActor.loop("walk")

        posInterval1 = self.pandaActor.posInterval(13,
                                                   Point3(0, -10, 0),
                                                   startPos=Point3(0, 10, 0))
        posInterval2 = self.pandaActor.posInterval(13,
                                                   Point3(0, 10, 0),
                                                   startPos=Point3(0, -10, 0))
        hprInterval1 = self.pandaActor.hprInterval(3,
                                                   Point3(180, 0, 0),
                                                   startHpr=Point3(0, 0, 0))
        hprInterval2 = self.pandaActor.hprInterval(3,
                                                   Point3(0, 0, 0),
                                                   startHpr=Point3(180, 0, 0))

        # Create and play the sequence that coordinates the intervals.
        self.pandaPace = Sequence(posInterval1, hprInterval1,
                                  posInterval2, hprInterval2,
                                  name="pandaPace")
        self.pandaPace.loop()

    # Define a procedure to move the camera.
    def spinCameraTask(self, task):
        angleDegrees = abs(task.time * 6.0 % 360 - 180) - 90
        angleRadians = angleDegrees * (pi / 180.0)
        self.camera.setPos(20 * sin(angleRadians), -20 * cos(angleRadians), 0)
        self.camera.setHpr(angleDegrees, 0, 0)
        return Task.cont

app = TextApp()
app.run()
