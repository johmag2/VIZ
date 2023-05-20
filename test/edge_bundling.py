import tempfile
import os
import sys
import math
import numpy as np

sys.path.append("../")
from pygraphml import GraphMLParser
from pygraphml import Graph,Node,Edge
import copy
import time

from numba.experimental import jitclass
from numba import float32, jit, prange, float64, njit
from numba.typed import List
from numba.types import ListType, int16, uint8
#from tqdm.auto import tqdm

FASTMATH = True
eps = 1e-6
K = 0.5 ##Bundling constant for spring force

##Initials
S_initial = 0.4 #point distance move
P_initial = 1
I_initial = 50
C = 6
##Rate
S_rate = 0.5
P_rate = 2  #Increase of subdivisions
I_rate = 0.6666667

@jitclass([('x', float32), ('y', float32)])
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


@jitclass([('source', Point.class_type.instance_type), ('target', Point.class_type.instance_type),('id',int16)])
class Edge:
    def __init__(self, source, target,edge_id):
        self.source = source
        self.target = target
        self.id = edge_id

Force = Point

pt_cls = Point.class_type.instance_type
#list_of_points = ListType(pt_cls)
@njit(fastmath=FASTMATH)
def edge_subdivision_points(edge,P=0):
    list_of_points = List.empty_list(pt_cls)
    if P == 0:
        list_of_points.append(edge.source)
        list_of_points.append(edge.target)
        return list_of_points
    else:
        start = edge.source
        x = start.x
        y = start.y
        end = edge.target
        list_of_points.append(edge.source)
        
        for i in range(P):
            if i == 1:
                pass
            x -= (start.x - end.x)/(P+1)
            y -= (start.y - end.y)/(P+1)
            
            list_of_points.append(Point(x,y))

        list_of_points.append(edge.target)
        
        return list_of_points
    
pt_cls = Point.class_type.instance_type
list_of_pts = ListType(pt_cls)
@njit(fastmath=FASTMATH)
def create_edge_subdivision(edges,P=1):
    subdivision_points_for_edges = List.empty_list(list_of_pts)
    
    for i in range(len(edges)):
        subdivision_points_for_edges.append(edge_subdivision_points(edges[i],P))
        
    return subdivision_points_for_edges

@njit(fastmath=FASTMATH)
def update_edge_subdivisions(edges, subdivision_points_for_edge, P):
    for edge_idx in range(len(edges)):
        if P == 1:
            return subdivision_points_for_edge
        else:
            edge = subdivision_points_for_edge[edge_idx]
            divided_edge_length = compute_divided_edge_length(edge)
            segment_length = divided_edge_length / (P + 1)
            current_segment_length = segment_length
            new_subdivision_points = List()
            new_subdivision_points.append(edges[edge_idx].source)  # source
            for i in range(1, len(subdivision_points_for_edge[edge_idx])):
                old_segment_length = distance(subdivision_points_for_edge[edge_idx][i],
                                                        subdivision_points_for_edge[edge_idx][i - 1])
                while old_segment_length > current_segment_length:
                    percent_position = current_segment_length / old_segment_length
                    new_subdivision_point_x = subdivision_points_for_edge[edge_idx][i - 1].x
                    new_subdivision_point_y = subdivision_points_for_edge[edge_idx][i - 1].y

                    new_subdivision_point_x += percent_position * (
                                subdivision_points_for_edge[edge_idx][i].x - subdivision_points_for_edge[edge_idx][
                            i - 1].x)
                    new_subdivision_point_y += percent_position * (
                                subdivision_points_for_edge[edge_idx][i].y - subdivision_points_for_edge[edge_idx][
                            i - 1].y)
                    new_subdivision_points.append(Point(new_subdivision_point_x, new_subdivision_point_y))

                    old_segment_length -= current_segment_length
                    current_segment_length = segment_length

                current_segment_length -= old_segment_length

            target = edges[edge_idx].target
            new_subdivision_points.append(target)  # target
            subdivision_points_for_edge[edge_idx] = new_subdivision_points

    return subdivision_points_for_edge


