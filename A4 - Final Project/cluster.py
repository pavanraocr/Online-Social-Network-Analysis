"""
cluster.py
"""
from collections import Counter, defaultdict, deque
import copy
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path
import sys
import time
import pickle
from networkx.drawing.nx_pydot import write_dot

import collect as col

#global Constants
MOD_USER_FILE_NAME = "mod_user.pkl"
PRE_CLUSTERING_NETWORK_FILE_NAME = "pre_network.png"
POST_CLUSTERING_NETWORK_FILE_NAME = "post_network.png"

#global variables
num_of_clusters = 20

def write_modified_user_data(unique_users):
	"""
	Writes the user data in the MOD_USER_FILE_NAME for future use

	Params:
		Void
	Returns:
		Void
	"""
	with open(MOD_USER_FILE_NAME,"wb+") as f:
		pickle.dump(unique_users, f)

def read_mod_users():
	"""
	Reads the MOD_USER_FILE_NAME and returns a json object
	Params:
		void
	Returns:
		void
	"""
	userObj = []

	with open(MOD_USER_FILE_NAME, "rb") as f:
		userObj.extend(pickle.load(f))

	return userObj

def get_friends(twitter, screen_name):
    """ Return a list of Twitter IDs for users that this person follows, up to 5000.
    See https://dev.twitter.com/rest/reference/get/friends/ids

    Note, because of rate limits, it's best to test this method for one candidate before trying
    on all candidates.

    Args:
        twitter.......The TwitterAPI object
        screen_name... a string of a Twitter screen name
    Returns:
        A list of ints, one per friend ID, sorted in ascending order.

    Note: If a user follows more than 5000 accounts, we will limit ourselves to
    the first 5000 accounts returned.

    In this test case, I return the first 5 accounts that I follow.
    >>> twitter = get_twitter()
    >>> get_friends(twitter, 'aronwc')[:5]
    [695023, 1697081, 8381682, 10204352, 11669522]
    """
    return sorted(col.robust_request(twitter, 'friends/ids', col.forMultipleQuerryDict(['screen_name','count'],[screen_name,5000])).json()['ids'])


def add_all_friends(twitter, users):
    """ Get the list of accounts each user follows.
    I.e., call the get_friends method for all 4 candidates.

    Store the result in each user's dict using a new key called 'friends'.

    Args:
        twitter...The TwitterAPI object.
        users.....The list of user dicts.
    Returns:
        Nothing

    >>> twitter = get_twitter()
    >>> users = [{'screen_name': 'aronwc'}]
    >>> add_all_friends(twitter, users)
    >>> users[0]['friends'][:5]
    [695023, 1697081, 8381682, 10204352, 11669522]
    """
    user_file_path = Path(MOD_USER_FILE_NAME)

    if user_file_path.is_file():
    	users = read_mod_users()
    else:
    	for user in users:
    		user['friends'] = get_friends(twitter,user['screen_name'])
    	write_modified_user_data(users)

    return users

def count_friends(users):
    """ Count how often each friend is followed.
    Args:
        users: a list of user dicts
    Returns:
        a Counter object mapping each friend to the number of candidates who follow them.
        Counter documentation: https://docs.python.org/dev/library/collections.html#collections.Counter

    In this example, friend '2' is followed by three different users.
    >>> c = count_friends([{'friends': [1,2]}, {'friends': [2,3]}, {'friends': [2,3]}])
    >>> c.most_common()
    [(2, 3), (3, 2), (1, 1)]
    """
    counterObj = Counter()

    for user in users:
        counterObj.update(user['friends'])
    return counterObj

def friend_overlap(users):
    """
    Compute the number of shared accounts followed by each pair of users.

    Args:
        users...The list of user dicts.

    Return: A list of tuples containing (user1, user2, N), where N is the
        number of accounts that both user1 and user2 follow.  This list should
        be sorted in descending order of N. Ties are broken first by user1's
        screen_name, then by user2's screen_name (sorted in ascending
        alphabetical order). See Python's builtin sorted method.

    In this example, users 'a' and 'c' follow the same 3 accounts:
    >>> friend_overlap([
    ...     {'screen_name': 'a', 'friends': ['1', '2', '3']},
    ...     {'screen_name': 'b', 'friends': ['2', '3', '4']},
    ...     {'screen_name': 'c', 'friends': ['1', '2', '3']},
    ...     ])
    [('a', 'c', 3), ('a', 'b', 2), ('b', 'c', 2)]
    """
    finalList = []
    counterObj = Counter()
    for i in range(len(users)):
        for j in range(i+1,len(users)):
            counterObj.update(users[i]['friends'])
            counterObj.update(users[j]['friends'])
            finalList.append((users[i]['screen_name'],users[j]['screen_name'],len([x for x in counterObj.most_common() if x[1] != 1])))
            counterObj.clear()
    return sorted(finalList,key=lambda x: -x[2])

def getFilteredFriendList(oriFriendList, friend_counts):
    """
    This filters out all the friends who are not followed by more than one candidate
    """
    return [x for x in oriFriendList if friend_counts[x] > 1]

def create_pre_graph(edgeMapping):
    """ Create a networkx undirected Graph, adding each candidate and friend
        as a node.  Note: while all candidates should be added to the graph,
        only add friends to the graph if they are followed by more than one
        candidate. (This is to reduce clutter.)

        Each candidate in the Graph will be represented by their screen_name,
        while each friend will be represented by their user id.

    Args:
      users...........The list of user dicts.
      friend_counts...The Counter dict mapping each friend to the number of candidates that follow them.
    Returns:
      A networkx Graph
    """
    return nx.Graph([(x,y) for (x,y,z) in edgeMapping])

