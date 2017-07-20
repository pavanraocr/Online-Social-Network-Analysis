"""
classify.py
"""
from collections import Counter, defaultdict
from itertools import chain, combinations
import glob
import matplotlib.pyplot as plt
import numpy as np
import os
import re
import collect as c
import pickle
import json
from pathlib import Path
from scipy.sparse import csr_matrix
from sklearn.cross_validation import KFold
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import CountVectorizer
import string

#global constants
TRAIN_PREFIX_TWEET_FILE_NAME = 'Train_' + c.TWEETS_FILE_NAME
TRAIN_PREFIX_TWEET_JSON_FILE_NAME = "train_data.json"
TRAIN_PREFIX_USER_FILE_NAME = 'Train_' + c.USER_FILE_NAME

def read_labled_tweets(tweetFileName):
	"""
	This reads the tweets from the file named as the variable passed as a parameter

	Params:
		fileName.......String that denotes the file name
	Returns:
		tweetObj.......Object that holds the tweets in Dictionary format
	"""
	tweetFile = Path(tweetFileName)
	tweetObj = []
	tweets = []
	label = []

	#checks if the file is present
	if tweetFile.is_file():
		#reading the tweets
		f = open(tweetFileName, 'r')
		tweetObj.extend(json.load(f))
		f.close()

		for t in tweetObj:
			tweets.append(t['text'])
			label.append(t['label'])
	else:
		return []

	return tweets,label

def tokenize_with_punc(doc):
    """
    Tokenize a string.
    The string should be converted to lowercase.
    If keep_internal_punct is False, then return only the alphanumerics (letters, numbers and underscore).
    If keep_internal_punct is True, then also retain punctuation that
    is inside of a word. E.g., in the example below, the token "isn't"
    is maintained when keep_internal_punct=True; otherwise, it is
    split into "isn" and "t" tokens.

    Params:
      doc....a string.
      keep_internal_punct...see above
    Returns:
      a numpy array containing the resulting tokens.
    """
    preProcess = doc.lower().split(" ")
    #remove the special characters if it exsists
    regex = re.compile("\A\W+|\W+\Z",re.M)
    fnlArr = []

    for word in preProcess:
      fnlArr.extend([x for x in re.sub(regex, " ", word).split(" ") if x not in [""," "]])

    return np.array(fnlArr)

def tokenize_without_punc(doc):
	preProcess = doc.lower().split(" ")
	regex = re.compile("\W+",re.M)
	fnlArr = []

	for word in preProcess:
	  fnlArr.extend([x for x in re.sub(regex, " ", word).split(" ") if x not in [""," "]])

	return np.array(fnlArr)

def vertorize(tweets, tokenizerFunc = tokenize_without_punc, min_df=1, max_df=1,
	 binary=True, ngram_range=(1,2)):
	stop_words = []
	vec = CountVectorizer( tokenizer=tokenizerFunc, min_df=min_df,
		max_df=max_df,binary=binary, ngram_range=ngram_range,stop_words=stop_words,max_features=600)
	data = vec.fit_transform(tweets)
	return (data,vec)

def main():
	print("Tweet classifier is executed")
	print('Reads the labelled tweets for training')
	#sp.main()

	clf = LogisticRegression()

	labelledTTweets,label = read_labled_tweets(TRAIN_PREFIX_TWEET_JSON_FILE_NAME)
	vectorizer = CountVectorizer(min_df=1,ngram_range=(1,2),tokenizer = None,preprocessor = None,stop_words = None, max_features = 600)

	#labelledTTweets = read_tweets(TRAIN_PREFIX_TWEET_FILE_NAME, TRAIN_PREFIX_USER_FILE_NAME)
	print('Now training the data:Calling Vectorizer')
	trainDataLen = len(labelledTTweets)
	X, vec = vertorize(labelledTTweets)

	testTweets = c.read_tweets()
	totalTweets = []
	totalTweets.extend(labelledTTweets)
	totalTweets.extend([t['text'] for t in testTweets])

	print('Fitting the model')
	matrix = vectorizer.fit_transform(totalTweets)

	
	clf.fit(matrix[:trainDataLen], label)
	print('Predicting test data')
	predicted = clf.predict(matrix[trainDataLen:])
	classCategory = Counter(predicted)

	keys = ["Number of instances per class found","class\t"]
	vals = ["","instances\t"]
	data = c.forMultipleQuerryDict(keys,vals)
	c.writeToSummaryFile(data)

	keys = [x for x,y in classCategory.items()]
	vals = [y for x,y in classCategory.items()]
	data = c.forMultipleQuerryDict(keys,vals)
	c.writeToSummaryFile(data)

	for i,t in enumerate(testTweets):
		if str(predicted[i]) == str(0):
			c.writeToSummaryFile(c.forMultipleQuerryDict(["class 0"],[t['text']]))
			break
	for i,t in enumerate(testTweets):
		if str(predicted[i]) == str(1):
			c.writeToSummaryFile(c.forMultipleQuerryDict(["class 1"],[t['text']]))
			break

if __name__ == "__main__":
	main()
