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
            self.airport_throughput()
        
        self.circle_to_node = {}
        self.node_to_circle = {}
        self.line_to_edge = {}
        self.edge_to_line = {}
        
        self.name_to_node = {}
            
    
    def parse(self,url):
        g = GraphMLParser().parse(url)
        self._nodes = g._nodes
        self._edges = g._edges
        self.get_node_labels()
        self.airport_throughput()
        #self.create_nodes()
        #self.create_edges()
        
    def get_node_labels(self): 
        
        for node in self.nodes():
            
            label = node['tooltip'][0:3]
            node['label'] = label
            
            self.name_to_node[label] = node
        
        
        return label 
    
    
    def airport_throughput(self):
        ## Count the throughput of an airport
        self.outgoing = np.zeros(len(self.nodes()),dtype=np.int32)
        self.incoming = np.zeros(len(self.nodes()),dtype=np.int32)
        
        for edge in self.edges():
            self.outgoing[int(edge.node1.id)] += 1   #Outgoing  
            self.incoming[int(edge.node2.id)] += 1   #Incoming
        
        ##Check if size info in node
        try:
            self.nodes()[0]["in"] = self.nodes()[0]["in"]
        except KeyError:
            for node in self.nodes():
                node["in"] = self.incoming[int(node.id)]
                node["out"] = self.outgoing[int(node.id)]

        return self.outgoing,self.incoming
        
        
    def create_nodes(self):
        #Create nodes
        
        for i in self.nodes():
            x = float(i['x'])
            y = float(i['y'])
            #c = colours[int(i.id)]
            
            total = int(i['in']) + int(i['out'])
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
