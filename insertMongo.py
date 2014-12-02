from pymongo import MongoClient
import datetime
import re
import json	

from variables import mongo_url

class mongo_titles:
	def __init__(self):
		self.clients = MongoClient(mongo_url, 27017)
		self.db = self.clients.wikipages
		self.posts = self.db.posts

	def insert(self,post):
		post_id = self.posts.insert(json.loads(post))

	def find(self,post):
		t=self.posts.find_one(post)
		#print t
		try:
			if str(t['cat'][0]) == "":
				return t
			elif str(t['cat'][0]).find("Category:") == -1:
				return self.find({"title":str(t['cat'][0])})
			return t
		except:
			return {"title":post["title"],"cat":[]}

	def insert(self):
		arr = []
		count = 0
		f = open('titletocat.txt')
		for line in f:
			count += 1
			spl = line.strip().split('#')
			cat = spl[1].split(' ')
			arr.append({"title":spl[0],"cat":cat})
			if count%100000 == 0:
				print count
				mon.insert(arr)
				print "DONE"
				arr = []
		mon.insert(arr)		

	def disconnect(self):
		self.clients.close()

	def out_degree(self,category):
		t=self.posts.find({'cat':category}).count()
		return t

	def get_children(self,category):
		child = []
		if "Category:" != category[:9]:
			return child
		t = self.posts.find({'cat':category})
		for i in t:
			child.append(i['title'])
		return child

	def topic_sim(self,title1,title2):
		cat1 = set(self.find({"title":title1})['cat'])
		cat2 = set(self.find({"title":title2})['cat'])
		intersectn = cat1 & cat2
		score  = 0
		for i in intersectn:
			print i
			score += 1.0/self.out_degree(i)
		return score

if __name__ == '__main__':		
	mon = mongo_titles()
	#print mon.find({"title":"Apple"})
	#print mon.find({"title":"Blackberry"})
	#print mon.find({"title":"Orange_(fruit)"})
	print mon.topic_sim("Apple_Inc.","Steve_Jobs")
	print mon.topic_sim("Apple_Inc.","India")