from newAnchors import get_mentions_candidates
import requests
import re
import operator
import multiprocessing as mp

from bottle import route, run,get, post,request,static_file,template,response
import json

from sklearn.ensemble import GradientBoostingRegressor
import cPickle

from variables import ritter_url,cmu_url


stop = set(["a","a's","able","about","above","according","accordingly","across","actually","after","afterwards","again","against","ain't","all","allow","allows","almost","alone","along","already","also","although","always","am","among","amongst","an","and","another","any","anybody","anyhow","anyone","anything","anyway","anyways","anywhere","apart","appear","appreciate","appropriate","are","aren't","around","as","aside","ask","asking","associated","at","available","away","awfully","b","be","became","because","become","becomes","becoming","been","before","beforehand","behind","being","believe","below","beside","besides","best","better","between","beyond","both","brief","but","by","c","c'mon","c's","came","can","can't","cannot","cant","cause","causes","certain","certainly","changes","clearly","co","com","come","comes","concerning","consequently","consider","considering","contain","containing","contains","corresponding","could","couldn't","course","currently","d","definitely","described","despite","did","didn't","different","do","does","doesn't","doing","don't","done","down","downwards","during","e","each","edu","eg","eight","either","else","elsewhere","enough","entirely","especially","et","etc","even","ever","every","everybody","everyone","everything","everywhere","ex","exactly","example","except","f","far","few","fifth","first","five","followed","following","follows","for","former","formerly","forth","four","from","further","furthermore","g","get","gets","getting","given","gives","go","goes","going","gone","got","gotten","greetings", "great","h","had","hadn't","happens","hardly","has","hasn't","have","haven't","having","he","he's","hello","help","hence","her","here","here's","hereafter","hereby","herein","hereupon","hers","herself","hi","him","himself","his","hither","hopefully","how","howbeit","however","i","i'd","i'll","i'm","i've","ie","if","ignored","imagine","immediate","in","inasmuch","inc","indeed","indicate","indicated","indicates","inner","insofar","instead","into","inward","is","isn't","it","it'd","it'll","it's","its","itself","j","just","k","keep","keeps","kept","know","knows","known","l","last","lately","later","latter","latterly","least","less","lest","let","let's","like","liked","likely","little","look","looking","looks","ltd","m","mainly","many","may","maybe","me","mean","meanwhile","merely","might","more","moreover","most","mostly","much","must","my","myself","n","name","namely","nd","near","nearly","necessary","need","needs","neither","never","nevertheless","new","next","nine","no","nobody","non","none","noone","nor","normally","not","nothing","novel","now","nowhere","o","obviously","of","off","often","oh","ok","okay","old","on","once","one","ones","only","onto","or","other","others","otherwise","ought","our","ours","ourselves","out","outside","over","overall","own","p","particular","particularly","per","perhaps","placed","please","plus","possible","presumably","probably","provides","q","que","quite","qv","r","rather","rd","re","ready","really","reasonably","regarding","regardless","regards","relatively","respectively","right","s","said","same","saw","say","saying","says","second","secondly","see","seeing","seem","seemed","seeming","seems","seen","self","selves","sensible","sent","serious","seriously","seven","several","shall","she","should","shouldn't","since","six","so","some","somebody","somehow","someone","something","sometime","sometimes","somewhat","somewhere","soon","sorry","specified","specify","specifying","still","sub","such","sup","sure","t","t's","take","taken","tell","tends","th","than","thank","thanks","thanx","that","that's","thats","the","their","theirs","them","themselves","then","thence","there","there's","thereafter","thereby","therefore","therein","theres","thereupon","these","they","they'd","they'll","they're","they've","think","third","this","thorough","thoroughly","those","though","thr","three","through","throughout","thru","thus","to","today","together","too","took","toward","towards","tried","tries","truly","try","trying","twice","two","u","un","under","unfortunately","unless","unlikely","until","unto","up","upon","us","use","used","useful","uses","using","usually","uucp","v","value","various","very","via","viz","vs","w","want","wants","was","wasn't","way","we","we'd","we'll","we're","we've","welcome","well","went","were","weren't","what","what's","whatever","when","whence","whenever","where","where's","whereafter","whereas","whereby","wherein","whereupon","wherever","whether","which","while","whither","who","who's","whoever","whole","whom","whose","why","will","willing","wish","with","within","without","won't","wonder","would","would","wouldn't","x","y","yes","yet","you","you'd","you'll","you're","you've","your","yours","yourself","yourselves","z","zero"])