@njit(fastmath=FASTMATH)
def compute_divided_edge_length(edge):
    tot_len = 0.0
    for i in range(1,len(edge)):
        tot_len += distance(edge[i-1],edge[i])
    
    return tot_len
    
@njit(fastmath=FASTMATH)
def edge_length(edge):
    ##Return euclidian distance of edge
    source = edge.source
    target = edge.target
    x1 = source.x
    y1 = source.y
    x2 = target.x
    y2 = target.y
    
    if (abs(x1 - x2)) < eps and (abs(y1 - y2)) < eps:
        return eps
    
    return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))

@njit(fastmath=FASTMATH)
def distance(point1,point2):
    if (abs(point1.x - point2.x)) < eps and (abs(point1.y - point2.y)) < eps:
        return eps

    return math.sqrt(math.pow(point1.x - point2.x, 2) + math.pow(point1.y - point2.y, 2))

@njit(fastmath=FASTMATH)    
def get_spring_force(edge_points, edge_idx, point_id, kP):
    prev = edge_points[point_id - 1]
    next_ = edge_points[point_id + 1]
    crnt = edge_points[point_id]
    x = prev.x - crnt.x + next_.x - crnt.x
    x = x if x >= 0 else 0.
    y = prev.y - crnt.y + next_.y - crnt.y
    y = y if y >= 0 else 0.

    x *= kP
    y *= kP

    return Force(x, y)

    ##Compute spring forces
    prev_p = edge_points[point_id - 1]
    next_p = edge_points[point_id + 1]
    current = edge_points[point_id]
    dist = distance(prev_p,current)
    
    fs1_x = (prev_p.x-current.x)
    #fs1_x = 0 if fs1_x < 0 else fs1_x
    fs1_y = (prev_p.y-current.y)
    #fs1_y = 0 if fs1_y < 0 else fs1_y
    
    fs2_x = -(current.x-next_p.x)
    #fs2_x = 0 if fs2_x < 0 else fs2_x
    fs2_y = -(current.y-next_p.y)
    #fs2_y = 0 if fs2_y < 0 else fs2_y
    
    force_x = kP * (fs1_x + fs2_x)
    force_y = kP * (fs1_y + fs2_y)
    #print(fs1_x,fs2_x)
    return Force(force_x, force_y)

@njit(fastmath=FASTMATH)
def custom_edge_length(edge):
    return math.sqrt(math.pow(edge.source.x - edge.target.x, 2) + math.pow(edge.source.y - edge.target.y, 2))

@njit(fastmath=FASTMATH)
def get_electrostatic_force(subdivision_points_for_edges,compatible_edges_list,edge_points, edge_idx, i):
    
    ##Compute electostatic forces
    sum_of_forces_x = 0.0
    sum_of_forces_y = 0.0
    
    #compatible_edges_list = compatibility_list_for_edge[edge_idx]
    current_point = edge_points[i]
    
    for oe_id in range(len(compatible_edges_list)):
        other_edge_id = compatible_edges_list[oe_id]#[0]
        #score = compatible_edges_list[oe_id][1]
        o_point = subdivision_points_for_edges[other_edge_id[i]] #compatible_edges_list
        
        force_x = o_point.x - current_point.x
        force_y = o_point.y - current_point.y
        
        #print(dist)
        if (math.fabs(force_x) > eps) or (math.fabs(force_y) > eps):
            divisor = custom_edge_length(Edge(o_point,current_point,-1))
            diff = 1/divisor
            #dist = distance(current_point,o_point)

            sum_of_forces_x += force_x * diff #/ dist**2
            sum_of_forces_y += force_y * diff #/ dist**2
            
    #print(sum_of_forces_x, sum_of_forces_y) 
        
    return Force(sum_of_forces_x, sum_of_forces_y)    
  
