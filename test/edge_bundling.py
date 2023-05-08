import tempfile
import os
import sys
import math

sys.path.append("../")
from pygraphml import GraphMLParser
from pygraphml import Graph

# Hyper-parameters
#
# global bundling constant controlling edge stiffness
K = 0.1
# initial distance to move points
S_initial = 0.1
# initial subdivision number
P_initial = 1
# subdivision rate increase
P_rate = 2
# number of cycles to perform
C = 6
# initial number of iterations for cycle
I_initial = 90
# rate at which iteration number decreases i.e. 2/3
I_rate = 0.6666667

def split_edge(edge,n):
    
    
    return

def edge_length(edge):
    ##Return euclidian distance of edge
    node1 = edge.node1
    node2 = edge.node2
    x1 = float(node1['x'])
    y1 = float(node1['y'])
    x2 = float(node2['x'])
    y2 = float(node2['y'])
    
    return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))


if __name__ == "__main__":
    parser = GraphMLParser()
    g = parser.parse("airlines.graphml/airlines.graphml")
    edge = g.edges()[0]
    node1 = edge.node1
    node2 = edge.node2
    g.show()
    #split_edge(edge)
    print(edge_length(edge))
