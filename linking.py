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

import features_parallel
import tagmerelatedness
import resolve_redirects

from relatedness import Relatedness,get_title_sim_score
#from inmem_graph import get_topic_sim_server,DBPediaCategories
from mongo_cat_graph import DBPediaCategories
from get_summary import Summary
from searchPageviews import PageviewsSearcher
from searchMyIndex import GCDSearcher
from mart import Disambiguate,Ensemble


dbpedia_categories = DBPediaCategories()
disambiguate = Disambiguate()

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

def predict_parallel_entities(this_candidate,candidates,qstr,train_candidate=None):
    print 'YES',this_candidate
    class_obj = entity_linking()
    if train_candidate:
        feat1 = class_obj.get_milne_relatedness_commoness_topics_tweet(candidates,10,train_candidate=train_candidate,this_candidate=this_candidate)
    else:
        feat1 = class_obj.get_milne_relatedness_commoness_topics_tweet(candidates,10,this_candidate=this_candidate)
    print this_candidate,'STEP 2'
    linkages = []
    for i in feat1:
        #print i
        features = []
        linkages = feat1[i].keys()
        summary_sim = class_obj.get_wiki_summary_similarity(qstr.lower().replace(i,''),linkages)
        #views = class_obj.get_wiki_pageview_score(linkages)
        for j in feat1[i]:
            get_feat = []
            for k in feat1[i][j]:
                get_feat.append(k)
            get_feat.append(summary_sim[j])
            get_feat.append(class_obj.jaccard_abstract(qstr,j))
            #get_feat.append(views[j])
            #get_feat.append(self.get_wiki_change_views(j))
            get_feat.append(class_obj.get_title_sim_score(i,j))
            features.append((j,disambiguate.predict_score(get_feat)))
    return features


nproc = 2   # maximum number of simultaneous processes desired
pool1 = mp.Pool(processes=nproc/2)
pool2 = mp.Pool(processes=nproc/2)

def parallel_processing(args_list):
    if len(args_list) == 0:
        return [0,0,0,0]
    results = [pool1.apply_async(find_parallel_relatedness, args=(x[0],x[1],)) for x in args_list]
    output = [p.get() for p in results]
    return sum(output)[:-1]

def parallel_predict(args_list):
    if len(args_list) == 0:
        return None
    print [(x[0],x[1],x[2].keys(),x[3],x[4]) for x in args_list]
    results = [pool2.apply_async(predict_parallel_entities, args=(x[1],x[2],x[3],x[4],)) for x in args_list]
    output = [p.get() for p in results]
    print output
    return output