def is_substring_mention(mention,all_mentions):	
	all_mentions.remove(mention)
	all_length = set([])
	word_len = len(mention.split())
	for i in all_mentions:
		all_mentions_words = i.split()
		for j in range(len(all_mentions_words)):
			for k in range(j,len(all_mentions_words)+1):
				#print k,j,all_mentions_words[j:k]
				if k-j == word_len:
					all_length.add(' '.join(all_mentions_words[j:k]))
		#print mention,i,all_length
	if mention in all_length:
		return 1.0
	return 0.0


def ritter_chunks(tweet):
	url = ritter_url
	proxies = {"http": "","https": ""}
	params ={
	'tweet':tweet
	}
	r = requests.post(url, data=params, proxies=proxies)
	tags = r.text.split(' ')
	#print tags
	return tags

def CMU_tags(tweet):
	url = cmu_url
	proxies = {"http": "","https": ""}
	params ={
	'tweet':tweet
	}
	r = requests.post(url, data=params, proxies=proxies)
	tags = r.text.split('#$%^')
	dict_tags = []
	for i in range(0,len(tags)-1,2):
		dict_tags.append((tags[i].lower().strip(),tags[i+1]))
	return dict_tags

def get_cmupos_count(pos_tags):
	total = 0.0
	tags = {"!":0,"^":0,"D":0,"V":0,"A":0,"N":0,"O":0,"P":0,"G":0}
	for i in pos_tags:
		if i[1] in tags:
			tags[i[1]] += 1
			total += 1
	if total == 0.0:
		return tags
	for i in tags:
		tags[i] /= total
	return tags

def get_special_char(tweet):
	count = 0
	total = 0.0
	for i in tweet:
		if len(re.sub("[^A-Za-z0-9 ]","",i)) == 0:
			count += 1
		total += 1
	return count/total

def no_words(tweet):
	return len(tweet.split())

def get_capital_names(tweet):
	count = 0
	total = 0.0
	for i in tweet.split():
		if len(re.sub("[A-Z]","",i[:1])) == 0:
			count += 1
		total += 1

	return count/total

def get_stopwords(tweet):
	count = 0;
	total = 0.0
	for i in tweet.split():
		if i in stop:
			count += 1
		total += 1.0
	return 1 - count/total

def get_chunks(tags):
	chunks = []
	part = ""
	for i in tags:
		splits = str(i).strip().split("/")
		if len(splits) < 4:
			continue
		if splits[1][:2]=="B-":
			if len(part) > 0:
				chunks.append(part.strip().lower())
			part = splits[0] + " "
		elif splits[1][:2] == "I-" or splits[3][:2]=="I-":
			part += splits[0] + " "
		else:
			if len(part) > 0:
				chunks.append(part.strip().lower())
			part = ""
	if len(part) > 0:
		chunks.append(part.strip().lower())
	return chunks

def get_pos_count(pos_tags):
	#pos_tags = self.ritter_chunks(tweet)
	#print pos_tags
	total = 0.0
	tags = {"DT":0,"NN":0,"IN":0,"VB":0,"JJ":0,"HT":0,"US":0,"UR":0}
	for i in pos_tags:
		splits = str(i).strip().split("/")
		if len(splits) < 4:
			continue
		if splits[2][:2] in tags:
			tags[splits[2][:2]] += 1
			total += 1
	if total == 0.0:
		return tags
	for i in tags:
		tags[i] /= total
	return tags

def get_poschunk_count(pos_tags):
	#pos_tags = self.ritter_chunks(tweet)
	#print pos_tags
	total = 0.0
	tags = {"B-NP":0,"I-NP":0,"B-VP":0,"I-VP":0,"B-PP":0,"I-PP":0,"B-ADVP":0,"I-ADVP":0}
	for i in pos_tags:
		splits = str(i).strip().split("/")
		if len(splits) < 4:
			continue
		if splits[3] in tags:
			tags[splits[3]] += 1
			total += 1
	if total == 0.0:
		return tags
	for i in tags:
		tags[i] /= total
	return tags

def get_entity_count(pos_tags):
	#pos_tags = self.ritter_chunks(tweet)
	#print pos_tags
	total = 0.0
	tags = {"B-ENTITY":0,"I-ENTITY":0}
	for i in pos_tags:
		splits = str(i).strip().split("/")
		if len(splits) < 4:
			continue
		if splits[1] in tags:
			tags[splits[1]] += 1
			total += 1
	if total == 0.0:
		return tags
	for i in tags:
		tags[i] /= total
	return tags

