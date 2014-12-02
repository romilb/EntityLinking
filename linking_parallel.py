import functools
import math
import re
import operator
import sys
import time
import cPickle
from sklearn.ensemble import *
from termcolor import colored, cprint
import numpy as np
import multiprocessing as mp
import time
from bottle import route, run,get, post,request,static_file,template,response

import features_parallel
import tagmerelatedness
import resolve_redirects
import relatedness
import get_related_tweets
import get_cosine
#from relatedness import Relatedness,get_title_sim_score
#from inmem_graph import get_topic_sim_server,DBPediaCategories
from mongo_cat_graph import DBPediaCategories
from get_summary import Summary
from searchPageviews import PageviewsSearcher
from searchMyIndex import GCDSearcher
from mart import Disambiguate,Ensemble


dbpedia_categories = DBPediaCategories()
disambiguate = Disambiguate()
mention_detection = features_parallel.Predict()
summary = Summary()
related = relatedness.Relatedness()
twitter = get_related_tweets.TwitterAPI()

nproc = 6   # maximum number of simultaneous processes desired
#pool1 = mp.Pool(processes=nproc/2)

def find_parallel_relatedness(candidates,j):
    start = time.time()
    voteB = 0
    topicB_1 = 0
    topicB_2 = 0
    topicB_3 = 0
    countB = 0.00001
    for l in candidates:
        if l[1]<.01:
            break
        else:
            voteB += (tagmerelatedness.relatedness(j[0],l[0]))*l[1]
            #topicB_1 += (get_topic_sim_server(j[0],l[0],1))*l[1]
            topicB_1 += (dbpedia_categories.get_topic_sim(j[0],l[0],1))*l[1]
            #topicB_2 += (get_topic_sim_server(j[0],l[0],2))*l[1]
            topicB_2 += (dbpedia_categories.get_topic_sim(j[0],l[0],2))*l[1]
            #topicB_3 += (get_topic_sim_server(j[0],l[0],3))*l[1]
            topicB_3 += (dbpedia_categories.get_topic_sim(j[0],l[0],3))*l[1]
            #topicBA_3 = 0
            countB += 1
    end = time.time()
    #print 'Time Elaspsed: ',end-start
    return np.array([voteB/(countB*1.0),topicB_1/(countB*1.0),topicB_2/(countB*1.0),topicB_3/(countB*1.0),end-start])


def parallel_processing(args_list):
    if len(args_list) == 0:
        return [0,0,0,0]
    results = [pool1.apply_async(find_parallel_relatedness, args=(x[0],x[1],)) for x in args_list]
    output = [p.get() for p in results]
    return sum(output)[:-1]

def synchronous_processing(args_list):
    features = [0,0,0,0,0]
    for i in args_list:
        features += find_parallel_relatedness(i[0],i[1])
    return features[:-1]


def get_milne_relatedness(entity1,entity2):
    #tagmerelatedness.py implimentation
    return tagmerelatedness.relatedness(entity1,entity2)

def jaccard_abstract(qstr,wiki_title):
    relatd = related.get_abstract_similarity(qstr,wiki_title)
    return relatd

def get_milne_relatedness_commoness_topics_tweet(candidates,threshold=0,train_candidate=None,this_candidate=None):
    votes = {}
    for i in candidates:
        if this_candidate and i!=this_candidate:
            continue
        prelims = {}
        maxVote = -1
        detected = ""
        j_new = []
        sorted_x = candidates[i][0]
        if threshold != 0:
            if len(sorted_x) > threshold:
                sorted_x = sorted_x[:threshold]
        for j in sorted_x:
            try:
                j_re = resolve_redirects.resolve_title(j[0]).replace(' ','_')
                j_re = (j_re,j[1])
            except:
                j_re = j
            args_list = []
            for k in candidates:
                if i == k:
                    continue
                if train_candidate == None or i in train_candidate:
                    args_list.append((candidates[k][0],j_re))
            #voteBA,topicBA_1,topicBA_2,topicBA_3=parallel_processing(args_list)
            voteBA,topicBA_1,topicBA_2,topicBA_3=synchronous_processing(args_list)
            commoness = j[1]
            #print j,voteBA,topicBA_1,topicBA_2,topicBA_3
            prelims[j[0]] = (voteBA,topicBA_1,topicBA_2,topicBA_3,commoness)
        votes[i] = prelims
    dbpedia_categories.get_parents_recursive('',0,clear=True)
    tagmerelatedness.relatedness('','',clear=True)
    return votes

def get_topic_sim(title1,title2,distance=2):
    return get_topic_sim_server(title1,title2,distance)

def get_user_score():
    pass

def get_recent_tweets_score():
    pass


def get_wiki_summary_similarity(qstr,entity_arr):
    normalized_sim = summary.get_normalized_sim(entity_arr,qstr)
    return_dict = {}
    for i in range(len(entity_arr)):
        return_dict[entity_arr[i]] = normalized_sim[i]
    return return_dict