class entity_linking():

    def __init__(self):
        self.mention_detection = features_parallel.Predict()
        self.summary = Summary()
        #self.pageviews = PageviewsSearcher()
        self.related = Relatedness()
        #self.GCDSearcher= GCDSearcher()

    def __destroy__(self):
        self.pageviews.destroy()
        self.GCDSearcher.destroy()

    def get_milne_relatedness(self,entity1,entity2):
        #tagmerelatedness.py implimentation
        return tagmerelatedness.relatedness(entity1,entity2)

    def jaccard_abstract(self,qstr,wiki_title):
        relatd = self.related.get_abstract_similarity(qstr,wiki_title)
        return relatd

    def get_milne_relatedness_commoness_topics_tweet(self,candidates,threshold=0,train_candidate=None,this_candidate=None):
        votes = {}
        for i in candidates:
            if this_candidate and i!=this_candidate:
                print 'T',this_candidate
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
                args_list = []
                for k in candidates:
                    if i == k:
                        continue
                    if train_candidate == None or i in train_candidate:
                        args_list.append((candidates[k][0],j))
                voteBA,topicBA_1,topicBA_2,topicBA_3=parallel_processing(args_list)
                commoness = j[1]
                #print j,voteBA,topicBA_1,topicBA_2,topicBA_3
                prelims[j[0]] = (voteBA,topicBA_1,topicBA_2,topicBA_3,commoness)
            votes[i] = prelims
        dbpedia_categories.get_parents_recursive('',0,clear=True)
        tagmerelatedness.relatedness('','',clear=True)
        return votes

    def get_topic_sim(self,title1,title2,distance=2):
        return get_topic_sim_server(title1,title2,distance)

    def get_wiki_pageview_score(self,entity_arr):
        normalized_views = self.pageviews.get_normalized_pageview(entity_arr)
        return_dict = {}
        for i in range(len(entity_arr)):
            return_dict[entity_arr[i]] = normalized_views[i]
        return return_dict

    def get_wiki_change_views(self,entity):
        return self.pageviews.get_percent_change(entity)

    def get_user_score():
        pass

    def get_recent_tweets_score():
        pass

    def get_gcd_probability(self,mention,entity): 
        return self.GCDSearcher.searcher('st ann')

    def get_wiki_summary_similarity(self,qstr,entity_arr):
        normalized_sim = self.summary.get_normalized_sim(entity_arr,qstr)
        return_dict = {}
        for i in range(len(entity_arr)):
            return_dict[entity_arr[i]] = normalized_sim[i]
        return return_dict

    def get_candidates(self,qstr):
        candidates = self.mention_detection.predict(qstr)

    def get_features(self,entity,mention,qstr):
        #get relatedness feature
        pass

    def get_title_sim_score(self,mention,entity):
        return get_title_sim_score(mention,entity)

    def coherence(self,votes):
        pass
        return coherence(votes)

    def get_entities_parallel(self,qstr,train_candidate=None):
        candidates = self.mention_detection.predict(qstr)
        print 'STEP 1'
        args_list = []
        for i in candidates:
            args_list.append((self,i,candidates,qstr,train_candidate))
        print parallel_predict(args_list)


    def get_entities(self,qstr,train_candidate=None):
        candidates = self.mention_detection.predict(qstr,cutoff=.1)
        print 'STEP 1'
        if train_candidate:
            feat1 = self.get_milne_relatedness_commoness_topics_tweet(candidates,10,train_candidate=train_candidate)
        else:
            feat1 = self.get_milne_relatedness_commoness_topics_tweet(candidates,10)
        print 'STEP 2'
        features = {}
        linkages = []
        for i in feat1:
            #print i
            features[i] = []
            linkages = feat1[i].keys()
            summary_sim = self.get_wiki_summary_similarity(qstr.lower().replace(i,''),linkages)
            views = self.get_wiki_pageview_score(linkages)
            for j in feat1[i]:
                get_feat = []
                for k in feat1[i][j]:
                    get_feat.append(k)
                get_feat.append(summary_sim[j])
                get_feat.append(self.jaccard_abstract(qstr,j))
                get_feat.append(views[j])
                #get_feat.append(self.get_wiki_change_views(j))
                get_feat.append(self.get_title_sim_score(i,j))
                features[i].append((j,get_feat))
        return features
        #print "Detected Entities in after Phase 1: ",candidates.keys()     

class Predict_Entity():
    def __init__(self):
        #filename = '/home/romil/Desktop/LinkingModel/model_small.pkl'
        filename = './data/clf_linking.pkl'
        with open(filename, 'rb') as fid:                                 
            self.clf = cPickle.load(fid)
        self.el = entity_linking()

    def __destroy__(self):
        self.el.__destroy__()

    def predict(self,tweet):
        clf = self.clf
        features = self.el.get_entities_parallel(tweet.strip())
        print features
        scores = {}
        for i in features:
            #print repr(i),repr(features[i])
            scores[i] = []
            for j in features[i]:
                #print i,j[0],j[1]
                scores[i].append((j[0],clf.predict(j[1])[0]))
            #print i,scores[i]
        return scores

    def get_best_predict(self,tweet):
        results = self.predict(tweet)
        best = {}
        for i in results:
            best_now = -10000
            best_entity = ""
            for j in results[i]:
                if best_now<j[1]:
                    best_now = j[1]
                    best_entity = j[0]
            best[i] = best_entity
        return best

def create_data(fil):
    f = open(fil)
    fff = open('./data/ltr_test.svm','w')
    tweets = f.readlines()
    entity = entity_linking()
    f.close()
    X = []
    y = []
    count = 1
    query = 1
    for i in tweets:
        try:
            # if count <= 2000:
            #    count += 1
            #    continue
            tweet_text = i.split('\t')[0]
            mention_entity = {}
            for j in i.split('\t')[1:]:
                if j.split('--')[1].strip() != 'null':
                    mention_entity[j.split('--')[0].lower()]=j.split('--')[1].strip()
            if '' in mention_entity:
                del mention_entity['']
            features = entity.get_entities(tweet_text,train_candidate=mention_entity.keys())
            print mention_entity.keys(),features.keys()
            for j in features:
                if j not in mention_entity.keys():
                    continue
                print j,[x[0] for x in features[j]]
                flag = True
                to_write = ""
                for k in features[j]:
                    X.append(k[1])
                    #if resolve_redirects.resolve_title(k[0])==resolve_redirects.resolve_ids(mention_entity[j]):
                    if k[0].strip() == resolve_redirects.resolve_ids(mention_entity[j]).strip():
                        y.append(1)
                        flag = True
                    else:
                        y.append(0)
                    to_write += str(y[-1])+' qid:'+str(query)+' '
                    for g in range(len(X[-1])):
                        to_write += str(g+1)+':'+str(X[-1][g]) + ' '
                    to_write = to_write.strip() +' # '+repr(j)+'--'+repr(k[0])+'\n'
                if flag:
                    fff.write(to_write)
                    fff.flush()
                    query += 1
            if count % 10 == 0:
                print y.count(1)
                #with open('./data/X_Linking5.pkl','wb') as fid:
                #    cPickle.dump(X,fid)
                #with open('./data/y_Linking5.pkl','wb') as fid:
                #    cPickle.dump(y,fid)
            print count,tweet_text
            count += 1
        except Exception as e:
            print e
            count += 1
            continue
    # with open('./data/X_Linking5.pkl','wb') as fid:
    #     cPickle.dump(X,fid)
    # with open('./data/y_Linking5.pkl','wb') as fid:
    #     cPickle.dump(y,fid)
    entity.__destroy__()


