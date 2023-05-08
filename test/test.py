import tempfile
import os
import sys

sys.path.append("../")

from pygraphml import GraphMLParser
from pygraphml import Graph
import networkx as nx

g = Graph()

n1 = g.add_node("A")
n2 = g.add_node("B")
n3 = g.add_node("C")
n4 = g.add_node("D")
n5 = g.add_node("E")

g.add_edge(n1, n3)
g.add_edge(n2, n3)
g.add_edge(n3, n4)
g.add_edge(n3, n5)

fname = tempfile.mktemp()
parser = GraphMLParser()
parser.write(g, fname)


parser = GraphMLParser()
g = parser.parse("airlines.graphml/airlines.graphml")
print(g.edges()[0].node1,g.edges()[0].node2)
## Access nodes: g.nodes() -> list of nodes

"""
##Edge object
class Edge(Item):
    def __init__(self, node1, node2, directed = False):

        super(Edge, self).__init__()

        self.node1 = node1
        self.node2 = node2

        self.node1._edges.append(self)
        self.node2._edges.append(self)

        self._directed = directed
"""
#g = parser.parse(fname)
#g.show()

#mygraph = nx.read_gml("path.to.file")

