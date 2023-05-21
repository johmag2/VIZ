from numba import float32, jit, prange, float64, njit
from numba.experimental import jitclass
from numba.typed import List
from numba.types import ListType,int64
from tqdm.auto import tqdm
import math

# Parameters


K = 10 # Bundling constant. Affects string force. Dont put too (?) large

C = 6   #Amount of cycles 
## initials
I_initial = 50  #Amount of iterations
P_initial = 1   #Subdivision amount
S_initial = 0.4 #Point move 

## Changing rates
P_rate = 1.75 #2      #With P_rate = 1.75 it will go [1,2,4,7,12,21]
I_rate = 0.6666667
S_rate = 0.5

compatibility_threshold = 0.2
eps = 1e-6

# Numba Jit Execution settings
FASTMATH = True

@jitclass([('x', float32), ('y', float32)])
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


@jitclass([('source', Point.class_type.instance_type), ('target', Point.class_type.instance_type),('id', int64)])
class Edge:
    def __init__(self, source, target,id):
        self.source = source
        self.target = target
        self.id = id

Force = Point

@njit(fastmath=FASTMATH)
def distance(source, target):
    return math.sqrt(math.pow(source.x - target.x, 2) + math.pow(source.y - target.y, 2))


@njit(fastmath=FASTMATH)
def project_point_on_line(point, edge):
    L = math.sqrt(math.pow(edge.target.x - edge.source.x, 2) + math.pow((edge.target.y - edge.source.y), 2))
    r = ((edge.source.y - point.y) * (edge.source.y - edge.target.y) - (edge.source.x - point.x) * (edge.target.x - edge.source.x)) / math.pow(L, 2)
    return Point((edge.source.x + r * (edge.target.x - edge.source.x)),
                 (edge.source.y + r * (edge.target.y - edge.source.y)))


@njit(fastmath=FASTMATH)
def edge_visibility(edge, oedge):
    # send actual edge points positions
    I0 = project_point_on_line(oedge.source, edge)
    I1 = project_point_on_line(oedge.target, edge)
    divisor = distance(I0, I1)
    divisor = divisor if divisor != 0 else eps

    midI = Point((I0.x + I1.x) / 2.0, (I0.y + I1.y) / 2.0)

    midP = Point((edge.source.x + edge.target.x) / 2.0,
                 (edge.source.y + edge.target.y) / 2.0)

    return max(0, 1 - 2 * distance(midP, midI) / divisor)

@njit(fastmath=FASTMATH)
def compatiblity_score(edge, oedge):
    
    edge_dist = distance(edge.source,edge.target)
    oedge_dist = distance(oedge.source,oedge.target)
    
    P_x = edge.target.x - edge.source.x
    P_y = edge.target.y - edge.source.y
    Q_x = oedge.target.x - oedge.source.x
    Q_y = oedge.target.y - oedge.source.y
    
    dot_prod = P_x * Q_x + P_y * Q_y
    angles_score =  math.fabs(dot_prod / (edge_dist * oedge_dist))
    
    lavg = (edge_dist + oedge_dist) / 2.0
    scales_score = 2.0 / (lavg/min(edge_dist, oedge_dist) + max(edge_dist, oedge_dist)/lavg)
    
    midP = Point((edge.source.x + edge.target.x) / 2.0,
                (edge.source.y + edge.target.y) / 2.0)
    midQ = Point((oedge.source.x + oedge.target.x) / 2.0,
                    (oedge.source.y + oedge.target.y) / 2.0)
        
    positi_score = lavg / (lavg + distance(midP, midQ))
    
    visivi_score = min(edge_visibility(edge, oedge), edge_visibility(oedge, edge))

    score = (angles_score * scales_score * positi_score * visivi_score)

    return score


def compute_compatible_list(edges):
    compatible_list = List()
    scores = List()
    for _ in edges:
        compatible_list.append(List.empty_list(int64))
        scores.append(List.empty_list(float64))

    processed_edges = 0
    for edge_id in tqdm(range(len(edges) - 1), unit='Edges'):
        edge = edges[edge_id]
        
        for oedge in edges[processed_edges:]:
            oe_id = oedge.id
            
            if edge_id != oe_id:
                
                score = compatiblity_score(edge,oedge)
                #print(score)    
                
                if score >= compatibility_threshold:
                    compatible_list[edge_id].append(oe_id)
                    compatible_list[oe_id].append(edge_id)
                    
                    scores[edge_id].append(score)
                    scores[oe_id].append(score)
                    
                    
        processed_edges += 1
        
    return compatible_list,scores

pt_cls = Point.class_type.instance_type
list_of_pts = ListType(pt_cls)
@njit(fastmath=FASTMATH)
def create_edge_subdivision(edges,P=1):
    subdivision_points_for_edges = List.empty_list(list_of_pts)
    
    for i in range(len(edges)):
        list_of_points = List.empty_list(pt_cls)
        
        edge = edges[i]
        if P == 0:
            list_of_points.append(edge.source)
            list_of_points.append(edge.target)
            subdivision_points_for_edges.append(list_of_points)
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
            
            subdivision_points_for_edges.append(list_of_points)
        
    return subdivision_points_for_edges