def parallel_features(i,f_i,tags,CMUTags,chunks,query,regression):
	feat = []
	if len(f_i[0]) > 2:
		feat = ([f_i[0][0][1], f_i[0][1][1], f_i[0][2][1],f_i[2]*1.0/f_i[1]])
		#feat = ([sum(f_i[0][0][1])*.5, sum(f_i[0][1][1])*.5, sum(f_i[0][2][1])*.5,f_i[2]*1.0/f_i[1]])
	elif len(f_i[0]) > 1:
		feat = ([f_i[0][0][1], f_i[0][1][1], 0.0,f_i[2]*1.0/f_i[1]])
		#feat = ([sum(f_i[0][0][1])*.5, sum(f_i[0][1][1])*.5, 0.0,f_i[2]*1.0/f_i[1]])
	else:
		feat = ([f_i[0][0][1], 0.0, 0.0,f_i[2]*1.0/f_i[1]])
		#feat = ([sum(f_i[0][0][1])*.5, 0.0, 0.0,f_i[2]*1.0/f_i[1]])
	feat.append(f_i[2])
	feat.append(f_i[1])
	if i in chunks:
		feat.append(1)
	else:
		feat.append(0)
	feat.append(get_special_char(i))
	feat.append(no_words(i))
	feat.append(get_capital_names(i))
	feat.append(get_stopwords(i))
	
	twit = query.lower().split(i)
	begin = len(twit[0].split())
	end = begin + len(i.split())
	pos_f = get_pos_count(tags[begin:end])
	#print pos_f

	feat.append(pos_f['DT'])
	feat.append(pos_f['NN'])
	feat.append(pos_f['IN'])
	feat.append(pos_f['VB'])
	feat.append(pos_f['JJ'])
	feat.append(pos_f['HT'])
	feat.append(pos_f['US'])
	feat.append(pos_f['UR'])

	######ADDING EXTRA FEATURES#####
	pos_chunk_f = get_poschunk_count(tags[begin:end])
	feat.append(pos_chunk_f['B-NP'])
	feat.append(pos_chunk_f['I-NP'])
	feat.append(pos_chunk_f['B-VP'])
	feat.append(pos_chunk_f['I-VP'])
	feat.append(pos_chunk_f['B-PP'])
	feat.append(pos_chunk_f['I-PP'])
	feat.append(pos_chunk_f['B-ADVP'])
	feat.append(pos_chunk_f['I-ADVP'])

	pos_entity_f = get_entity_count(tags[begin:end])
	feat.append(pos_entity_f['B-ENTITY'])
	feat.append(pos_entity_f['I-ENTITY'])
	######ENDING EXTRA FEATURES######

	cmu_pos = get_cmupos_count(CMUTags[begin:end])
	feat.append(cmu_pos['!'])
	feat.append(cmu_pos['^'])
	feat.append(cmu_pos['D'])
	feat.append(cmu_pos['V'])
	feat.append(cmu_pos['A'])
	feat.append(cmu_pos['N'])
	feat.append(cmu_pos['O'])
	feat.append(cmu_pos['P'])
	feat.append(cmu_pos['G'])

	#Is submention
	if regression:
		feat.append(is_substring_mention(i,f.keys()))

	return (i,feat)

nproc = 6   # maximum number of simultaneous processes desired
pool = mp.Pool(processes=nproc)

def parallel_processing(args_list):
    results = [pool.apply_async(parallel_features, args=(x[0],x[1],x[2],x[3],x[4],x[5],x[6],)) for x in args_list]
    output = [p.get() for p in results]
    #print 'Time Elaspsed: ',sum(output)[-1]
    return output


class get_features():
	def __init__(self):
		pass

	def get_X(self,query,label=True,mentions=False,regression=False):
		query = query.strip()
		print query
		tags = ritter_chunks(query)
		CMUTags = CMU_tags(query)
		chunks = get_chunks(tags)
		f = get_mentions_candidates(query)
		#f = get_mentions_candidates(query,get_sep=True)
		
		for i in stop:
			if i in f:
				del f[i]
		
		X = []
		args_list = []
		for i in f:
			args_list.append((i,f[i],tags,CMUTags,chunks,query,regression))
		features = parallel_processing(args_list)
		for i in features:	
			if label:
				X.append((i[0],i[1]))
			else:
				X.append(i[1])
		if mentions:
			return X,f
		else:
			return X

