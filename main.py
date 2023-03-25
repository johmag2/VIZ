# Copyright (c) 2021 Ladislav Čmolík
#
# Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is 
# hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE 
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE 
# FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS 
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING 
# OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import sys, random, math
from PySide6.QtCore import Qt, QSize, QLineF
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QSizePolicy
from PySide6.QtGui import QBrush, QPen, QTransform, QPainter
import numpy as np

import graph

class VisGraphicsScene(QGraphicsScene):
    def __init__(self):
        super(VisGraphicsScene, self).__init__()
        self.selection = None
        self.wasDragg = False
        self.pen = QPen(Qt.black)
        self.selected = QPen(Qt.red)

    def mouseReleaseEvent(self, event): 
        if(self.wasDragg):
            return
        if(self.selection):
            self.selection.setPen(self.pen)
        item = self.itemAt(event.scenePos(), QTransform())
        
        if(item):
            item.setPen(self.selected)
            self.selection = item

class VisGraphicsView(QGraphicsView):
    def __init__(self, scene, parent):
        super(VisGraphicsView, self).__init__(scene, parent)
        self.startX = 0.0
        self.startY = 0.0
        self.distance = 0.0
        self.myScene = scene
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

    def wheelEvent(self, event):
        zoom = 1 + event.angleDelta().y()*0.001
        self.scale(zoom, zoom)
        
    def mousePressEvent(self, event):
        self.startX = event.position().x()
        self.startY = event.position().y()
        self.myScene.wasDragg = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        endX = event.position().x()
        endY = event.position().y()
        deltaX = endX - self.startX
        deltaY = endY - self.startY
        distance = math.sqrt(deltaX*deltaX + deltaY*deltaY)
        if(distance > 5):
            self.myScene.wasDragg = True
        super().mouseReleaseEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.graph = graph.graph()
        self.graph.parse("airlines.graphml/airlines.graphml")
        #self.graph.airport_throughput()
        
        self.setWindowTitle('American air traffic')
        self.createGraphicView()
        
        self.circle_to_node = {}
        self.node_to_circle = {}
        self.drawNodes()
        self.line_to_edge = {}
        self.edge_to_line = {}
        self.drawEdges()
        
        #self.setMinimumSize(800, 600)
        self.show()
        

    def createGraphicView(self):
        self.scene = VisGraphicsScene()
        
        self.brush = [QBrush(Qt.yellow),QBrush(Qt.green), QBrush(Qt.blue),QBrush(Qt.red)]
        
        self.view = VisGraphicsView(self.scene, self)
        self.setCentralWidget(self.view)
        self.view.setGeometry(0, 0, 800, 600)
        
        
    def drawNodes(self):
        
        #Determine size of airport based on throughput
        g = self.graph
        outgoing,incoming = self.airport_throughput(g)
        total = outgoing + incoming 
        
        colours = np.zeros((len(total)),dtype=np.int16)
        colours[total > 25] = 1
        colours[total > 50] = 2
        colours[total > 100] =3
        #colours[total > 100] =4
        
        
        for i in g.nodes():
            x = float(i['x'])
            y = float(i['y'])
            c = colours[int(i.id)]
            
            #total = i['Incoming'] + i['Outgoing']
            d =  2 * math.log (total[int(i.id)],2) 
            
            ellipse = self.scene.addEllipse(x -d/2, y-d/2, d, d, self.scene.pen,self.brush[c])
            
            self.circle_to_node[i] = ellipse
            self.node_to_circle[ellipse] = i
    
    
    def drawEdges(self):
        
        for edge in self.graph.edges():
            start = edge.node1
            x1 = float(start['x'])
            y1 = float(start['y'])
            
            end = edge.node2
            x2 = float(end['x'])
            y2 = float(end['y'])
            
            line = self.scene.addLine(x1,y1,x2,y2)
            self.line_to_edge[line] = edge
            self.edge_to_line[edge] = line
            
        
    
    def airport_throughput(self,g):
        ## Count the throughput of an airport
        outgoing = np.zeros(len(g.nodes()))
        incoming = np.zeros(len(g.nodes()))
        
        for edge in g.edges():
            outgoing[int(edge.node1.id)] += 1   #Outgoing  
            incoming[int(edge.node2.id)] += 1   #Incoming
        
        return outgoing,incoming
    
    
def main():
    app = QApplication(sys.argv)

    ex = MainWindow()
    sys.exit(app.exec())
    
if __name__ == "__main__":
    main()
