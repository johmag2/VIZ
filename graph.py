from pygraphml import GraphMLParser 
from pygraphml import Graph as pyGraph
import numpy as np

class graph(pyGraph):
    def __init__(self,g=None):
        super(graph,self).__init__()
        
        if isinstance(g, pyGraph):
            self._nodes = g._nodes
            self._edges = g._edges
            self.get_node_labels()
    
            
    
    def parse(self,url):
        g = GraphMLParser().parse(url)
        self._nodes = g._nodes
        self._edges = g._edges
        self.get_node_labels()
        
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
        
        
        
def main():
    pyG = GraphMLParser().parse("airlines.graphml/airlines.graphml")
    g = graph()
    
if __name__ == "__main__":
    main()
