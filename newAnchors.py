from pymongo import MongoClient
import re
import operator
import json	
#from get_related_tweets import get_tweets
import urllib2
import requests
from searchMyIndex import *
from variables import mongo_url,ritter_url

clients = MongoClient(mongo_url, 27017)
db = clients.anchorDB
posts = db.anchors
gcd_searcher = GCDSearcher()

def get_pages(anchor,clear=False):
	if anchor == '' and clear == True:
		return {},0,0
	t=posts.find_one({'anchor':anchor},{'anchor':0,'_id':0})
	if not t:
		return {},0,0
	total = t['total_freq']+t['anchor_freq']
	total_link = t['anchor_freq']
	dictionaries = []

	#for i in t['pages']:
#		ids = i['page_id']
#		dictionaries.append((ids,i['page_freq']))
	#print total
	return t['pages'],total,total_link

def get_links_inprob(anchor):
	dictionaries,total,total_link = get_pages(anchor)
	if total == 0:
		return 0,[],0,0
	return total_link/(total*1.0),dictionaries,total,total_link


def cmp(x,y):
	#print sum(x[1]),sum(y[1])
	if (sum(x[1]) - sum(y[1]))>0:
		return 1
	else:
		return-1

def get_mentions_candidates(mention,hashtag=False,get_sep=False,cutoff=0.01):
	'''Set get_sep true if you want to get seperate probability for Wiki Anchors and GCD'''
	url = ritter_url
	proxies = {"http": "","https": ""}
	params ={
	'tweet':mention
	}
	r = requests.post(url, data=params, proxies=proxies)
	tags = r.text.split(' ')
	#print r.text

	wiki_clients = MongoClient(mongo_url, 27017)
	wiki_db = wiki_clients.wikiPageDB
	wiki_posts = wiki_db.wikiPageTitle
	prevScore = -1
	prevMention = ""
	string = mention.lower().strip()
	mentions = []
	mention_dict = {}
	cand_titles = []
	#string = re.sub("[^A-Za-z0-9 ]","",string)
	string = re.split('[ -.,]',string)
	if '' in string:
		string.remove('')
	length = len(string)
	i = 0
	while i < length:
		for j in range(min(length,i+6),i,-1):
			sub = ""
			cand_titles = {}
			for k in range(i,j):
				sub = sub + string[k] + " "
			sub = sub.strip()
			link_prob,candidates,total,total_link = get_links_inprob(sub.strip().lower())
			#print sub,link_prob
			if link_prob>cutoff: #Variable Here
				####
				#RULE for MENTION PRUNING
				#REPLACED BY CLASSIFIER NOW
				####
				'''
				if not hashtag:
					flag = False
				else:
					flag = True
				for o in tags:
					if o.split('/')[0].lower().replace('#','') in sub.lower() and (o.split('/')[2][:2]=='NN' or o.split('/')[2][:2]=='HT'):
						flag = True
						break
				if not flag:
					continue
				#''
				#print sub,prevMention,link_prob,prevScore
				
				if sub in prevMention and link_prob<=prevScore*.3:
					continue
				if sub in prevMention and link_prob>prevScore*3:
					del mention_dict[prevMention]
				'''
				prevMention = sub
				prevScore = link_prob
				mentions.append(sub)
				cand_titles_gcd = gcd_searcher.searcher(sub.strip())
				cand_dict_gcd = {}
				diff = {}
				for k in cand_titles_gcd:
					cand_dict_gcd[k[0]] = k[1]/1.5
				for k in candidates:
					t=wiki_posts.find_one({'pageId':k['page_id']},{'_id':0})
					if t!=None:
						if t['title'] in cand_dict_gcd:
							cand_dict_gcd[t['title']] = cand_dict_gcd[t['title']]  + k['page_freq']/(total_link*2.0)
							diff[t['title']] = (cand_dict_gcd[t['title']],k['page_freq']/(total_link*2.0))
						else:
							cand_dict_gcd[t['title']] = k['page_freq']/(total_link*2.0)
							diff[t['title']] = (0.0,k['page_freq']/(total_link*2.0))
				#print cand_dict_gcd
				if not get_sep:
					cand_titles = sorted(cand_dict_gcd.iteritems(), key=operator.itemgetter(1))
					cand_titles.reverse()
					#print cand_titles[:5]
					mention_dict[sub.strip()] = [cand_titles,total,total_link]
					cand_titles = []
				else:
					cand_titles = sorted(diff.iteritems(), cmp=cmp)
					cand_titles.reverse()
					#print cand_titles[:5]
					mention_dict[sub.strip()] = [cand_titles,total,total_link]
					cand_titles = []

				total = total_link=0
				#i = j-1
				#break
		i+=1
	
	wiki_clients.close()
	return mention_dict

def eval_linkprob():
	f = open('/home/romil/Desktop/Datasets/My_mentions/mannual_anno.tsv')
	data = f.readlines()
	f.close()
	cutoffs = [0.01,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.99]
	for cutoff in cutoffs:
		f1 = open('data/threshresults/'+str(cutoff),'w')
		for tweets in data:
			tweet_text = tweets.split('\t')[0].strip()
			print cutoff,tweet_text
			res = get_mentions_candidates(tweet_text,cutoff=cutoff).keys()
			str_pr = tweet_text
			for i in res:
				str_pr += "\t" + i +'--'+'NO MENTION'
			f1.write(str_pr.strip()+'\n')
			f1.flush()
		f1.close()


if __name__ == '__main__':
	eval_linkprob()
	asd
	# f = open('/home/romil/Desktop/Mentions/mention_annot.tsv')
	# data = f.readlines()
	# f.close()
	# f = open('/home/romil/Desktop/Mentions/mention_annot.tsv','w')
	
	# string = ""
	# for i in data:
	# 	string = i.strip()
	# 	mentions = get_mentions_candidates(i.strip()).keys()
	# 	for j in mentions:
	# 		string += "\t" + j.strip()
	# 	f.write(string.strip()+"\n")
	# 	print string
	# f.close()

	print get_mentions_candidates("iwatch On my Xmas list for this year even if its the only gift I get").keys()
	print get_mentions_candidates("going to visit Yahoo labs in Dublin this year.").keys()
	print get_mentions_candidates("Game of Thrones is out!!").keys()
	print get_mentions_candidates("India is my country",get_sep=True).keys()
	print get_mentions_candidates("Apple is a fruit").keys()
	print get_mentions_candidates('The Buccaneers just gave a $19 million contract to a punter http://t.co/ZYTqUhn via @YahooSports wow').keys()