def draw_network(graph, filename):
	"""
	Draw the network to a file. Only label the candidate nodes; the friend
	nodes should have no labels (to reduce clutter).

	Methods you'll need include networkx.draw_networkx, plt.figure, and plt.savefig.

	our figure does not have to look exactly the same as mine, but try to
	make it look presentable.
	"""
	figsize=(500,500)
	plt.figure()
	pos = nx.fruchterman_reingold_layout(graph,iterations=75)
	nx.draw_networkx(graph, pos, node_size=30, node_color='b', alpha=0.8, with_labels=False, linewidths=0, width=0.05, edge_color='r',font_size=5)
	nx.draw_networkx_edges(graph,pos, alpha=0.1)
	#nx.draw_networkx_nodes(graph,pos,alpha=0.2,node_color='r')
	plt.axis('off')
	plt.savefig(filename)

def displayBeforeCluster(edgeMapping):
	"""
	Creates a networkx object and draws a graph based on the same
	"""
	#create an object before cluster
	graphBeforeCluster = create_pre_graph(edgeMapping)
	print('Pre-clustering Graph Stats:\ngraph has %s nodes and %s edges' % (len(graphBeforeCluster.nodes()), len(graphBeforeCluster.edges())))
	draw_network(graphBeforeCluster, PRE_CLUSTERING_NETWORK_FILE_NAME)

	return graphBeforeCluster

def constructGraphObject():
	"""
	This requires the TWEET_FILE_NAME to be present and filled with tweets
	Params:
		void
	Returns:
		networkx Object
	"""
	print("Getting the users form the file")
	unique_users = col.read_users()
	if len(unique_users) == 0:
		print("ERROR: You may have not run collect.py as there are no users collected for clustering")

	#retrieves the same list but with the extra colunm which is a list \
	#of friends that a particular user follows
	print("Getting the follower ids from the list of users")
	unique_users = add_all_friends(col.get_twitter(),unique_users)
	print("Getting common friends")
	friend_counts = count_friends(unique_users)
	print('Most common friends:\n%s' % str(friend_counts.most_common(5)))
	edgeMapping = friend_overlap(unique_users)

	graphBeforeCluster = displayBeforeCluster(edgeMapping)

	return graphBeforeCluster

def weigh_the_edges(graph):
	"""
	This weighs each edge in the graph by the centerality factor
	Params:
		graph.....A networkx object
	Returns:
		edges.....a list of edges with weights
	"""
	edges = nx.edge_betweenness_centrality(graph)
	return sorted(edges.items(), key=lambda x: x[1], reverse=True)

def partition_girvan_newman(graph, k):
    """
    Use your approximate_betweenness implementation to partition a graph.
    Unlike in class, here you will not implement this recursively. Instead,
    just remove edges until more than one component is created, then return
    those components.
    That is, compute the approximate betweenness of all edges, and remove
    them until multiple comonents are created.

    You only need to compute the betweenness once.
    If there are ties in edge betweenness, break by edge name (e.g.,
    (('A', 'B'), 1.0) comes before (('B', 'C'), 1.0)).

    Note: the original graph variable should not be modified. Instead,
    make a copy of the original graph prior to removing edges.
    See the Graph.copy method https://networkx.github.io/documentation/development/reference/generated/networkx.Graph.copy.html
    Params:
      graph.......A networkx Graph
      max_depth...An integer representing the maximum depth to search.

    Returns:
      A list of networkx Graph objects, one per partition.

    >>> components = partition_girvan_newman(example_graph(), 5)
    >>> components = sorted(components, key=lambda x: sorted(x.nodes())[0])
    >>> sorted(components[0].nodes())
    ['A', 'B', 'C']
    >>> sorted(components[1].nodes())
    ['D', 'E', 'F', 'G']
    """
    graphCopy = graph.copy()
    edge_to_remove = deque(weigh_the_edges(graphCopy))
    components = list(nx.connected_component_subgraphs(graphCopy))

    while len(components) < k:
    	edge = edge_to_remove.popleft()
    	for u,v in [edge[0]]:
    		break
    	graphCopy.remove_edge(u,v)
    	components = list(nx.connected_component_subgraphs(graphCopy))

    return components

def main():

	global num_of_clusters

	preGraph = constructGraphObject()
	print("Now Partioning the graph")
	clusters = partition_girvan_newman(preGraph, 20)
	print("Drawing graph after clustering look for ",POST_CLUSTERING_NETWORK_FILE_NAME)
	clusteredGraph = nx.karate_club_graph()

	sumOfUsers = 0
	for i,cluster in enumerate(clusters):
		sumOfUsers += cluster.order()
		# print("Cluster",i,"has the size",cluster.order())
		clusteredGraph.add_edges_from(cluster.edges())
		clusteredGraph.add_nodes_from(cluster.nodes())

	draw_network(clusteredGraph, POST_CLUSTERING_NETWORK_FILE_NAME)

	#summary generation
	data = col.forMultipleQuerryDict(["Number of communities discovered","Average number of users per community"],[num_of_clusters,sumOfUsers/num_of_clusters])
	col.writeToSummaryFile(data)

if __name__ == '__main__':
	main()