@njit(fastmath=FASTMATH)
def update_edge_divisions(edges, subdivision_points_for_edge, P):
    for edge_idx in range(len(edges)):
        
        edge = subdivision_points_for_edge[edge_idx]
        divided_edge_length = 0.0
        for i in range(1,len(edge)):
            divided_edge_length += distance(edge[i-1],edge[i])
        
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

        new_subdivision_points.append(edges[edge_idx].target)  # target
        subdivision_points_for_edge[edge_idx] = new_subdivision_points

    return subdivision_points_for_edge

@njit(fastmath=FASTMATH)
def get_spring_force(edge, i, kP):
    prev_p = edge[i - 1]
    next_p = edge[i + 1]
    current = edge[i]
    
    fs1_x = (prev_p.x-current.x)
    fs1_y = (prev_p.y-current.y)
    
    fs2_x = -(current.x-next_p.x)
    fs2_y = -(current.y-next_p.y)
    
    force_x = kP * (fs1_x + fs2_x)
    force_y = kP * (fs1_y + fs2_y)
    #print(fs1_x,fs2_x)
    return Force(force_x, force_y)

@njit(fastmath=FASTMATH)
def get_electrostatic_force(subdivision_points_for_edge, compatible_edges_list,scores, edge_idx, i):
    ##Compute electostatic forces
    sum_of_forces_x = 0.0
    sum_of_forces_y = 0.0
    
    current_point = subdivision_points_for_edge[edge_idx][i]
    
    for oe in range(len(compatible_edges_list)):
        other_edge = subdivision_points_for_edge[compatible_edges_list[oe]]
        other_point = other_edge[i]
        #print(edge_idx,other_edge)
        score = scores[edge_idx][oe]
    
        force_x = other_point.x - current_point.x
        force_y = other_point.y - current_point.y
        
        if (math.fabs(force_x) > eps) or (math.fabs(force_y) > eps):
            divisor = distance(other_point, current_point)
            diff = (score / divisor)

            sum_of_forces_x += score * force_x * diff
            sum_of_forces_y += score * force_y * diff

    return Force(sum_of_forces_x, sum_of_forces_y)

@njit(fastmath=FASTMATH)
def calculate_edge_forces(edge, subdivision_points_for_edge, compatable_edges_list,scores, edge_idx, K, P, S):
    
    kP = K / (distance(edge.source,edge.target) * (P + 1))
    current_edge = subdivision_points_for_edge[edge_idx]
    compatible_edges = compatable_edges_list[edge_idx]
    
    forces_on_edge = List()

    for i in range(1, P + 1): #The node positions
        spring_force = get_spring_force(current_edge, i, kP)
        electrostatic_force = get_electrostatic_force(subdivision_points_for_edge, compatible_edges,scores, edge_idx, i)

        force_tot_x = S * (spring_force.x + electrostatic_force.x)
        force_tot_y = S * (spring_force.y + electrostatic_force.y)
        
        forces_on_edge.append(Force(force_tot_x,force_tot_y))

    return forces_on_edge

def forcebundle(edges):
    ##Set cycle parameters to initials
    S = S_initial
    I = I_initial
    P = P_initial

    ##Create starting points
    print("Compute compatibilities:")
    compatable_edges_list,scores = compute_compatible_list(edges)
    subdivision_points_for_edge = create_edge_subdivision(edges,1)

    print("Starting force-bundling cycles:")
    for _cycle in tqdm(range(C), unit='cycle'):
        
        for iteration in range(math.ceil(I)):
            
            for edge_idx in range(len(edges)):
                edge = edges[edge_idx]
                edge_movements = calculate_edge_forces(edge, subdivision_points_for_edge,compatable_edges_list,scores,
                                                       edge_idx,K, P, S)
                
                for i in range(len(edge_movements)):
                    current_point = subdivision_points_for_edge[edge_idx][i+1]  #i+1 -> skip node position
                    new_x = current_point.x + edge_movements[i].x   #Move x pos
                    new_y = current_point.y + edge_movements[i].y   #Move y pos
                    subdivision_points_for_edge[edge_idx][i+1] = Point(new_x,new_y) #Update position
        
        ##Increment S,I,P
        S *= S_rate
        I *= I_rate
        P = round(P * P_rate) 
        
        subdivision_points_for_edge = update_edge_divisions(edges, subdivision_points_for_edge, P)
        
    
    return subdivision_points_for_edge

##Not sure why necessary. Error if done within convert_edges
edge_class = Edge.class_type.instance_type
@njit
def get_empty_edge_list():
    return List.empty_list(edge_class)


def convert_edges(graph):
    edges = get_empty_edge_list()
    for edge in graph.edges():
        
        source = edge.node1
        source = Point(float32(source['x']), float32(source['y']))
        
        target = edge.node2
        target = Point(float32(target['x']), float32(target['y']))
        
        edge = Edge(source, target,int(edge.id))
        edges.append(edge)

    return edges

