from pygraphml import GraphMLParser 
from pygraphml import Graph as pyGraph
import numpy as np
import math
from PySide6.QtCore import Qt, QSize, QLineF,QRectF


class graph(pyGraph):
    def __init__(self,g=None):
        super(graph,self).__init__()
        
        if isinstance(g, pyGraph):
            self._nodes = g._nodes
            self._edges = g._edges
            self.get_node_labels()
        
        self.circle_to_node = {}
        self.node_to_circle = {}
        self.line_to_edge = {}
        self.edge_to_line = {}
            
    
    def parse(self,url):
        g = GraphMLParser().parse(url)
        self._nodes = g._nodes
        self._edges = g._edges
        self.get_node_labels()
        #self.airport_throughput()
        #self.create_nodes()
        #self.create_edges()
        
    def get_node_labels(self): 
        
        for node in self.nodes():
            
            label = node['tooltip'][0:3]
            node['label'] = label
            
        return label 
    
    
    def airport_throughput(self):
        ## Not finished
        ## Count the throughput of an airport
        
        N = len(self.nodes())
        outgoing = np.zeros(N)
        incoming = np.zeros(N)
        
        for edge in self.edges():
            try:
                edge.node1["Outgoing"] = int(edge.node1["Outgoing"]) + 1
                edge.node2["Incoming"] = int(edge.node2["Incoming"]) + 1
            except KeyError:
                edge.node1["Outgoing"] = 1
                edge.node2["Incoming"] = 1
            
            #outgoing[int(edge.node1.id)] += 1   #Outgoing  
            #incoming[int(edge.node2.id)] += 1   #Incoming
        
        return outgoing,incoming
        
    def create_nodes(self):
        #Create nodes
        
        for i in self.nodes():
            x = float(i['x'])
            y = float(i['y'])
            #c = colours[int(i.id)]
            
            total = int(i['Incoming']) + int(i['Outgoing'])
            d =  2 * math.log (total,2) 
            
            ellipse = QRectF(x -d/2, y-d/2, d, d)
            
            self.circle_to_node[i] = ellipse
            self.node_to_circle[ellipse] = i
    
    def create_edges(self):
        
        for edge in self.edges():
            start = edge.node1
            x1 = float(start['x'])
            y1 = float(start['y'])
            
            end = edge.node2
            x2 = float(end['x'])
            y2 = float(end['y'])
            
            line = QLineF(x1,y1,x2,y2)
            self.line_to_edge[line] = edge
            self.edge_to_line[edge] = line
        
def main():
    pyG = GraphMLParser().parse("airlines.graphml/airlines.graphml")
    g = graph()
    
if __name__ == "__main__":
    main()