def cross_validate():
	p = []
	r = []
	f = open('./data/mannual_anno.tsv')
	f1 = open('./data/rate_res.txt','w')
	data = f.readlines()
	points = [x * 0.05 for x in range(0, 21)]
	for rate in points:
		for i in data[700:]:
			tweet_text = i.replace('#',' ').replace('@',' ').split('\t')[0]
			mentions = i.split('\t')[1:]
			for j in range(len(mentions)):
				mentions[j] = mentions[j].split('--')[0].strip().lower()
			detected = men_predict.predict(tweet_text,rate).keys()
			if '' in mentions:
				mentions.remove('')
			print mentions,detected
			if len(set(detected))>0:
				precision = len(set(mentions) & set(detected))*1.0/len(set(detected))
				p.append(precision)
			else:
				precision = 'ND'
			if len(set(mentions))>0:
				recall = len(set(mentions) & set(detected))*1.0/len(set(mentions))
				r.append(recall)
			else:
				recall = 'ND'
			print precision,recall
			#print tweet_text,mentions
		print sum(p)/len(p)
		print sum(r)/len(r)
		f1.write(str(rate)+"\t"+str(sum(p)/len(p))+"\t"+str(sum(r)/len(r))+"\n")
		f1.flush()
	f1.close() 

def train_model():
	fil = get_training_data()
	X = []
	y = []
	f = get_features()
	for query in fil:
		for feat in f.get_X(query):
			X.append(feat[1])
			if feat[0] in fil[query]:
				y.append(1)
			else:
				y.append(0)
	print len(X),len(y),X,y
	clf = GradientBoostingRegressor()
	clf.fit(X, y) 
	print clf 
	print clf.score(X, y)
	filename = '/home/romil/Desktop/Model4/digits_classifier.joblib.pkl'
	_ = joblib.dump(clf, filename)
	with open('/home/romil/Desktop/Model4/X.pkl', 'wb') as fid:
		cPickle.dump(X, fid)
	with open('/home/romil/Desktop/Model4/y.pkl', 'wb') as fid:
		cPickle.dump(y, fid)

def cmp(x,y):
	#print x,y
	return len(x[0]) - len(y[0])