def compute_compatibility_list(edges):
    ##To Do: Only return other compatible edges
    
    compatibility_list_for_edge = List()
    
    for _ in edges:
        compatibility_list_for_edge.append(List.empty_list(int16))
        
    comp_thresh = 0.1
    processed_edges = 0
    
    for edge in edges:
        e_id = edge.id
        
        for oedge in edges[processed_edges:]:
            o_id = oedge.id
            
            if e_id != o_id:
                
                score = compatibility_score(edge,oedge)
                #print(score)    
                if score >= comp_thresh:
                    compatibility_list_for_edge[int(e_id)].append(o_id)#(o_id,score))
                    compatibility_list_for_edge[int(o_id)].append(e_id)#(e_id,score))
                    
                    
        processed_edges += 1
    #compatibility_list_for_edge = np.array(compatibility_list_for_edge) 
    #print(compatibility_list_for_edge)
    return compatibility_list_for_edge
     
@njit(fastmath=FASTMATH)     
def edge_as_vector(edge):
    source = edge.source
    target = edge.target
    x1 = source.x
    y1 = source.y
    x2 = target.x
    y2 = target.y
    return Point(x2-x1,y2-y1)
 
@njit(fastmath=FASTMATH)   
def compatibility_score(edge,oedge):
    return 1
    vec = edge_as_vector(edge)
    edge_len = edge_length(edge)
    o_vec = edge_as_vector(oedge)
    oe_len = edge_length(oedge)
    
    source_point = edge.source
    target_point = edge.target
    osource_point = edge.source
    otarget_point = oedge.target
    
    ## Angle compatibility
    dot_prod = vec.x*o_vec.x + vec.y*o_vec.y
    angle_score = math.fabs(dot_prod/(edge_len * oe_len))
    
    ## Scale comp
    avg_len = (edge_len+oe_len)/2.0
    scale_score = 2.0 / (avg_len/min(edge_len, oe_len) + max(edge_len, oe_len)/avg_len)
    
    ## Position comp
    midP = Point((source_point.x + target_point.x) / 2.0, (source_point.y + target_point.y) / 2.0)
    midQ = Point((osource_point.x + oedge.target.x) / 2.0,(osource_point.y + otarget_point.y) / 2.0)
    pos_score =  avg_len / (avg_len + distance(midP, midQ))
    
    ## vis comp
    """
    I0 = project_point_on_line(osource_point,source_point,target_point)
    I1 = project_point_on_line(otarget_point,source_point,target_point)
    dist = distance(I0,I1)
    midI = ((I0.x + I1.x) / 2.0, (I0.y + I1.y) / 2.0)
    V_pq = max(0, 1 - 2 * distance(midP, midI) / dist)
    
    I0 = project_point_on_line(source_point,osource_point,otarget_point)
    I1 = project_point_on_line(target_point,osource_point,otarget_point)
    dist = distance(I0,I1)
    midI = ((I0.x + I1.x) / 2.0, (I0.y + I1.y) / 2.0)
    V_qp = max(0, 1 - 2 * distance(midQ, midI) / dist)
    #print(V_pq,V_qp)
    vis_score = min(V_pq,V_qp)
    """
    vis_score = 1
    #print(angle_score,scale_score,pos_score)
    
    
    return angle_score*scale_score*pos_score*vis_score

@njit(fastmath=FASTMATH)   
def project_point_on_line(point, edge_source_point,edge_target_point):
    
    L = math.sqrt(math.pow(edge_target_point.x - edge_source_point.x, 2) + math.pow((edge_target_point.y - edge_source_point.y), 2))
    r = ((edge_target_point.y - point.y) * (edge_source_point.y - edge_target_point.y) - 
            (edge_source_point.x - point.x) * (edge_target_point.x - edge_source_point.x)) / math.pow(L, 2)
    
    return (edge_source_point.x + r * (edge_target_point.x - edge_source_point.x),
            edge_source_point.y + r * (edge_target_point.y - edge_source_point.y))
        