def get_candidates(qstr):
    candidates = mention_detection.predict(qstr)

def get_title_sim_score(mention,entity):
    return relatedness.get_title_sim_score(mention,entity)

def coherence(self,votes):
    pass
    return coherence(votes)

def print_formatted(feature,comment,score):
    to_print = '0 qid:3 '
    for i in range(len(feature)):
        to_print += str(i+1)+':'+str(feature[i])+' '
    to_print += '# '+repr(comment) + ' ' + repr(score)
    print to_print

def my_diambiguator(max_score,features,disamb_entity):
    cutoff = max_score[0] - .5*max_score[0]
    f_final = []
    max_relad = -999

    for j in features:
        #+j[1][3]/10
        if max_relad<sum(j[1][0:3]) and j[2]>cutoff:
            max_relad=sum(j[1][0:3])

    for j in features:
        if j[2]>cutoff and (sum(j[1][0:3])) >=max_relad:
            f_final.append(j)

    if len(f_final)<=1:
        return (disamb_entity,"")
    elif len(f_final)>=1 and max_relad>0.0:
        return (f_final[0][0],"")
    else:
        max_relad = -999
        for j in features:
            if max_relad<(j[1][5]+j[1][6]/10) and j[2]>cutoff:
                max_relad=(j[1][5]+j[1][6]/10)
        f_final = []
        for j in features:
            if j[2]>cutoff and (j[1][5]+j[1][6]/10)>=max_relad:
                f_final.append(j)
        if len(f_final)>=1 and max_relad>0.0:
            return (f_final[0][0],'RR')
        else:
            max_relad = -999
            for j in features:
                if max_relad<(j[1][4]) and j[2]>cutoff:
                    max_relad=(j[1][4])
                f_final = []
                for j in features:
                    if j[2]>cutoff and (j[1][4])>=max_relad:
                        f_final.append(j)
                if len(f_final)==1:
                    return (f_final[0][0],'RRR')
                else:
                    return (disamb_entity,'RRR')

def predict_parallel_entities(this_candidate,candidates,qstr,train_candidate=None):
    if train_candidate!=None:
        feat1 = get_milne_relatedness_commoness_topics_tweet(candidates,5,train_candidate=train_candidate,this_candidate=this_candidate)
    else:
        feat1 = get_milne_relatedness_commoness_topics_tweet(candidates,5,this_candidate=this_candidate)
    #print this_candidate,feat1,'STEP 2'
    linkages = []
    max_score = -99999
    disamb_entity = ""
    for i in feat1:
        features = []
        linkages = feat1[i].keys()
        summary_sim = get_wiki_summary_similarity(qstr.lower().replace(i,''),linkages)
        #views = class_obj.get_wiki_pageview_score(linkages)
        for j in feat1[i]:
            get_feat = []
            for k in feat1[i][j]:
                get_feat.append(k)
            get_feat.append(summary_sim[j])
            get_feat.append(jaccard_abstract(qstr,j))
            #get_feat.append(views[j])
            #get_feat.append(self.get_wiki_change_views(j))
            get_feat.append(get_title_sim_score(i,j))
            disam_score = disambiguate.predict_score(get_feat)
            print_formatted(get_feat,j,disam_score[0])
            features.append((j,get_feat,disam_score))
            if disam_score>max_score:
                max_score=disam_score
                disamb_entity = j
        disamb_entity = my_diambiguator(max_score,features,disamb_entity)
        ### Pruning unrelated mentions
        print disamb_entity
        if len(disamb_entity[1])>1:
            print candidates[this_candidate][2],candidates[this_candidate][1]
            if candidates[this_candidate][2]<30:
                disamb_entity = ("","RRR")
                print "DELETED",this_candidate
    
    return disamb_entity

pool2 = mp.Pool(processes=nproc)

def parallel_predict(args_list):
    if len(args_list) == 0:
        return []
    #print [(x[0],x[1].keys(),x[2],x[3]) for x in args_list]
    results = [pool2.apply_async(predict_parallel_entities, args=(x[0],x[1],x[2],x[3],)) for x in args_list]
    output = [p.get() for p in results]
    return map(lambda x:(x[0][0],x[1]),zip(args_list,output))

def synchronous_predict(args_list):
    output = []
    for i in args_list:
        output.append((i[0],predict_parallel_entities(i[0],i[1],i[2],i[3])))
    return output

