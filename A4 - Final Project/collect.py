"""
collect.py
"""
# Imports you'll need.
import sys
import os
import pickle
import time
import re
from TwitterAPI import TwitterAPI
from pathlib import Path

consumer_key = '****'
consumer_secret = '****'
access_token = '****'
access_token_secret = '****'

#global constants
MAX_USERS = 200
MAX_TWEETS = 1000
TWEETS_FILE_NAME = "Tweet.pkl"
USER_FILE_NAME = "User.pkl"
SUMMARY_FILE_NAME = "summary.txt"
# HASH_TAGS = ['#calexit','#YesCalifornia','#notmypresident']
HASH_TAGS = '#calexit'

#global declarations
unique_userCounts = 0
tweet_count = 0
num_of_ios = 0

# This method is done for you.
def get_twitter():
    """ Construct an instance of TwitterAPI using the tokens you entered above.
    Returns:
      An instance of TwitterAPI.
    """
    twitterHandle = TwitterAPI(consumer_key, consumer_secret, access_token, access_token_secret)
    return twitterHandle

# I've provided the method below to handle Twitter's rate limiting.
# You should call this method whenever you need to access the Twitter API.
def robust_request(twitter, resource, params, max_tries=5):
    """ If a Twitter request fails, sleep for 15 minutes.
    Do this at most max_tries times before quitting.
    Args:
      twitter .... A TwitterAPI object.
      resource ... A resource string to request; e.g., "friends/ids"
      params ..... A parameter dict for the request, e.g., to specify
                   parameters like screen_name or count.
      max_tries .. The maximum number of tries to attempt.
    Returns:
      A TwitterResponse object, or None if failed.
    """
    for i in range(max_tries):
        request = twitter.request(resource, params)
        if request.status_code == 200:
            return request
        else:
            print('Got error %s \nsleeping for 15 minutes.' % request.text)
            sys.stderr.flush()
            time.sleep(61 * 15)

def formQuerryDict(key, li):
    """
    forms the dictionary for sending as a parameter to the robust request
    Params:
	li - list of values which will become a parameter list with the key which is passed as an argument in a dict
    Returns:
	A dictionary
    """
    return {key:li}

def forMultipleQuerryDict(keyLst, valLst):
	"""
	forms the dictionary for sending as a parameter to the robust request
    Params:
    	keyLst.......List of keys that will be a key in the final dictionary
		valLst.......List of values which will become a parameter list with the key which is passed as an argument in a dict
    Returns:
		A dictionary
	"""
	d = {}
	for i,x in enumerate(keyLst):
		d[x] = valLst[i]

	return d

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
    return sorted(robust_request(twitter, 'friends/ids', formQuerryDict('screen_name',screen_name)).json()['ids'])

def writeToSummaryFile(data):
	"""
	write the data which is in form of a dictionary to the summary file
	Params:
		data....Dictionary which has the text to be written with values
	Returns:
		None
	"""
	try:
		with open(SUMMARY_FILE_NAME, 'a+') as f:
			for k,v in data.items():
				f.write("".join(["\t- ",str(k),":",str(v),"\n"]))
	except IOError:
		pass

def writeData(tweets, unique_users, tweetFileName=TWEETS_FILE_NAME,userFileName=USER_FILE_NAME):
	"""
	Gets a list of tweets with filtered characteristics and writes it into a pickel file

	Param:
		tweets........List of all the filtered lists
	Returns:
		NONE
	"""
	global num_of_ios

	with open(tweetFileName, 'ab+') as f:
		pickle.dump(tweets, f)

	with open(userFileName,"ab+") as f:
		pickle.dump(unique_users, f)

	num_of_ios += 1

def isTweetInValid(tweet):
	"""
	Checks of a tweet is valid
	Params:
		tweet.......A tweet object
	Returns
		boolean.....signifying whether this tweet should be retained or not
	"""

	if re.match('^RT',tweet['text']):	
		return True
	else:
		tweet['text'] = re.sub('http[^ ]+','',tweet['text'])
		return False