if __name__ == '__main__':
    #create_data('/home/romil/Desktop/Datasets/Tagme/tagme_formatted.tsv')
    #create_data('/home/romil/Desktop/Datasets/User/user_formatted.tsv')
    #create_data('/home/romil/Desktop/Datasets/My_mentions/mannual_anno.tsv')
    #create_data('./data/test_tweet.txt')
    entity = Predict_Entity()
    #for i in open('./data/test'):
    #    print entity.get_best_predict(i)
    #print entity.get_best_predict('Steve was the formar CEO of Microsoft')
    print entity.get_best_predict('Apple and Orange are fruits.')
    entity.__destroy__()
    #el = entity_linking()
    #print el.get_entities('Steve Jobs, Bill Gates and Apple')
    #print el.get_entities('Absolutely delighted. Two of my politics students have been offered places to read PPE at Oxford. Really chuffed.')
    error
    #get_hashtag_topics('#SafariTrails')
    #qstr = "Its the Abdullah family who enjoys the 'special status' provided to J&K, not the Kashmiri people."
    #qstr = "apple is a fruit"
    #qstr = "india is my country"
    #qstr = "Apple and blackberry are just fruits"
    #qstr = "condos in florida"
    #qstr = "Steve Jobs, Bill Gates and Apple"
    #qstr = "Capricorns are: Mostly compatible with Taurus and Virgo."
    #qstr = "Zodiac Facts As an Aries ,You have drive and ambition to accomplish tasks the other signs might laugh off."
    #qstr = "Cars damaged by rioters at St Ann's  in Nottingham riots"
    #qstr = "iwatch On my Xmas list for this year even if its the only gift I get"
    qstr = "nurses sue douglas kennedy"
    qstr = "Thomas and Mario are strikers playing in Munich."
    qstr = "India is my country"
    qstr = "An apple a day keeps the doctor away."
    for i in open('./data/test'):
        print el.get_entities(i)
    asd
    #qstr = "Wish Twitter had smell-o-tweet technology, these smell gorgeous! #homesandgarden #property #suffolk #flora"
    #qstr = "On my Xmas list for this year even if its the only gift I get #iwatch #apple #applegeek #iluvapple"
    #qstr = "#Apple is a fruit"
    #qstr = "Save your pity party. I don't care. #youdidthistoyourself #karmasabitch"
    #qstr = "KXIP have won the toss and they're bowling, KKR are batting first! Off to #HibernationMode until the innings break. Adios! #ISupportKKR"
    #qstr = "#HBODEFINED #GameOfThrones ''The Lannisters always Pay their debts'' i'll #TakeTheThrone at least the books for now!"
    #qstr = "#Capricorns are: Mostly compatible with #Taurus and #Virgo."
    qstr = "#ZodiacFacts As an #Aries ,You have drive and ambition to accomplish tasks the other signs might laugh off."
    qstr = "Cars damaged by rioters at St Ann's  in #Nottingham #riots http://twitpic.com/63d3hu"
    #print get_entities(qstr)
    segAcc = 0
    totalSeg = 0
    corr = 0
    total = 0
    for i in MakeData().make_psuedo_hashtags():
        #print i
        try:
            overallSplits,overallLinker = get_tweet(i[1])
        except:
            continue
        if overallSplits == i[0]:
            segAcc += 1
        totalSeg += 1
        if len(i[2]) > 0:
            for j in i[2]:
                if j in overallLinker:
                    if i[2][j] == overallLinker[j]:
                        corr += 1
                total += 1
        #print overallLinker,i[2]
    print segAcc,totalSeg
    print corr,total
    #get_hashtag_topics('#GameOfThrones')
