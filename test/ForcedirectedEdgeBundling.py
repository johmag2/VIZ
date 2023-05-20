from numba import float32, jit, prange, float64, njit
from numba.experimental import jitclass
from numba.typed import List
from numba.types import ListType,int64
from tqdm.auto import tqdm
import math

# Parameters


K = 1 # Bundling constant. Affects string force

C = 6   #Amount of cycles 
## initials
I_initial = 50  #Amount of iterations
P_initial = 1   #Subdivision amount
S_initial = 0.2 #Point move 

## Changing rates
P_rate = 2
I_rate = 0.6666667
S_rate = 0.5

compatibility_threshold = 0.5
eps = 1e-6

# Numba Jit Execution settings
FASTMATH = True

@jitclass([('x', float32), ('y', float32)])
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


@jitclass([('source', Point.class_type.instance_type), ('target', Point.class_type.instance_type)])
class Edge:
    def __init__(self, source, target):
        self.source = source
        self.target = target


ForceFactors = Point


@njit(fastmath=FASTMATH)
def edge_as_vector(edge):
    return Point(edge.target.x - edge.source.x, edge.target.y - edge.source.y)


@njit(fastmath=FASTMATH)
def edge_length(edge):
    # handling nodes that are the same location, so that K / edge_length != Inf
    if (abs(edge.source.x - edge.target.x)) < eps and (abs(edge.source.y - edge.target.y)) < eps:
        return eps

    return math.sqrt(math.pow(edge.source.x - edge.target.x, 2) + math.pow(edge.source.y - edge.target.y, 2))


@njit(fastmath=FASTMATH)
def angle_compatibility(edge, oedge):
    v1 = edge_as_vector(edge)
    v2 = edge_as_vector(oedge)
    dot_product = v1.x * v2.x + v1.y * v2.y
    return math.fabs(dot_product / (edge_length(edge) * edge_length(oedge)))


@njit(fastmath=FASTMATH)
def scale_compatibility(edge, oedge):
    lavg = (edge_length(edge) + edge_length(oedge)) / 2.0
    return 2.0 / (lavg/min(edge_length(edge), edge_length(oedge)) + max(edge_length(edge), edge_length(oedge))/lavg)


@njit(fastmath=FASTMATH)
def euclidean_distance(source, target):
    return math.sqrt(math.pow(source.x - target.x, 2) + math.pow(source.y - target.y, 2))


@njit(fastmath=FASTMATH)
def position_compatibility(edge, oedge):
        lavg = (edge_length(edge) + edge_length(oedge)) / 2.0
        midP = Point((edge.source.x + edge.target.x) / 2.0,
                (edge.source.y + edge.target.y) / 2.0)
        midQ = Point((oedge.source.x + oedge.target.x) / 2.0,
                     (oedge.source.y + oedge.target.y) / 2.0)

        return lavg / (lavg + euclidean_distance(midP, midQ))

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
    divisor = euclidean_distance(I0, I1)
    divisor = divisor if divisor != 0 else eps

    midI = Point((I0.x + I1.x) / 2.0, (I0.y + I1.y) / 2.0)

    midP = Point((edge.source.x + edge.target.x) / 2.0,
                 (edge.source.y + edge.target.y) / 2.0)

    return max(0, 1 - 2 * euclidean_distance(midP, midI) / divisor)


@njit(fastmath=FASTMATH)
def visibility_compatibility(edge, oedge):
    return min(edge_visibility(edge, oedge), edge_visibility(oedge, edge))

@njit(fastmath=FASTMATH)
def are_compatible(edge, oedge):
    angles_score = angle_compatibility(edge, oedge)
    scales_score = scale_compatibility(edge, oedge)
    positi_score = position_compatibility(edge, oedge)
    visivi_score = visibility_compatibility(edge, oedge)

    score = (angles_score * scales_score * positi_score * visivi_score)

    return score


