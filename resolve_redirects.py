#https://en.wikipedia.org/w/api.php?action=query&pageids=21555729&redirects&format=json

#https://en.wikipedia.org/w/api.php?action=query&titles=21555729&redirects&format=json

import requests
import urllib2
import json

def resolve_ids(ids):
	try:
		url = 'https://en.wikipedia.org/w/api.php?action=query&pageids='+str(ids)+'&redirects&format=json'
		opener = urllib2.build_opener()
		infile = opener.open(url)
		response = infile.read()
		#print response
		jsonify = json.loads(response)
		subjson = jsonify["query"]
		if "redirects" in subjson:
			return subjson["redirects"][-1]["to"]
		for key,value in subjson['pages'].iteritems():
			return subjson['pages'][key]["title"]
	except Exception as e:
		print e
		return None

def resolve_title(title):
	try:
		url = 'https://en.wikipedia.org/w/api.php?action=query&titles='+str(title)+'&redirects&format=json'
		#print url
		opener = urllib2.build_opener()
		infile = opener.open(url)
		response = infile.read()
		#print response
		jsonify = json.loads(response)
		subjson = jsonify["query"]
		if "redirects" in subjson:
			return subjson["redirects"][-1]["to"]
		for key,value in subjson['pages'].iteritems():
			return subjson['pages'][key]["title"]
	except:
		return None

if __name__ == '__main__':
	print resolve_title("fruits")
	print resolve_ids(12)