import urllib2
import urllib
import json
import re
from elasticsearch import Elasticsearch
from pymongo import MongoClient
from variables import mongo_url

def jaccard(wordlist1,wordlist2):
	intersection = set(wordlist1) & set(wordlist2)
	union = set(wordlist2 + wordlist1)
	return len(intersection)*1.0/len(union) 

def text_to_words(text):
	words = re.sub(r'[^a-zA-Z0-9]',' ',text).lower().split(' ')
	return words

def get_title_sim_score(mention,entity):
	entity = entity.replace('_',' ')
	return jaccard(text_to_words(entity), text_to_words(mention))

class Relatedness(object):
	def __init__(self):
		self.clients = MongoClient(mongo_url, 27017)
		self.db = self.clients.wikiabstracts
		self.posts = self.db.words

		self.stopwords=["a's", "able", "about", "above", "according", "accordingly", "across", "actually", "after", "afterwards", "again", "against", "ain't", "all", "allow", "allows", "almost", "alone", "along", "already", "also", "although", "always", "am", "among", "amongst", "an", "and", "another", "any", "anybody", "anyhow", "anyone", "anything", "anyway", "anyways", "anywhere", "apart", "appear", "appreciate", "appropriate", "are", "aren't", "around", "as", "aside", "ask", "asking", "associated", "at", "available", "away", "awfully", "be", "became", "because", "become", "becomes", "becoming", "been", "before", "beforehand", "behind", "being", "believe", "below", "beside", "besides", "best", "better", "between", "beyond", "both", "brief", "but", "by", "c'mon", "c's", "came", "can", "can't", "cannot", "cant", "cause", "causes", "certain", "certainly", "changes", "clearly", "co", "com", "come", "comes", "concerning", "consequently", "consider", "considering", "contain", "containing", "contains", "corresponding", "could", "couldn't", "course", "currently", "definitely", "described", "despite", "did", "didn't", "different", "do", "does", "doesn't", "doing", "don't", "done", "down", "downwards", "during", "each", "edu", "eg", "eight", "either", "else", "elsewhere", "enough", "entirely", "especially", "et", "etc", "even", "ever", "every", "everybody", "everyone", "everything", "everywhere", "ex", "exactly", "example", "except", "far", "few", "fifth", "first", "five", "followed", "following", "follows", "for", "former", "formerly", "forth", "four", "from", "further", "furthermore", "get", "gets", "getting", "given", "gives", "go", "goes", "going", "gone", "got", "gotten", "greetings", "had", "hadn't", "happens", "hardly", "has", "hasn't", "have", "haven't", "having", "he", "he's", "hello", "help", "hence", "her", "here", "here's", "hereafter", "hereby", "herein", "hereupon", "hers", "herself", "hi", "him", "himself", "his", "hither", "hopefully", "how", "howbeit", "however", "i'd", "i'll", "i'm", "i've", "ie", "if", "ignored", "immediate", "in", "inasmuch", "inc", "indeed", "indicate", "indicated", "indicates", "inner", "insofar", "instead", "into", "inward", "is", "isn't", "it", "it'd", "it'll", "it's", "its", "itself", "just", "keep", "keeps", "kept", "know", "knows", "known", "last", "lately", "later", "latter", "latterly", "least", "less", "lest", "let", "let's", "like", "liked", "likely", "little", "look", "looking", "looks", "ltd", "mainly", "many", "may", "maybe", "me", "mean", "meanwhile", "merely", "might", "more", "moreover", "most", "mostly", "much", "must", "my", "myself", "name", "namely", "nd", "near", "nearly", "necessary", "need", "needs", "neither", "never", "nevertheless", "new", "next", "nine", "no", "nobody", "non", "none", "noone", "nor", "normally", "not", "nothing", "novel", "now", "nowhere", "obviously", "of", "off", "often", "oh", "ok", "okay", "old", "on", "once", "one", "ones", "only", "onto", "or", "other", "others", "otherwise", "ought", "our", "ours", "ourselves", "out", "outside", "over", "overall", "own", "particular", "particularly", "per", "perhaps", "placed", "please", "plus", "possible", "presumably", "probably", "provides", "que", "quite", "qv", "rather", "rd", "re", "really", "reasonably", "regarding", "regardless", "regards", "relatively", "respectively", "right", "said", "same", "saw", "say", "saying", "says", "second", "secondly", "see", "seeing", "seem", "seemed", "seeming", "seems", "seen", "self", "selves", "sensible", "sent", "serious", "seriously", "seven", "several", "shall", "she", "should", "shouldn't", "since", "six", "so", "some", "somebody", "somehow", "someone", "something", "sometime", "sometimes", "somewhat", "somewhere", "soon", "sorry", "specified", "specify", "specifying", "still", "sub", "such", "sup", "sure", "t's", "take", "taken", "tell", "tends", "th", "than", "thank", "thanks", "thanx", "that", "that's", "thats", "the", "their", "theirs", "them", "themselves", "then", "thence", "there", "there's", "thereafter", "thereby", "therefore", "therein", "theres", "thereupon", "these", "they", "they'd", "they'll", "they're", "they've", "think", "third", "this", "thorough", "thoroughly", "those", "though", "three", "through", "throughout", "thru", "thus", "to", "together", "too", "took", "toward", "towards", "tried", "tries", "truly", "try", "trying", "twice", "two", "un", "under", "unfortunately", "unless", "unlikely", "until", "unto", "up", "upon", "us", "use", "used", "useful", "uses", "using", "usually", "value", "various", "very", "via", "viz", "vs", "want", "wants", "was", "wasn't", "way", "we", "we'd", "we'll", "we're", "we've", "welcome", "well", "went", "were", "weren't", "what", "what's", "whatever", "when", "whence", "whenever", "where", "where's", "whereafter", "whereas", "whereby", "wherein", "whereupon", "wherever", "whether", "which", "while", "whither", "who", "who's", "whoever", "whole", "whom", "whose", "why", "will", "willing", "wish", "with", "within", "without", "won't", "wonder", "would", "would", "wouldn't", "yes", "yet", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves", "zero","ref","www","http","com","url","web"]
		self.es = Elasticsearch(mongo_url)

	def wikipage_words(self,title):
		#print urllib.quote_plus(title)
		url = 'https://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles='+urllib.quote_plus(title)
		opener = urllib2.build_opener()
		infile = opener.open(url)
		response = infile.read()
		jsonify = json.loads(response)
		subjson = jsonify["query"]["pages"]
		key = subjson.keys()
		data = subjson[key[0]]['revisions'][0]['*'].encode('ascii', 'ignore')
		words = re.sub(r'[^a-zA-Z0-9]',' ',data).split(' ')
		a = [x for x in words if len(x)>2 and len(x)<15]
		a = [x for x in a if x not in self.stopwords]
		return a


	def wikipedia_abstract_elastic(self,title):
		results = self.es.search(index="wikipedia", doc_type="abstracts", body={'query':{
			'match':{'key':title}
			}})['hits']['hits']
		#print len(results)
		for i in results:
			if i['_source']['key'] == title:
				abstract = i['_source']['value']
				words = re.sub(r'[^a-zA-Z0-9]',' ',abstract).split(' ')
				a = [x for x in words if len(x)>2 and len(x)<15]
				a = [x for x in a if x not in self.stopwords]
				return a

	def wikipedia_abstract(self,title):
		t=self.posts.find_one({'key':title},{'page':0,'_id':0})
		try:
			#print t['value']
			return t['value']
		except:
			return []

	def get_abstract_similarity(self,tweet,title):
		return jaccard(text_to_words(tweet), self.wikipedia_abstract(title))


if __name__ == '__main__':
	relatedness = Relatedness()
	print get_title_sim_score('Steve Jobs','Steve_Jobs')
	print relatedness.get_abstract_similarity("Steve_Jobs, Bill Gates and Apple","Bill_Gates")
	print jaccard(text_to_words("Apple is an awesome company!!"), relatedness.wikipage_words("Apple_Inc."))
	#print wikipeda_abstract('India')
