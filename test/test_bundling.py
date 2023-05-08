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
from pygraphml import GraphMLParser 
import sys, random, math
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QSizePolicy
from PySide6.QtGui import QBrush, QPen, QTransform, QPainter, QColor

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
        zoom = 1 + event.angleDelta().y()*0.001;
        self.scale(zoom, zoom)
        
    def mousePressEvent(self, event):
        self.startX = event.pos().x()
        self.startY = event.pos().y()
        self.myScene.wasDragg = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        endX = event.pos().x()
        endY = event.pos().y()
        deltaX = endX - self.startX
        deltaY = endY - self.startY
        distance = math.sqrt(deltaX*deltaX + deltaY*deltaY)
        if(distance > 5):
            self.myScene.wasDragg = True
        super().mouseReleaseEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('VIZ Qt for Python Example')
        self.createGraphicView()
        
        self.graph = GraphMLParser().parse("airlines.graphml/airlines.graphml")
        
        self.generateLine()
        #self.generateCircle()
        
        #self.setMinimumSize(800, 600)
        self.show()

    def createGraphicView(self):
        self.scene = VisGraphicsScene()
        self.brush = [QBrush(Qt.yellow), QBrush(Qt.green), QBrush(Qt.blue)]
        self.view = VisGraphicsView(self.scene, self)
        self.setCentralWidget(self.view)
        self.view.setGeometry(0, 0, 800, 600)

    def generateLine(self):
        alpha = 150 #Interval is [0,255]
        color = QColor(0,0,0,alpha)
        pen = QPen(color,0.5)
        
        i = 5
        edges = self.graph.edges()
        edges.reverse()
        for edge in edges:
            start = edge.node1
            x1 = float(start['x'])
            y1 = float(start['y'])
            
            end = edge.node2
            x2 = float(end['x'])
            y2 = float(end['y'])
            
            line = self.scene.addLine(x1,y1,x2,y2,pen=pen)
            line.setData(0,"{}->{}".format(start['label'],end['label']))
            points = edge_subdivision_points(edge,3)
            #print(points)
            self.generateCircles(points)
            
            if i == 0:
                break
            
            i -= 1
        
    def generateCircles(self,points):
        #Generate random data
        d = 5
        
        for x,y in points:
            ellipse = self.scene.addEllipse(x-d/2, y-d/2, d, d, self.scene.pen, self.brush[0])

def edge_subdivision_points(edge,n=1):
    node1 = edge.node1
    node2 = edge.node2
    
    if n == 1:
        return [node1,node2]
    else:
        start = node1
        x = float(start['x']) 
        y = float(start['y'])
        end = node2
        list_of_points = [(x,y)]
        for i in range(n-1):
            if i == 1:
                pass
            x -= (float(start['x']) - float(end['x']))/n
            y -= (float(start['y']) - float(end['y']))/n

            list_of_points.append((x,y))

        list_of_points.append((float(end['x']),float(end['y']) ))
        return list_of_points

def edge_length(edge):
    ##Return euclidian distance of edge
    node1 = edge.node1
    node2 = edge.node2
    x1 = float(node1['x'])
    y1 = float(node1['y'])
    x2 = float(node2['x'])
    y2 = float(node2['y'])
    
    return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))

def main():
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
