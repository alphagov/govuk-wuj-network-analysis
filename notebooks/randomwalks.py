import numpy as np
import networkx as nx
from tqdm.notebook import tqdm

def group(original_list, n):
    '''Groups original_list into a list of lists, where each list contains n consecutive
    elements from the original_list'''
    return [original_list[x:x+n] for x in range(0,len(original_list),n)]


def evaluate(true_pages, predicted_pages):
    '''
    true_pages is a list of all the pages known to belong to a WUJ
    predicted_pages ia a list of pages predicted to belong to a WUJ
    
    returns precision and recall as percentages
    '''
    
    true_pages = set(true_pages)
    predicted_pages = set(predicted_pages)
    
    # what proportion of true pages were correctly predicted?
    recall = len(true_pages.intersection(predicted_pages))/len(true_pages)*100
    
    # what proportion of predicted pages are true pages?
    precision = len(true_pages.intersection(predicted_pages))/len(predicted_pages)*100
    
    return (precision, recall)

def getSlugs(G):
    '''
    Returns a list of slugs, given a networkx graph G.
    '''
    return [node[1]['properties']['name'] for node in G.nodes(data=True)]

def showGraph(G, figsize=None):
    '''
    Prints graph information and plots the graph, G.
    Takes figsize as input, a tuple, e.g. (10,10)
    '''
    print(nx.info(G))
    plt.figure(figsize=(figsize))
    nx.draw(G)

def random_walk(A, G, steps, seed, p=False):
    '''
    A is an adjacency matrix, or a transition probability matrix. These should be CSR sparse matrices.
    Set p=True if using a transition probability matrix.
    G is a networkx graph.
    steps is the number of steps to take in the random walk.
    seed is a page slug for your starting node in the random walk. E.g. "/set-up-business" 
    
    returns a numpy array of node ids visited during the random walk.
    can return numpy array of nodes with their data if nodeData == True
    '''

    # set a seed node
    foundSeed = False
    for current_node_index, node in enumerate(G.nodes(data=True)):
        if node[1]["properties"]["name"] == seed:
            foundSeed = True
            break
    
    if not foundSeed:
        return []

    # list of nodes visited during the random walk
    visited = [current_node_index]
    
    transition_probs = None

    for _ in range(steps):

        # identify neighbours of current node
        neighbours = np.nonzero(A[current_node_index])[1]

        # if reached an absorbing state, i.e. no neighbours, then terminate the random walk
        if neighbours.size == 0:
            #print("Reached absorbing state after", step, "steps")
            visited = list(set(visited))
            return np.array(G.nodes())[visited]
        
        # if using transition probabilities, get them
        if p:
            transition_probs = A[current_node_index].toarray()[0, neighbours]
        
        # select the index of next node to transition to
        current_node_index = np.random.choice(neighbours, p=transition_probs)

        # maintain record of the path taken by the random walk
        visited.append(current_node_index)
    
    # return unique pages visited
    visited = list(set(visited))
        
    return np.array(G.nodes())[visited]

def walk_get_slugs(T,G,N,seed_page,proba):
    '''Just gets slugs from a random walk'''
    return getSlugs(G.subgraph(random_walk(T,G,N,seed_page,proba)))

def check_seed_pages(seeds, G):
    G_nodes = set([node[1]['properties']['name'] for node in G.nodes(data=True)])
    not_found = [seed for seed in seeds if seed not in G_nodes]
    if len(not_found) > 0:
        print(not_found, 'could not be found in the graph')
        return not_found
    else:
        return []
    
def repeat_random_walks(N, M, T, G, seed_pages, proba, combine, n_jobs=1):
    '''
    Performs M random walks per seed page in seed_pages, each with N steps. seed_pages is a list
    of page slugs. e.g. 
    ['/government/collections/ip-enforcement-reports',
    '/government/publications/annual-ip-crime-and-enforcement-report-2020-to-2021',
    '/search-registered-design']
    
    Each random walk will traverse a network of gov.uk pages, each one recording the set of pages
    that were visited.
    
    M*len(seed_pages) many sets of pages will be generated. combine takes value 'intersection' or 'union',
    depending on whether to compute the union or intersection of these sets. In either case, a single
    set of pages is returned, containing only the unique pages visited.
    
    If combine is set to 'no', then a list of len(seed_pages) lists will be
    returned. Each list will contain the paths of the M random walks performed per seed node.
    
    T is an adjaceny matrix or a transition probability matrix. They are CSR sparse matrices.
    If using a probability transition matrix, set proba=True.
    
    n_jobs is the number of CPUs to use.
    For large experiments, I recommend n_jobs = -2, to use all but 1 of your CPUs.
    For small experiments, I recommend n_jobs = 1. The overhead of n_jobs > 1 is only
    worth it for large experiments.
    '''
    
    from itertools import product 
    from joblib import Parallel, delayed

    # find seed pages not found in the graph
    not_found = set(check_seed_pages(seed_pages, G))

    # remove seed pages not found in the graph
    seed_pages = [page for page in seed_pages if page not in not_found]

    # create list to loop over
    # it repeats each seed_page M times
    seeds_Ms = list(product(seed_pages,list(range(M))))

    paths_taken = Parallel(n_jobs=n_jobs)(delayed(walk_get_slugs)(T,G,N,seed_page,proba) for seed_page,_ in tqdm(seeds_Ms))

    if combine == 'union':
        pages_visited = {page for path in paths_taken for page in path}
    elif combine == 'intersection':
        pages_visited = set.intersection(*map(set,paths_taken))
    elif combine == 'no':
        pages_visited = group([list(set(path))for path in paths_taken], M)
    else:
        print(combine, 'is an invalid path combination method')
        return

    if not pages_visited:
        print("No pages found")
        return

    return {'seeds': seed_pages, 'pages_visited': pages_visited}