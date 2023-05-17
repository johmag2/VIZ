import tempfile
import os
import sys
import math



sys.path.append("../")
from pygraphml import GraphMLParser
from pygraphml import Graph
import copy

eps = 1e-6
class EdgeBundling():
    def __init__(self,edges):
        # Hyper-parameters
        self.K = 10
        ##Initials
        self.S_initial = 0.4
        self.P_initial = 1
        self.I_initial = 50
        self.C = 6
        ##Rate
        self.S_rate = 0.5
        self.P_rate = 2
        self.I_rate = 0.6666667
        
        self.edges = edges
    
    
    def create_edge_subdivision(self,P=1):
        self.subdivision_points_for_edges = []
        
        for i in range(len(self.edges)):
            self.subdivision_points_for_edges.append(self.edge_subdivision_points(self.edges[i],P))
        
    def edge_subdivision_points(self,edge,P=0):
        node1 = edge.node1
        node2 = edge.node2
        
        if P == 0:
            return [node1,node2]
        else:
            start = node1
            x = float(start['x']) 
            y = float(start['y'])
            end = node2
            list_of_points = [(x,y)]
            
            for i in range(P):
                if i == 1:
                    pass
                x -= (float(start['x']) - float(end['x']))/(P+1)
                y -= (float(start['y']) - float(end['y']))/(P+1)

                list_of_points.append((x,y))

            list_of_points.append((float(end['x']),float(end['y']) ))
            return list_of_points
    
    def update_edge_subdivisions(self,edges, subdivision_points_for_edge, P):
        for edge_idx in range(len(edges)):
            if P == 1:
                return subdivision_points_for_edge
            else:
                divided_edge_length = self.compute_divided_edge_length(subdivision_points_for_edge[edge_idx])
                segment_length = divided_edge_length / (P + 1)
                current_segment_length = segment_length
                new_subdivision_points = list()
                source = edges[edge_idx].node1 # source
                
                new_subdivision_points.append((float(source['x']),float(source['y']))) 
                for i in range(1, len(subdivision_points_for_edge[edge_idx])):
                    old_segment_length = self.distance(subdivision_points_for_edge[edge_idx][i],
                                                            subdivision_points_for_edge[edge_idx][i - 1])
                    while old_segment_length > current_segment_length:
                        percent_position = current_segment_length / old_segment_length
                        new_subdivision_point_x = subdivision_points_for_edge[edge_idx][i - 1][0]
                        new_subdivision_point_y = subdivision_points_for_edge[edge_idx][i - 1][1]

                        new_subdivision_point_x += percent_position * (
                                    subdivision_points_for_edge[edge_idx][i][0] - subdivision_points_for_edge[edge_idx][
                                i - 1][0])
                        new_subdivision_point_y += percent_position * (
                                    subdivision_points_for_edge[edge_idx][i][1] - subdivision_points_for_edge[edge_idx][
                                i - 1][1])
                        new_subdivision_points.append((new_subdivision_point_x, new_subdivision_point_y))

                        old_segment_length -= current_segment_length
                        current_segment_length = segment_length

                    current_segment_length -= old_segment_length

                target = edges[edge_idx].node2  # target
                new_subdivision_points.append((float(target['x']),float(target['y'])))
                subdivision_points_for_edge[edge_idx] = new_subdivision_points

        return subdivision_points_for_edge

    def compute_divided_edge_length(self,edge):
        tot_len = 0
        for i in range(1,len(edge)):
            tot_len += self.distance(edge[i-1],edge[i])
        
        return tot_len
        
    def edge_length(self,edge):
        ##Return euclidian distance of edge
        node1 = edge.node1
        node2 = edge.node2
        x1 = float(node1['x'])
        y1 = float(node1['y'])
        x2 = float(node2['x'])
        y2 = float(node2['y'])
        
        return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))

    def distance(self,point1,point2):
        if (abs(point1[0] - point2[0])) < eps and (abs(point1[1] - point2[1])) < eps:
            return eps
    
        return math.sqrt(math.pow(point1[0] - point2[0], 2) + math.pow(point1[1] - point2[1], 2))
    
    def get_spring_force(self,edge_points, edge_idx, point_id, kP):
        ##Compute spring forces
        prev_p = edge_points[point_id - 1]
        next_p = edge_points[point_id + 1]
        current = edge_points[point_id]
        dist = self.distance(prev_p,current)
        
        fs1_x = (prev_p[0]-current[0]) #/dist
        #fs1_x = 0 if fs1_x < 0 else fs1_x
        fs1_y = (prev_p[1]-current[1]) #/dist
        #fs1_y = 0 if fs1_y < 0 else fs1_y
        
        fs2_x = -(current[0]-next_p[0]) #/dist
        #fs2_x = 0 if fs2_x < 0 else fs2_x
        fs2_y = -(current[1]-next_p[1]) #/dist
        #fs2_y = 0 if fs2_y < 0 else fs2_y
        
        force_x = kP * (fs1_x + fs2_x)
        force_y = kP * (fs1_y + fs2_y)
        
        return (force_x, force_y)

    def get_electrostatic_force(self,edge_points, edge_idx, i):
        ##Compute electostatic forces
        sum_of_forces_x = 0.0
        sum_of_forces_y = 0.0
        compatible_edges_list = self.compatibility_list_for_edge[edge_idx]
        
        current_point = edge_points[i]
        for oe_id in range(len(compatible_edges_list)):
            o_point = compatible_edges_list[oe_id][i] #compatible_edges_list
            force_x = current_point[0] - o_point[0]
            force_y = current_point[1] - o_point[1]
            dist = self.distance(current_point,o_point)
            
            if dist > eps:
                sum_of_forces_x -= force_x/dist
            if dist > eps:
                sum_of_forces_y -= force_y/dist

        return (sum_of_forces_x, sum_of_forces_y)    
    
    def compute_compatibility_list(self):
        ##To Do: Only return other compatible edges
        self.compatibility_list_for_edge = []
        
        for e_id in range(len(self.edges)):
            o_list = copy.copy(self.subdivision_points_for_edges)
            del o_list[e_id]
            
            self.compatibility_list_for_edge.append(o_list)
        
        
    def forcebundle(self):
        self.S = self.S_initial
        self.I = self.I_initial
        self.P = self.P_initial

        self.create_edge_subdivision(self.P)    ##Creates self.subdivision_points_for_edges
        self.compute_compatibility_list() #self.compatibility_list_for_edge = self.subdivision_points_for_edges #compute_compatibility_list(edges)
        #subdivision_points_for_edge = update_edge_divisions(edges, subdivision_points_for_edge, P)

        for _cycle in range(self.C):
            
            for iteration in range(math.ceil(self.I)):
                
                for e_id,edge in enumerate(self.subdivision_points_for_edges):
                    edge_movements = self.calculate_edge_forces(edge,e_id)
                    
                    for i in range(1,self.P+1):
                        point = self.subdivision_points_for_edges[e_id][i]
                        new_x = point[0] + edge_movements[i-1][0]
                        new_y = point[1] + edge_movements[i-1][1]
                        self.subdivision_points_for_edges[e_id][i] = (new_x,new_y)
    
                        #print(self.distance(point,(new_x,new_y)))
                
            
            self.S *= self.S_rate
            self.I *= self.I_rate
            self.P *= self.P_rate
            
            self.subdivision_points_for_edge = self.update_edge_subdivisions(self.edges, self.subdivision_points_for_edges, self.P)
            self.compute_compatibility_list()
            #print(self.subdivision_points_for_edges[0])
            
        #[print(point[1]) for point in self.subdivision_points_for_edges]
        
        return self.subdivision_points_for_edges
    
    def calculate_edge_forces(self,edge,edge_id):
        edge_forces = []
        #self.K = 1
        kP = self.K / (self.edge_length(self.edges[edge_id]) * (self.P+1))
        
        for i in range(1,len(edge)-1):
            
            F_s = self.get_spring_force(edge,edge_id,i,kP)
            F_e = self.get_electrostatic_force(edge,edge_id,i) 
            
            F_x = self.S * (F_s[0] + F_e[0])
            F_y = self.S * (F_s[1] + F_e[1])
            edge_forces.append((F_x,F_y))
        
        return edge_forces
    

if __name__ == "__main__":
    parser = GraphMLParser()
    g = parser.parse("airlines.graphml/airlines.graphml")
    edge = g.edges()[0]
    node1 = edge.node1
    node2 = edge.node2
    g.show()
    #split_edge(edge)