def saveData(tweetLst, tweetFileName=TWEETS_FILE_NAME,userFileName=USER_FILE_NAME):
	"""
	Filters all the tweets and retains only the data that is required and puts it to the file with the name
	TWEETS_FILE_NAME

	Params:
		tweetList.......List of tweet object retrieved from the request done to twitter
	Returns:
		maxtweetId......An integer which is the mintweetId of the previous batch
	"""
	global unique_userCounts, tweet_count

	unique_users = []
	unique_users_set = set()
	newTweets = []
	tweetIds = []

	for tweet in tweetLst['statuses']:
		tweetObj = {}
		if isTweetInValid(tweet):
			continue
		try:
			tweetObj['tweetId'] = tweet['id']
			tweetObj['userId'] = tweet['user']['id']
			tweetObj['screenName'] = tweet['user']['screen_name']
			tweetObj['text'] = tweet['text']
			#this is required to retrive unique tweets from one tweets to the other
			tweetIds.append(tweetObj['tweetId'])
			newTweets.append(tweetObj)
			tweet_count += 1

			if len(set([tweetObj['userId']]) & unique_users_set) == 0:
				unique_users_set.add(tweetObj['userId'])
				unique_users.append({'screen_name':tweetObj['screenName'],'id':tweetObj['userId']})
				unique_userCounts += 1
		except KeyError:
			print("==============>ERROR,",tweet_count,unique_userCounts)
			print(tweet)
	
	if len(newTweets) > 0:
		writeData(newTweets, unique_users, tweetFileName, userFileName)

	return min(tweetIds),newTweets

def get_all_tweets(twitter, hashTags, tweetFileName=TWEETS_FILE_NAME,userFileName=USER_FILE_NAME):
	"""
	Retrieves the list of tweets on the hashtags that is passed as a parameter it writes into the file or
	reads from the file if the number of users required for analysis is reached

	Params:
		twitter...........The twitter API object
		hashTags..........A list of hashtags which the tweets are trying to be retrieved
	Returns:
		A list of tweet object
	"""
	global unique_userCounts,tweet_count
	maxTweetId = -1
	tweetLst = []

	while unique_userCounts < MAX_USERS and tweet_count < MAX_TWEETS:
		newSetOfTweets = []

		if maxTweetId != -1:
			receiveHandle = robust_request(twitter, 'search/tweets',
				forMultipleQuerryDict(['q','count','result_type','max_id'],[hashTags,180,"recent",maxTweetId])).json()
		else:
			receiveHandle = robust_request(twitter, 'search/tweets',
				forMultipleQuerryDict(['q','count','result_type'],[hashTags,180,"recent"])).json()
		#writes the data to the pickle file updates the unique_userCounts and numOfTweets collected so far
		maxTweetId,newSetOfTweets = saveData(receiveHandle, tweetFileName, userFileName)
		tweetLst.extend(newSetOfTweets)

	return tweetLst

def read_tweets(tweetFileName=TWEETS_FILE_NAME,userFileName=USER_FILE_NAME):
	"""
	This reads the data from the pickle file if it exists or it will request the from the twitter API

	Params:
		twitter..... A twitter handle
	Returns:
		void
	"""
	global num_of_ios,tweet_count, unique_userCounts

	#checks if the file exsists in the given path
	tweetFile = Path(tweetFileName)
	tweetObj = []
	userObj = []

	#checks if the file is present
	if tweetFile.is_file():
		#reading the tweets
		f = open(tweetFileName, 'rb')

		while 1:
			try:
				tweetObj.extend(pickle.load(f))
			except EOFError:
				break
		f.close()

		f = open(userFileName, 'rb')

		while 1:
			try:
				userObj.extend(pickle.load(f))
			except EOFError:
				break
		f.close()

		num_of_ios = 0
		tweet_count = len(tweetObj)
		unique_userCounts = len(userObj)

	if len(tweetObj) == 0:
		twitter = get_twitter()
		print('Established Twitter connection.')
		tweetObj = get_all_tweets(twitter, HASH_TAGS,tweetFileName,userFileName)

	print('Total Number of tweets collected:', tweet_count)
	print('Total Number of Unique Users:', unique_userCounts)
	
	return tweetObj

def read_users():
	"""
	Reads all the users from the file that was created already while creatign the tweets
	Params:
		Void
	Returns:
		userObj......list where each element is a dict of screen_name and id
	"""
	userFile = Path(USER_FILE_NAME)
	userObj = []

	if userFile.is_file():
		#reading the tweets
		try:
			f = open(USER_FILE_NAME, 'rb')

			while 1:
				try:
					userObj.extend(pickle.load(f))
				except EOFError:
					break
			f.close()
		except IOError:
			return []

	return userObj[:60]

def main():
	"""
	This is the main class which call the above functions which gets the tweets from the 
	twitter based on the hashtags provided in the global variable and retrives the user ids and does this 
	untill the MAX_TWEETS or MAX_USERS are reached
	"""
	global unique_userCounts,tweet_count

	print('Retrieving the data required for the assignment')
	read_tweets()

	#summary generation
	d = forMultipleQuerryDict(["Number of users collected","Number of messages collected"],[unique_userCounts,tweet_count])
	writeToSummaryFile(d)

if __name__ == "__main__":
	main()