class Predict():
	def __init__(self,regression=False):
		#filename = '/home/romil/Desktop/Model5/modelx38_small.pkl'
		#filename = '/home/romil/Desktop/Datasets/Tagme/tagme_splits/clf_a-l.pkl'
		filename = '/home/romil/Desktop/Datasets/My_mentions/clf.pkl'
		#filename = '/home/romil/Desktop/Datasets/User/clf.pkl'
		#filename_regression = '/home/romil/Desktop/Datasets/el-helpfulness-dataset-regression/clf_classify.pkl'
		filename_regression = '/home/romil/Desktop/Datasets/el-helpfulness-dataset-regression/clf.pkl'
		#filename_regression = '/home/romil/Desktop/RegressionModel/model_svr_2anno.pkl'
		#filename = '/home/romil/Desktop/Model/gbr.pkl'
		#filename = '/home/romil/Desktop/Model3/tweets/smallmodel.pkl'
		self.regression = regression
		if regression:
			with open(filename_regression, 'rb') as fid:                                 
				self.clf = cPickle.load(fid)
		else:
			with open(filename, 'rb') as fid:                                 
				self.clf = cPickle.load(fid)

	def predict(self,tweet,cutoff=None):
		if self.regression and not cutoff:
			cutoff = 1.3
		elif not self.regression and not cutoff:
			cutoff = .25
		clf = self.clf
		features,return_list = get_features().get_X(tweet.strip(),mentions=True,regression=self.regression)
		#return return_list
		scores = {}
		for i in features:
			scores[i[0]] = clf.predict(i[1])[0]
		sorted_dic = sorted(scores.iteritems(), cmp=cmp)[::-1]
		#sorted_dic = sorted(scores.iteritems(), key=operator.itemgetter(1))[::-1]
		#print sorted_dic
		active = [True for i in range(len(sorted_dic))]
		final_set = []
		alternate_set = []
		tweet_str = re.split('[ -.,]',tweet.lower().strip())
		for i in range(len(sorted_dic)):
			if sorted_dic[i][1] > cutoff:
				flag = True
				for j in sorted_dic[i][0].split():
					if j in tweet_str:
						tweet_str.remove(j)
					else:
						flag = False 
						break
				if flag:
					final_set.append(sorted_dic[i][0])
			else:
				flag = True
				for j in sorted_dic[i][0].split():
					if j not in tweet_str:
						flag = False
						break
				if flag:
					alternate_set.append(sorted_dic[i][0])
		test_cand = {}
		for i in final_set:
			test_cand[i] = return_list[i]
			del return_list[i]	
		return test_cand

	def predict_class(self,tweet):
		clf = self.clf
		features,return_list = get_features().get_X(tweet.strip(),mentions=True,regression=self.regression)
		#return return_list
		scores = {}
		for i in features:
			scores[i[0]] = clf.predict(i[1])[0]
		sorted_dic = sorted(scores.iteritems(), cmp=cmp)[::-1]
		#sorted_dic = sorted(scores.iteritems(), key=operator.itemgetter(1))[::-1]
		active = [True for i in range(len(sorted_dic))]
		final_set_rank1 = []
		final_set_rank2 = []
		final_set_rank3 = []
		final_set_rank4 = []
		alternate_set = []
		tweet_str = re.split('[ -.,]',tweet.lower().strip())
		for i in range(len(sorted_dic)):
			if sorted_dic[i][1] > .25:
				flag = True
				for j in sorted_dic[i][0].split():
					if j in tweet_str:
						tweet_str.remove(j)
					else:
						flag = False 
						break
				if flag:
					final_set_rank1.append(sorted_dic[i][0])
		for i in range(len(sorted_dic)):
			if sorted_dic[i][1] > .2:
				flag = True
				for j in sorted_dic[i][0].split():
					if j in tweet_str:
						tweet_str.remove(j)
					else:
						flag = False 
						break
				if flag:
					final_set_rank2.append(sorted_dic[i][0])
		for i in range(len(sorted_dic)):
			if sorted_dic[i][1] > .1:
				flag = True
				for j in sorted_dic[i][0].split():
					if j in tweet_str:
						tweet_str.remove(j)
					else:
						flag = False 
						break
				if flag:
					final_set_rank3.append(sorted_dic[i][0])
		for i in range(len(sorted_dic)):
			if sorted_dic[i][1] > .01:
				flag = True
				for j in sorted_dic[i][0].split():
					if j in tweet_str:
						tweet_str.remove(j)
					else:
						flag = False 
						break
				if flag:
					final_set_rank4.append(sorted_dic[i][0])

			else:
				flag = True
				for j in sorted_dic[i][0].split():
					if j not in tweet_str:
						flag = False
						break
				if flag:
					alternate_set.append(sorted_dic[i][0])
		test_cand_rank1 = {}
		test_cand_rank2 = {}
		test_cand_rank3 = {}
		test_cand_rank4 = {}
		for i in final_set_rank1:
			test_cand_rank1[i] = return_list[i]
			del return_list[i]	
		for i in final_set_rank2:
			if i in return_list:
				test_cand_rank2[i] = return_list[i]
				del return_list[i]	
		for i in final_set_rank3:
			if i in return_list:
				test_cand_rank3[i] = return_list[i]
				del return_list[i]	
		for i in final_set_rank4:
			if i in return_list:
				test_cand_rank4[i] = return_list[i]
				del return_list[i]	
		return [test_cand_rank1,test_cand_rank2,test_cand_rank3,test_cand_rank4]
		return test_cand_rank1.keys(),test_cand_rank2.keys(),test_cand_rank3.keys(),test_cand_rank4.keys()

#men_predict = Predict(regression=False)
@route('/process',method='POST')
def server():
	global men_predict
	line = request.forms.get('tweet')
	line = line.strip()
	print line
	return '\t'.join(men_predict.predict(line).keys())


if __name__ == '__main__':
	#train_model()
	men_predict = Predict(regression=False)
	print men_predict.predict_class('Coffee shop Coffee and a couple of doughnuts won\'t cost you too much.')
	print men_predict.predict_class(' lol, *snatches bottle of vodka and smashes it*  No booze around me!')
	print men_predict.predict(' OMG! Will Smith is playing the Governor on Walking Dead').keys()
	#print men_predict.predict('that is cool we only have a AAA team here in Portland Going to a game tomorrow').keys()
	#print men_predict.predict('Apple and Blackberry are fruits').keys()
	#print men_predict.predict('Sachin Dev Burman is a great musician').keys()
	#print men_predict.predict('Yahoo! Brazil looks like on thr way out of World Cup').keys()
	#print men_predict.predict('Steve Jobs, Bill Gates and Apple').keys()
	#print men_predict.predict_class('iwatch On my Xmas list for this year even if its the only gift I get')
	#print men_predict.predict('yahoo labs at dublin are awesome place to work',.35).keys()
	#print men_predict.predict('Matt Schaub did play for the Cavaliers').keys()
	#print men_predict.predict('#trevortruth is it bad that my favorite band (profile pic) has a song about blood.. I gave you blood, blood, gallons of the stuff').keys()
	#print men_predict.predict('Sachin is a great player. Infact, he is a god.').keys()
	#for i in open('./data/test'):
	#	print men_predict.predict_class(i)#.keys()
	#run(host='localhost', port=8082)

