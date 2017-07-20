import pickle
import csv
import json
import collect as c

#global constants
TRAIN_PREFIX_TWEET_FILE_NAME = 'Train_' + c.TWEETS_FILE_NAME
TRAIN_PREFIX_USER_FILE_NAME = 'Train_' + c.USER_FILE_NAME

def write_tweet_csv(data):
	with open('train_data.csv','w', encoding='utf-8') as f:
		a = csv.writer(f)
		a.writerows([list(x.items()) for x in data])

def write_tweet_json(data):
	print('writing the data of length', len(data))
	with open('train_data.json','w') as f:
		json.dump([{'text':x['text'],'label':1} for x in data],f)


def read_train_tweet_pkl():
	f = open('Train_Tweet.pkl', 'rb')

	tweetObj = []
	while 1:
		try:
			tweetObj.extend(pickle.load(f))
		except EOFError:
			break

	f.close()

	return tweetObj

def main():
	tweets = c.read_tweets(TRAIN_PREFIX_TWEET_FILE_NAME,TRAIN_PREFIX_USER_FILE_NAME)

	#tweets = read_train_tweet_pkl()
	write_tweet_json(tweets)

if __name__ == "__main__":
	main()