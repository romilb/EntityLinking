import tweepy
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from get_cosine import *

consumer_key_ = 'KJX5xGQ4HqSGWG8GfioI6w'
consumer_secret_ = 'nAJy5IRa4TKpI4aSryQH35tSEHatfP6AUvAHXAnX4bM'

access_key = '240974125-45UNENap7Zvv6COLOxYRa98I7rGqjhFrZqod160q'
access_secret = 'z2XXebjqUmWOUrjUDoV7GgdL87ahocJRrfbcEHjw'


class TwitterAPI:

	def __init__(self):
		print "Initializing TwitterAPI..."
		self.auth = tweepy.OAuthHandler(consumer_key_, consumer_secret_)
		self.auth.set_access_token(access_key, access_secret)
		self.api = tweepy.API(self.auth,proxy_url="proxy.iiit.ac.in:8080")
		print self.api.me().name
		print "Initialization of TwitterAPI Completed..."

	#ret = api.user_timeline(, count = 100, include_rts = True)
	#api = tweepy.API(auth,proxy_url="proxy.iiit.ac.in:8080")
	def get_tweets(self,keyword,max_count=20):
		print "Fetching Tweets..."
		arr_tweets = set([])
		count = 0
		results = self.api.search(q=keyword,lang="en",result_type="mixed",include_entities=False,include_retweets=False,count=50)
		for i in results:
			#print i
			for j in arr_tweets:
				if get_text_cosine(j,i.text) > .8:
					#print "Similar",i.text,'----AND----',j
					continue
			count += 1
			arr_tweets.add(i.text)
			if count > max_count:
				break
		#print "Fetch Completed"
		return arr_tweets

	def get_user_tweets(self,user,max_count=20):
		print "Fetching Tweets..."
		new_tweets = self.api.user_timeline(screen_name = user,count=200)
		if new_tweets:
			return [new_tweets[0].user.description]+[tweet.text for tweet in new_tweets][:max_count]

if __name__ == '__main__':
	twitter = TwitterAPI()
	print twitter.get_user_tweets('romilbansal')
	for result in twitter.get_tweets("recsys2014"):
		print result.encode('utf8','convert')
