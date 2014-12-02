#https://en.wikipedia.org/w/api.php?action=query&list=backlinks&bltitle=Sachin%20Tendulkar&bllimit=500&blnamespace=0&format=json
import urllib2
import urllib
import json
import re
import math
from pymongo import MongoClient
from variables import mongo_url

clients = MongoClient(mongo_url, 27017)
db = clients.wikilinks
posts = db.inlinks

'''Memoize function f.'''
def memo(f):
    table = {}
    def fmemo(*args,**kwargs):
    	if 'clear' in kwargs:
    		table.clear()
    		#print 'MEM0 CLEARED'
        if args not in table:
            table[args] = f(*args)
            table[(args[1],args[0])] = table[args]
        return table[args]
    fmemo.memo = table
    return fmemo

def backlinks(title):
	#Get links from web if not available in database.
	return [] #SPEED IS ISSUE :) Remove this if sufficient bandwidth is available.
	title = title.encode('ascii','ignore')
	url = 'https://en.wikipedia.org/w/api.php?action=query&list=backlinks&bllimit=500&blnamespace=0&format=json&bltitle='+urllib.quote_plus(title)
	opener = urllib2.build_opener()
	infile = opener.open(url)
	response = infile.read()
	jsonify = json.loads(response)
	pages = []
	subjson = jsonify["query"]["backlinks"]
	for i in subjson:
		pages.append(i['title'])
	if 'query-continue' in jsonify:
		pages = pages + backlinks_continue(title,jsonify['query-continue']['backlinks']['blcontinue'],500)
	#print pages
	return pages

def backlinks_continue(title,blcontinue,count):
	print "Querying..."+blcontinue+"..."+str(count)
	count += 500
	url = 'https://en.wikipedia.org/w/api.php?action=query&list=backlinks&bllimit=500&blnamespace=0&format=json&bltitle='+urllib.quote_plus(title)+'&blcontinue='+blcontinue
	opener = urllib2.build_opener()
	infile = opener.open(url)
	response = infile.read()
	jsonify = json.loads(response)
	pages = []
	subjson = jsonify["query"]["backlinks"]
	for i in subjson:
		pages.append(i['title'])
	if 'query-continue' in jsonify:
		pages = pages + backlinks_continue(title,jsonify['query-continue']['backlinks']['blcontinue'],count)
	return pages

def backlinks_mongo(title):
	pages = []
	t=posts.find_one({'page':title},{'page':0,'_id':0})
	try:
		pages = t['link']
	except:
		pages = backlinks(title)
	return pages

@memo
def relatedness(title1,title2,clear=False):
	if title1=='' and title2=='' and clear==True:
		return 0
	inpages1 = backlinks_mongo(title1)
	inpages2 = backlinks_mongo(title2)
	total_pages = 12165935
	len1 = len(inpages1)
	len2 = len(inpages2)
	min12 = min(len1,len2)
	max12 = max(len1,len2)
	s = set(inpages2)
	result = [x for x in inpages1 if x in s]
	intersection = len(result)
	if intersection == 0 or min12 == 0:
		return 0.00
	related_score = (math.log(max12) - math.log(intersection))/(17.3141503911 - math.log(min12))
	return 1-related_score

def relatedness_bulk(title1,list2):
	inpages1 = backlinks_mongo(title1)
	len1 = len(inpages1)
	s = set(inpages1)
	rel = {}
	for title2 in list2:
		inpages2 = backlinks_mongo(title2)
		len2 = len(inpages2)
		min12 = min(len1,len2)
		max12 = max(len1,len2)
		result = [x for x in inpages2 if x in s]
		intersection = len(result)
		if intersection == 0 or min12 == 0:
			rel[title2] = 0.00
		rel[title2] = 1 - ((math.log(max12) - math.log(intersection))/(17.3141503911 - math.log(min12)))
	return rel

def jaccard_relatedness(title1,title2):
	inpages1 = backlinks_mongo(title1)
	inpages2 = backlinks_mongo(title2)
	intersection = len(set(inpages1) & set(inpages2))
	union = len(set(inpages1 + inpages2))
	#print intersection,union
	related_score = intersection*1.0/union
	return related_score

def normalized_relatedness(title1,title_list2):
	#Assuming all the mentions are referred by the same name. Edit this if you have the exact count of anchors
	#Normalizing based on the number of inlinks
	counts = []
	scores = []
	inpages1 = backlinks_mongo(title1)
	for i in title_list2:
		#print title1,i
		inpages2 = backlinks_mongo(i)
		#counts.append(len(inpages2))
		counts.append(math.log(1+len(inpages2)))
		total_pages = 4508646
		min12 = min(len(inpages1),len(inpages2))
		max12 = max(len(inpages1),len(inpages2))
		intersection = len(set(inpages1) & set(inpages2))
		
		if intersection == 0 or min12 == 0 or max12==0:
			scores.append(0.01)
			continue
		related_score = (math.log(max12) - math.log(intersection))/(math.log(total_pages) - math.log(min12))
		#print math.log(max12),math.log(intersection),math.log(total_pages),math.log(min12),related_score
		scores.append(1 - related_score)
	#print scores,counts
	scoresC = [a*b for a,b in zip(scores,counts)]
	return [x/(sum(counts)) for x in scoresC] #max for two same things is .314

def disambiguations(lists):
	pass


if __name__ == '__main__':
	print relatedness('India','United_States')
	print normalized_relatedness('Fruit',['Apple','Apple_Inc.','Box','Orange_(fruit)','Hass_avocado']) #[0.3420885634811631, 0.12812822696562526]
	print normalized_relatedness('Yahoo!',['Google_Search', 'Google', 'Googled', 'Googal,_Devadurga', 'Google.org']) #
	#[0.11152912524208182, 0.21840898991493984, 0.01995233326674351, 0.0010523800013526655, 0.09687832295861436]
	# print relatedness('Google_Search', 'Yahoo!') #.569
	# print relatedness('Fruit','Apple')
	# print relatedness('Forbidden_fruit','Apple')
	# print relatedness('Fruit','Apple_Inc.')
	# print relatedness('Apple_Inc.','Forbidden_fruit')
	# print relatedness('Yahoo!','Google') #.4005
	# print relatedness('Yahoo!','Googled') #.5326
	# print relatedness('Yahoo!','Googal,_Devadurga') # 0
	# print relatedness('Yahoo!','Google.org') # .5762