# No numba, so we have tqdm
def compute_compatibility_list(edges):
    compatibility_list = List()
    scores = List()
    for _ in edges:
        compatibility_list.append(List.empty_list(int64))
        scores.append(List.empty_list(float64))

    total_edges = len(edges)
    for e_idx in tqdm(range(total_edges - 1), unit='Edges'):
        compatibility_list,scores = compute_compatibility_list_on_edge(edges, e_idx, compatibility_list,scores, total_edges)

    return compatibility_list,scores

@njit(fastmath=FASTMATH)
def compute_compatibility_list_on_edge(edges, e_idx, compatibility_list,scores, total_edges):
    for oe_idx in range(e_idx + 1, total_edges):
        score = are_compatible(edges[e_idx], edges[oe_idx])
        if score >= compatibility_threshold:
            compatibility_list[e_idx].append(oe_idx)
            compatibility_list[oe_idx].append(e_idx)
            
            scores[e_idx].append(score)
            scores[oe_idx].append(score)
            
    return compatibility_list,scores

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
def compute_divided_edge_length(subdivision_points_for_edge, edge_idx):
    length = 0
    for i in prange(1, len(subdivision_points_for_edge[edge_idx])):
        segment_length = euclidean_distance(subdivision_points_for_edge[edge_idx][i],
                                            subdivision_points_for_edge[edge_idx][i - 1])
        length += segment_length

    return length

@njit(fastmath=FASTMATH)
def edge_midpoint(edge):
    middle_x = (edge.source.x + edge.target.x) / 2
    middle_y = (edge.source.y + edge.target.y) / 2

    return Point(middle_x, middle_y)


