import numpy as np
import networkx as nx
from tqdm.notebook import tqdm
import matplotlib.pyplot as plt
from itertools import product
from joblib import Parallel, delayed

def group(original_list, n):
    '''Groups original_list into a list of lists, where each list contains n consecutive
    elements from the original_list'''
    return [original_list[x:x+n] for x in range(0,len(original_list),n)]


def evaluate(true_pages, predicted_pages, beta=2):
    '''
    true_pages is a list of all the pages known to belong to a WUJ
    predicted_pages ia a list of pages predicted to belong to a WUJ
    beta determines how much more important recall is than precision when computing fscore
    
    returns precision, recall and fscore
    '''
    
    true_pages = set(true_pages)
    predicted_pages = set(predicted_pages)
    
    # what proportion of true pages were correctly predicted?
    recall = len(true_pages.intersection(predicted_pages))/len(true_pages)
    
    # what proportion of predicted pages are true pages?
    precision = len(true_pages.intersection(predicted_pages))/len(predicted_pages)

    # compute f score, a harmonic mean of precision and recall
    fscore = ((1 + beta**2) * (precision * recall))/((precision * beta**2) + recall)
    
    return (precision, recall, fscore)

def getSlugs(G):
    '''
    Returns a list of slugs, given a networkx graph G.
    '''
    return [node[1]['properties']['name'] for node in G.nodes(data=True)]

def showGraph(G, k=None, iterations=50, node_size=100, figsize=None):
    '''
    Prints graph information and plots the graph, G.
    Takes figsize as input, a tuple, e.g. (10,10)
    '''
    print(nx.info(G))
    nx.spring_layout(G, k=k, iterations=iterations)
    plt.figure(figsize=(figsize))
    nx.draw(G, node_size=node_size)

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

def M_walks_get_slugs(T,G,steps,repeats,seed_page,proba):
    '''Gets slugs from 'repeats' many random walks for a given seed page'''
    return [getSlugs(G.subgraph(random_walk(T,G,steps,seed_page,proba))) for _ in range(repeats)]

def check_seed_pages(seeds, G):
    G_nodes = set([node[1]['properties']['name'] for node in G.nodes(data=True)])
    not_found = [seed for seed in seeds if seed not in G_nodes]
    if len(not_found) > 0:
        print(not_found, 'could not be found in the graph')
        return not_found
    else:
        return []
    
def repeat_random_walks(steps, repeats, T, G, seed_pages, proba, combine, level=0, verbose=1, n_jobs=1):
    '''
    Performs 'repeats' many random walks per seed page in seed_pages, each with 'steps' many steps. seed_pages is a list
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

    if combine = 'union' or 'intersection:
    level = 0 unions/intersects the pages visited by all 'repeats' many random walks
    at the level of seed nodes, giving you one set of pages per seed node.
    level = 1 unions/intersects the pages visited by all repeats*len(seed_pages) random walks,
    giving you one set of pages.
    
    T is an adjaceny matrix or a transition probability matrix. They are CSR sparse matrices.
    If using a probability transition matrix, set proba=True.

    verbose >= 1 if you want progress bars. verbose <= 0 if you don't want progress bars.
    
    n_jobs is the number of CPUs to use.
    For large experiments, I recommend n_jobs = -2, to use all but 1 of your CPUs, leaving
    1 CPU available for other tasks.
    For small experiments, I recommend n_jobs = 1. The overhead of n_jobs > 1 is only
    worth it for large experiments, e.g. when M > 100.
    '''

    # find seed pages not found in the graph
    not_found = set(check_seed_pages(seed_pages, G))

    # remove seed pages not found in the graph
    seed_pages = [page for page in seed_pages if page not in not_found]

    # for each seed node, compute paths taken
    if verbose >= 1:
        paths_taken = Parallel(n_jobs=n_jobs)(delayed(M_walks_get_slugs)(T,G,steps,repeats,seed_page,proba) for seed_page in tqdm(seed_pages))
    else:
        paths_taken = Parallel(n_jobs=n_jobs)(delayed(M_walks_get_slugs)(T,G,steps,repeats,seed_page,proba) for seed_page in seed_pages)
    
    if combine == 'union':
        if level == 0:
            pages_visited = [set([page for path in paths for page in path]) for paths in paths_taken]
        elif level == 1:
            pages_visited = {page for paths in paths_taken for path in paths for page in path}

    elif combine == 'intersection':
        if level == 0:
            pages_visited = [set.intersection(*map(set,paths)) for paths in paths_taken]
        elif level == 1:
            pages_visited = set.intersection(*[set([page for path in paths for page in path]) for paths in paths_taken])

    elif combine == 'no':
        pages_visited = paths_taken

    else:
        print(combine, 'is an invalid path combination method')
        return

    if not pages_visited:
        print("No pages found")
        return

    return {'seeds': seed_pages, 'pages_visited': pages_visited}

def M_N_Experiment(steps, repeats, T, G, target_pages, seed_pages, proba, n_jobs):
    '''
    For a given transition matrix T, graph G, set of WUJ target_pages and seed_pages within a WUJ,
    this function tries every combination of steps and repeats. E.g.

    Number of steps to take in random walk
    steps = [10,20,30,40,50,60,70,80,90,100,200,300,400,500,600]

    Number of times to initialise random walk from a given seed node
    repeats = [10,20,30,40,50,60,70,80,90,100,200,300,400,500,600]

    Set proba=True if T contains probabilities, and proba=False if T is an adjacency matrix.

    n_jobs = number of workers to use during execution, for parallelisation.
    '''
    # all combinations of N and M
    NMs = list(product(steps,repeats))

    results = Parallel(n_jobs=n_jobs)(delayed(repeat_random_walks)(step, repeat, T, G, seed_pages, proba, 'union', 1, 0, 1) for step, repeat in tqdm(NMs))

    scores = []
    for i, result in enumerate(results):
        path = result['pages_visited']
        p, r, f = evaluate(target_pages, path)
        n, m = NMs[i]
        scores.append([p,r,f,n,m,len(path)])

    return scores