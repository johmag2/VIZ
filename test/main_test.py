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
from PySide6.QtCore import Qt, QSize, QRectF, QLineF
import PySide6.QtWidgets as QtWidgets
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QSizePolicy, QWidget
from PySide6.QtGui import QBrush, QPen, QTransform, QPainter, QColor
import numpy as np
import copy
import graph
from edge_bundling import *

class VisGraphicsScene(QGraphicsScene):
    def __init__(self,window):
        super(VisGraphicsScene, self).__init__()
        self.window = window
        self.selection = []
        self.wasDragg = False
        self.cir_pen = QPen(Qt.black)
        self.line_pen = QPen(QColor(0,0,100,100),0.25)
        self.selected = QPen(Qt.red)
        self.l = []

    def mouseReleaseEvent(self, event): 
        if(self.wasDragg):
            return
        if(self.selection):
            [item.setPen(self.cir_pen) if type(item) == QtWidgets.QGraphicsEllipseItem else item.setPen(self.line_pen) for item in self.selection]
            #[item.setPen(self.pen) for item in self.selection if ]
            
        item = self.itemAt(event.scenePos(), QTransform())
        
        if(item):
            print(item.data(0))
            
            self.updateInfo(item)
            
            item.setPen(self.selected)
            self.selection.append(item)
            
            if type(item) == QtWidgets.QGraphicsEllipseItem:
                node = self.window.circle_to_node[item]
                self.selectEdges(node)

    def updateInfo(self,item):
        ##Update info label
        if type(item) == QtWidgets.QGraphicsEllipseItem:
            node = self.window.circle_to_node[item]
            text = "Airport: \n {} \n Incoming: {} \n Outgoing: {}".format(node["label"],node["in"],node["out"] )
                
        elif type(item) == QtWidgets.QGraphicsLineItem:
            text = "Airplane: \n" + item.data(0)     
            
        widget = self.window.dock.widget()
        info = widget.findChild(QtWidgets.QLabel,"Info")   #,"Info")
        info.setText(text) 
    
    def listChangeEvent(self,name):
        ##Function to catch the text change signal
        
        #Empty exception
        if name == "-":
            return
        
        ##Get selected node
        node = self.window.graph.name_to_node[name]
        
        ##Reset previous selected
        if self.selection:
            [item.setPen(self.cir_pen) if type(item) == QtWidgets.QGraphicsEllipseItem else item.setPen(self.line_pen) for item in self.selection]
           # [item.setPen(self.pen) for item in self.selection]
            
        ##Get circle
        circle_obj = self.window.node_to_circle[node]
        
        #Update viz
        self.updateInfo(circle_obj)
        circle_obj.setPen(self.selected)
        self.selection.append(circle_obj)
        self.selectEdges(node)

    def stepEvent(self):
        self.window.bundling.forcebundle_step()
        
        if self.l != [] and self.l is not None:
            for node in self.l:
                self.removeItem(node)
                del node
        
        self.l = self.window.drawLines(self.window.bundling.subdivision_points_for_edges)    
        #self.l = self.window.generateCircles(self.window.bundling.subdivision_points_for_edges,10,1)
        
    def selectEdges(self,node):
        ##Select edges stemming from node
        graph = self.window.graph
        out = graph.node_id_to_out_id[node.id]
        edges = graph.edges()
        
        for edge_id in out:
            edge = edges[int(edge_id)]
            try:
                line = self.window.edge_to_line[edge]
                
                line.setPen(self.selected)
                self.selection.append(line)
                
            except KeyError:
                pass
        
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
        #self.graph.parse("test_graph/test_ES.graphml")
        
        #self.graph = GraphMLParser().parse("airlines.graphml/airlines.graphml")
        self.graph.get_node_labels()
        #self.graph.airport_throughput()
        
        self.setWindowTitle('American air traffic')
        self.createGraphicView()
        
        ## Dicts to go from node to graphical object and vice versa
        self.circle_to_node = {}
        self.node_to_circle = {}
        self.drawNodes()
        
        ## Dicts to go from line to graphical object and vice versa
        self.line_to_edge = {}
        self.edge_to_line = {}
        #self.drawEdges()
        
        ##
        self.addGUI()
    
        self.setMinimumSize(800, 600)
        self.show()
        
        #print(self.circle_to_node)
        #print(self.node_to_circle)
        self.bundling = EdgeBundling(self.graph.edges())
        self.bundling.set_up()
        
        #self.bundling.forcebundle()
        #self.scene.l = self.drawLines(self.bundling.subdivision_points_for_edges)
        #self.scene.l = self.generateCircles(self.bundling.subdivision_points_for_edges,10,1)
        
    def generateCircles(self,edges,d,color_id):
        l = list()
        #Generate random data
        #d = 1
        #print(points)
        for points in edges: 
            for x,y in points:
                ellipse = self.scene.addEllipse(x-d/2, y-d/2, d, d, self.scene.cir_pen, self.brush[color_id])
                l.append(ellipse)
        return l
                     
    def addGUI(self):
        ## Attempt to add gui
        area = Qt.DockWidgetArea(0x2)
        self.dock = QtWidgets.QDockWidget(self)
        self.dock.setWindowTitle("")
        
        #text.setParent(self.dock)
        
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        
        layout.addWidget(QtWidgets.QLabel("Select Airport:",objectName='Select'),0)
        layout.addWidget(self.listSetUp(),1)
        layout.addWidget(QtWidgets.QLabel("Info:", objectName='InfoTitle'),0)
        layout.addWidget(QtWidgets.QLabel("", objectName='Info'),1)
        
        layout.addWidget(QtWidgets.QLabel("", objectName='Space'),3)
    
        layout.addWidget(self.paramSetUp(),3)
            
        #self.dock.setWidget(text)
        widget = QWidget()
        widget.setLayout(layout)
        self.dock.setWidget(widget)
        
        self.addDockWidget(area,self.dock)
        
    def listSetUp(self):
        
        node_list = QtWidgets.QComboBox(objectName='Box')
        
        ##Add each node to the list
        node_list.addItem("-")
        for node in self.graph.nodes():
            node_list.addItem(node["label"])
            
        ##Sort list alphabeticly
        node_list.model().sort(0)
        node_list.currentTextChanged.connect(self.scene.listChangeEvent)
        
        return node_list
    
    def paramSetUp(self):
        param_box_layout = QtWidgets.QVBoxLayout()
        param_box = QtWidgets.QGroupBox("Parameters") 
        
        widgets = [
            QtWidgets.QLabel("Testing"),
            QtWidgets.QSlider(Qt.Horizontal,objectName='Slider'),
            QtWidgets.QPushButton("Step")
        ]
        
        widgets[-1].clicked.connect(self.scene.stepEvent)  
        
        for w in widgets:
            param_box_layout.addWidget(w)
        
        #param_box_layout.setAlignment(Qt.AlignBottom)
        param_box.setLayout(param_box_layout)
        
        return param_box
    
    def createGraphicView(self):    
        self.scene = VisGraphicsScene(self)
        
        self.brush = [QBrush(Qt.green), QBrush(Qt.yellow), QBrush(Qt.red)]
        #self.brush = [QBrush(Qt.blue),QBrush(Qt.green), QBrush(Qt.yellow), QBrush(Qt.red)] ##https://doc.qt.io/qt-6/qt.html#GlobalColor-enum
        self.view = VisGraphicsView(self.scene, self)
        
        self.setCentralWidget(self.view)
        self.view.setGeometry(0, 0, 800, 600)
        
        
    def drawNodes(self):
        """
        for node in self.graph.node_to_circle.values():
            self.scene.addLine(node)
        
        """
        #Determine size of airport based on throughput
        g = self.graph
        outgoing,incoming = g.airport_throughput()
        total = outgoing + incoming 
        sort_indexes = np.argsort(total)
        
        ## Set color of airports
        colours = np.zeros((len(total)),dtype=np.int16) #Green
        colours[total > 25] = 1     #Yellow
        colours[total > 50] = 2     #Red
        #colours[total > 100] = 3
        #colours[total > 100] = 4
        nodes = g.nodes()
        
        for index in reversed(sort_indexes):
            i = nodes[index]
            x = float(i['x'])
            y = float(i['y'])
            c = colours[int(i.id)]
        
            d = math.sqrt(total[int(i.id)]) 
            
            ellipse = self.scene.addEllipse(x-d/2, y-d/2, d, d, self.scene.cir_pen,self.brush[c])
            ellipse.setData(0,i['label'])
            
            self.circle_to_node[ellipse] = i
            self.node_to_circle[i] = ellipse
    
    def drawEdges(self):
        """
        for edge in self.graph.edge_to_line.values():
            self.scene.addLine(edge)
         """
        """   
        alpha = 150 #Interval is [0,255]
        color = QColor(0,0,0,alpha)
        pen = QPen(color,0.5)
        """
        for edge in self.graph.edges():
            start = edge.node1
            x1 = float(start['x'])
            y1 = float(start['y'])
            
            end = edge.node2
            x2 = float(end['x'])
            y2 = float(end['y'])
            
            line = self.scene.addLine(x1,y1,x2,y2,pen=self.scene.line_pen)
            line.setData(0,"{}->{}".format(start['label'],end['label']))
            
            self.line_to_edge[line] = edge
            self.edge_to_line[edge] = line
            
            #break
            
    def drawLines(self,edges):
        l = list()
        """
        for edge in self.graph.edge_to_line.values():
            self.scene.addLine(edge)
         """
        """   
        alpha = 150 #Interval is [0,255]
        color = QColor(0,0,0,alpha)
        pen = QPen(color,0.5)
        """
        for edge in edges:
            for i in range(1,len(edge)):
                start = edge[i-1]
                x1 = start[0]
                y1 = start[1]
                
                end = edge[i]
                x2 = end[0]
                y2 = end[1]
                
                line = self.scene.addLine(x1,y1,x2,y2,pen=self.scene.line_pen)
                
                #line.setData(0,"{}->{}".format(start['label'],end['label']))
                
                #self.line_to_edge[line] = edge
                #self.edge_to_line[edge] = line
                l.append(line)
        return l
    
def main():
    app = QApplication(sys.argv)

    ex = MainWindow()
    sys.exit(app.exec())
    
if __name__ == "__main__":
    main()