@njit(fastmath=FASTMATH)
def update_edge_divisions(edges, subdivision_points_for_edge, P):
    for edge_idx in range(len(edges)):
        if P == 1:
            subdivision_points_for_edge[edge_idx].append(edges[edge_idx].source)
            subdivision_points_for_edge[edge_idx].append(edge_midpoint(edges[edge_idx]))
            subdivision_points_for_edge[edge_idx].append(edges[edge_idx].target)
        else:
            divided_edge_length = compute_divided_edge_length(subdivision_points_for_edge, edge_idx)
            segment_length = divided_edge_length / (P + 1)
            current_segment_length = segment_length
            new_subdivision_points = List()
            new_subdivision_points.append(edges[edge_idx].source)  # source
            for i in range(1, len(subdivision_points_for_edge[edge_idx])):
                old_segment_length = euclidean_distance(subdivision_points_for_edge[edge_idx][i],
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
def apply_spring_force(subdivision_points_for_edge, edge_idx, i, kP):
    prev_p = subdivision_points_for_edge[edge_idx][i - 1]
    next_p = subdivision_points_for_edge[edge_idx][i + 1]
    current = subdivision_points_for_edge[edge_idx][i]
    
    
    fs1_x = (prev_p.x-current.x)
    fs1_y = (prev_p.y-current.y)
    
    fs2_x = -(current.x-next_p.x)
    fs2_y = -(current.y-next_p.y)
    
    force_x = kP * (fs1_x + fs2_x)
    force_y = kP * (fs1_y + fs2_y)
    #print(fs1_x,fs2_x)
    return ForceFactors(force_x, force_y)

@njit(fastmath=FASTMATH)
def custom_edge_length(edge):
    return math.sqrt(math.pow(edge.source.x - edge.target.x, 2) + math.pow(edge.source.y - edge.target.y, 2))

@njit(fastmath=FASTMATH)
def apply_electrostatic_force(subdivision_points_for_edge, compatibility_list_for_edge,scores, edge_idx, i):
    ##Compute electostatic forces
    sum_of_forces_x = 0.0
    sum_of_forces_y = 0.0
    compatible_edges_list = compatibility_list_for_edge[edge_idx]
    current_point = subdivision_points_for_edge[edge_idx][i]
    
    for oe in range(len(compatible_edges_list)):
        other_edge = subdivision_points_for_edge[compatible_edges_list[oe]]
        other_point = other_edge[i]
        #print(edge_idx,other_edge)
        score = scores[edge_idx][oe]
    
        force_x = other_point.x - current_point.x
        force_y = other_point.y - current_point.y
        
        if (math.fabs(force_x) > eps) or (math.fabs(force_y) > eps):
            divisor = custom_edge_length(Edge(other_point, current_point))
            diff = (1 / divisor)

            sum_of_forces_x += score * force_x * diff
            sum_of_forces_y += score * force_y * diff

    return ForceFactors(sum_of_forces_x, sum_of_forces_y)

@njit(fastmath=FASTMATH)
def apply_resulting_forces_on_subdivision_points(edges, subdivision_points_for_edge, compatibility_list_for_edge,scores, edge_idx, K, P, S):
    # kP = K / | P | (number of segments), where | P | is the initial length of edge P.
    kP = K / (edge_length(edges[edge_idx]) * (P + 1))

    # (length * (num of sub division pts - 1))
    resulting_forces_for_subdivision_points = List()
    resulting_forces_for_subdivision_points.append(ForceFactors(0.0, 0.0))

    for i in range(1, P + 1): # exclude initial end points of the edge 0 and P+1
        spring_force = apply_spring_force(subdivision_points_for_edge, edge_idx, i, kP)
        electrostatic_force = apply_electrostatic_force(subdivision_points_for_edge, compatibility_list_for_edge,scores, edge_idx, i)

        resulting_force = ForceFactors(S * (spring_force.x + electrostatic_force.x),
                                       S * (spring_force.y + electrostatic_force.y))

        resulting_forces_for_subdivision_points.append(resulting_force)


    resulting_forces_for_subdivision_points.append(ForceFactors(0.0, 0.0))

    return resulting_forces_for_subdivision_points

def forcebundle(edges):
    ##Set cycle parameters to initials
    S = S_initial
    I = I_initial
    P = P_initial

    ##Create starting points
    print("Compute compatibilities")
    compatibility_list_for_edge,scores = compute_compatibility_list(edges) #compatibility_list_for_edge = subdivision_points_for_edges #compute_compatibility_list(edges)
    #subdivision_points_for_edge = update_edge_divisions(edges, subdivision_points_for_edge, P)
    subdivision_points_for_edge = create_edge_subdivision(edges,1)

    print("Starting force cycles")
    for _cycle in tqdm(range(C), unit='cycle'):
        
        for iteration in range(math.ceil(I)):
            forces = List()
            
            for edge_idx in range(len(edges)):
                forces.append(apply_resulting_forces_on_subdivision_points(edges, subdivision_points_for_edge,
                                                                            compatibility_list_for_edge,scores, edge_idx,
                                                                            K, P, S))
                
                for i in range(P + 1): # We want from 0 to P
                    subdivision_points_for_edge[edge_idx][i] = Point(
                        subdivision_points_for_edge[edge_idx][i].x + forces[edge_idx][i].x,
                        subdivision_points_for_edge[edge_idx][i].y + forces[edge_idx][i].y
                    )
        
        S *= S_rate
        I *= I_rate
        P = round(P * P_rate)
        
        subdivision_points_for_edge = update_edge_divisions(edges, subdivision_points_for_edge, P)
        
    
    return subdivision_points_for_edge

# Helpers
@njit(fastmath=FASTMATH)
def is_long_enough(edge):
    return True
    # Zero length edges
    if (edge.source.x == edge.target.x) or (edge.source.y == edge.target.y):
        return False
    # No EPS euclidean distance
    raw_lenght = math.sqrt(math.pow(edge.target.x - edge.source.x, 2) + math.pow(edge.target.y - edge.source.y, 2))
    if raw_lenght < (eps * P_initial * P_rate * C):
        return False
    else:
        return True


# Need to set types on var (they are not available inside a jit function)
edge_class = Edge.class_type.instance_type
@njit
def get_empty_edge_list():
    return List.empty_list(edge_class)


def net2edges(graph):
    edges = get_empty_edge_list()
    for edge in graph.edges():
        
        source = edge.node1
        source = Point(float32(source['x']), float32(source['y']))
        
        target = edge.node2
        target = Point(float32(target['x']), float32(target['y']))
        edge = Edge(source, target)
        #print(type(target))
        if is_long_enough(edge):
            edges.append(edge)

    return edges