def forcebundle(edges):
    S = S_initial
    I = I_initial
    P = P_initial

    subdivision_points_for_edges = create_edge_subdivision(edges,P)    ##Creates subdivision_points_for_edges
    compatibility_list_for_edge = compute_compatibility_list(edges) #compatibility_list_for_edge = subdivision_points_for_edges #compute_compatibility_list(edges)
    #subdivision_points_for_edge = update_edge_divisions(edges, subdivision_points_for_edge, P)

    for cycle in range(C):
        print("Cycle:{}".format(cycle))
        for iteration in range(math.ceil(I)):
            
            for e_id,edge in enumerate(subdivision_points_for_edges):
                edge_movements = calculate_edge_forces(subdivision_points_for_edges,compatibility_list_for_edge,
                                                       edges,edge,e_id,S,P)
                
                for i in range(1,P+1):
                    point = subdivision_points_for_edges[e_id][i]
                    new_x = point.x + edge_movements[i-1].x
                    new_y = point.y + edge_movements[i-1].y
                    subdivision_points_for_edges[e_id][i] = Point(new_x,new_y)

                    #print(distance(point,(new_x,new_y)))  
        
        S *= S_rate
        I *= I_rate
        P = round(P * P_rate)
        
        subdivision_points_for_edges = update_edge_subdivisions(edges, subdivision_points_for_edges, P)
        
        #print(subdivision_points_for_edges.x)
        
    #[print(point[1]) for point in subdivision_points_for_edges]
    
    return subdivision_points_for_edges
    
    
def forcebundle_step(edges,subdivision_points_for_edges,compatibility_list_for_edge,S=S_initial,I=I_initial,P=P_initial):
    t = time.time()
    print("Step")
    #for iteration in range(math.ceil(10)): #I)):
            
    for e_id,edge in enumerate(subdivision_points_for_edges):
        edge_movements = calculate_edge_forces(subdivision_points_for_edges,compatibility_list_for_edge,
                                                       edges,edge,e_id,S,P)
            
        for i in range(1,P+1):
            point = subdivision_points_for_edges[e_id][i]
            new_x = point.x + edge_movements[i-1].x
            new_y = point.y + edge_movements[i-1].y
            subdivision_points_for_edges[e_id][i] = Point(new_x,new_y)

              
    print("Time elapsed: {}".format(time.time()-t))       
    
@njit(fastmath=FASTMATH)                        
def calculate_edge_forces(subdivision_points_for_edges,compatibility_list_for_edge,edges,edge,edge_id,S,P):
    edge_forces = []
    
    kP = K / (edge_length(edges[edge_id]) * (P+1))
    
    for i in range(1,len(edge)-1):
        
        F_s = get_spring_force(edge,edge_id,i,kP)
        compatible_edges = compatibility_list_for_edge[edge_id]
        F_e = get_electrostatic_force(subdivision_points_for_edges,compatible_edges,edge,edge_id,i) 
        #F_s = (0,0)
        #if edge_id == 219:
        #    print(F_s,'\n',F_e,'\n')
            
        F_x = S * (F_s.x + F_e.x)
        F_y = S * (F_s.y + F_e.y)
        
        if math.fabs(F_x) > 1000 or math.fabs(F_y) > 1000:
            print((F_s,F_e))
            
        edge_forces.append(Force(F_x,F_y))
    
    return edge_forces

@jit(nopython=True, fastmath=FASTMATH)
def is_long_enough(edge):
    # Zero length edges
    if (edge.source.x == edge.target.x) or (edge.source.y == edge.target.y):
        return False
    # No EPS euclidean distance
    raw_lenght = math.sqrt(math.pow(edge.target.x - edge.source.x, 2) + math.pow(edge.target.y - edge.source.y, 2))
    if raw_lenght < (eps * P_initial * P_rate * C):
        return False
    else:
        return True
        
edge_class = Edge.class_type.instance_type
@njit(fastmath=FASTMATH)
def get_empty_edge_list():
    return List.empty_list(edge_class)

def graph2edges(graph):
    edges = get_empty_edge_list()
    for edge in graph.edges():
        
        source = edge.node1
        source = Point(float32(source['x']), float32(source['y']))
        
        target = edge.node2
        target = Point(float32(target['x']), float32(target['y']))
        edge = Edge(source, target,int16(edge.id))
        #print(type(target))
        if is_long_enough(edge):
            edges.append(edge)

    return edges

if __name__ == "__main__":
    parser = GraphMLParser()
    g = parser.parse("airlines.graphml/airlines.graphml")
    edge = g.edges()[0]
    node1 = edge.node1
    node2 = edge.node2
    g.show()
    #split_edge(edge)