def get_entities_parallel(qstr,train_candidate=None,recent=False,user=None):
    #candidates = mention_detection.predict(qstr,cutoff=.1)
    class_candidates = mention_detection.predict_class(qstr)
    candidates = {}
    train_candidate = []
    for i in class_candidates[:-1]:
        for j in i:
            candidates[j] = i[j]
            train_candidate.append(j)

    train_candidate = class_candidates[0].keys()
    train_candidate += class_candidates[1].keys()
    train_candidate += class_candidates[2].keys()
    train_candidate += class_candidates[3].keys()

    print 'STEP 1',train_candidate,candidates.keys()
    args_list = []

    if user:
        recent_tweets = twitter.get_user_tweets(user,max_count=5)
        for k in recent_tweets:
            try:
                rc = mention_detection.predict_class(k)[0]
                for j in rc:
                    if j not in candidates:
                        print 'ADDED ',j
                        candidates[j] = rc[j]
            except Exception as e:
                print 'EXCEPT',e

    for i in candidates:

        new_candidates = dict(candidates)

        if train_candidate!=None and i not in train_candidate:
            continue

        if recent:
            recent_tweets = twitter.get_tweets(i,max_count=5)
            for k in recent_tweets:
                try:
                    rc = mention_detection.predict_class(k)[0]
                    for j in rc:
                        if j not in new_candidates:
                            print 'ADDED ',j
                            new_candidates[j] = rc[j]
                except Exception as e:
                    print 'EXCEPT',e

        args_list.append((i,new_candidates,qstr,train_candidate))
    return parallel_predict(args_list)
    #return synchronous_predict(args_list)
    
class Predict_Entity():
    def __init__(self):
        #filename = '/home/romil/Desktop/LinkingModel/model_small.pkl'
        filename = './data/clf_linking.pkl'
        with open(filename, 'rb') as fid:                                 
            self.clf = cPickle.load(fid)

    def __destroy__(self):
        pass

    def predict(self,tweet,recent=False,user=None):
        clf = self.clf
        features = get_entities_parallel(tweet.strip(),recent=recent,user=user)
        new_features = []
        for i in range(len(features)):
            if features[i][1][0]!="":
                new_features.append((features[i][0],features[i][1][0]))
        return new_features


#entity = Predict_Entity()

@route('/disamb',method='POST')
def server():
    line = request.forms.get('tweet')
    user = request.forms.get('user')
    recent = request.forms.get('recent')
    if recent==None or recent=='' or recent=='false' or recent=='False':
        recent=False
    elif recent=='true':
        recent = True
    line = line.strip()
    try:
        line = line.encode('utf-8')
    except:
        line = line.decode('utf-8','ignore')
    answer = entity.predict(line,recent=recent,user=user)
    print answer
    return repr(answer)

def evaluate(fil):
    entity = Predict_Entity()
    f = open(fil)
    data = f.readlines()[:5000]
    f.close()
    f1 = open('neel_results_recent.out','a')
    for i in data[:5000]:
        try:
            tweet_text = i.split('\t')[0].strip()
            to_print = tweet_text.strip()
            entities = entity.predict(tweet_text,recent=True)
            for j in entities:
                to_print += '\t'+j[0]+'--'+j[1]
            f1.write(to_print+'\n')
        except:
            #f1.write(tweet_text+'\n')
            f1.write('EXCEPT\n')
        f1.flush()
    f1.close()
    entity.__destroy__()

if __name__ == '__main__':
    #create_data('/home/romil/Desktop/Datasets/Tagme/tagme_formatted.tsv')
    #evaluate('/home/romil/Desktop/Datasets/User/user_formatted.tsv')
    evaluate('/home/romil/Desktop/Datasets/My_mentions/mannual_anno.tsv')
    #evaluate('/home/romil/Desktop/Datasets/Meij/meij_data_formatted.tsv')
    #evaluate('/home/romil/Desktop/Datasets/Tagme/tagme_formatted.tsv')
    #create_data('./data/test_tweet.txt')
    entity = Predict_Entity()
    print entity.predict('So nothing has changed from last night. Timetable for handover of no-fly zone enforcement is still "days" according to WH.')
    # print entity.predict('Apple, Blackberry and Google')
    # for i in open('./data/test'):
    #     print entity.predict(i)
    # print entity.predict('Steve was the formar CEO of Microsoft')
    # print entity.predict('Online crowd can guess what you want to buy or guess.')
    # print entity.predict('Deep learning is fast catching up.')
    # print entity.predict('Apple and Orange are fruits.')
    # print entity.predict('Hats off to ISRO on Mangalyaan.')
    # print entity.predict('Apple was once the best company.')
    # print entity.predict('Apple was once known for its innovation.')
    # print entity.predict('I love Apple.')
    # print entity.predict('ML is a very tough course.')
    # print entity.predict('Sachin is a great musician.')
    # print entity.predict('Go go go goa.')
    # print entity.predict('India is my country.')
    # print entity.predict('Avatar is the best film ever.')
    # print entity.predict('Axe is a greate deodorant company.')
    # print entity.predict('Avatar is the best film ever.',recent=False,user='WDWAvatar')
    # print entity.predict('Netflix and utorrent go hand in hand.')
    # entity.__destroy__()
    #run(host='localhost', port=8089)

