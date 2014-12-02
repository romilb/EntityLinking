from pymongo import MongoClient
import datetime
import re
import json 
import traceback
from insertMongo import mongo_titles
from variables import mongo_url


class Summary(object):
    
    def __init__(self):
        self.clients = MongoClient(mongo_url, 27017)
        self.db = self.clients.wikipedia
        self.summary = self.db.summary

    def clean_tweet_words(self,tweet):
        words = re.split(r'[\n ,.?!:"\'-]', tweet.lower())
        if '' in words:
            words.remove('')
        return words

    def get_summary(self,title,scores=False):
        title = title.replace('_',' ')
        summary = self.summary.find_one({"title":title.strip()})
        if summary!=None:
            only_words = []
            words = summary["summary"]
            if scores:
                return words
            for i in words:
                only_words.append(i[0])
            return only_words
        else:
            return []

    def get_sim(self,title,tweet):
        words = self.clean_tweet_words(tweet)
        sim = 0
        summary = self.get_summary(title,True)
        #print summary
        if len(summary)>0:
            max_scr = summary[0][1]
        for i in summary:
            if i[0] in words:
                sim += words.count(i[0])*i[1]/max_scr
        return sim

    def get_jaccard(self,title,tweet):
        pass

    def get_normalized_sim(self,titles,tweet):
        sims = []
        for title in titles:
            sims.append(self.get_sim(title,tweet))
        summ = sum(sims) * 1.0
        if summ == 0.0:
            return sims
        sims = [i/summ for i in sims]
        return sims

def usage_example():
    summary = Summary()
    #print summary.get_summary('Shahrukh_Khan')
    #print summary.get_summary('Life_of_Pi')
    #print summary.get_summary('Life_of_Pi_(film)',False)
    #print summary.get_summary('Blackberry')
    #print summary.get_normalized_sim(['A_Game_of_Thrones','Game_of_Thrones'],'will be released on book stores tomorrow.')
    print summary.get_sim('Apple',', Blackberry and Google')
    #print summary.get_sim('Life_of_Pi_(film)','Pi got struct with a tiger on a boat')
    print summary.get_normalized_sim(['Life_of_Pi_(film)','Life_of_Pi','Life_of_Pi_(novel)',
        'Shahrukh_Khan','Take_Off_(film)'],'Pi got struct with a tiger on a boat')
    print summary.get_normalized_sim(['central_processing_unit', 
        'Communist_Party_of_Ukraine', u'List_of_Intel_microprocessors', 'CPU_(disambiguation)', 
        u'System_on_a_chip', 'Microprocessor', 'Central_processing_unit',
     'Commonwealth_Press_Union', 'Non-player_character', 'Central_Philippine_University'],'RT @PaulBegala: Santorum spoke from his heart.  Not to be outdone, Mitt is speaking from his CPU.')
    #print summary.get_summary('Take_Off_(film)')
                          
if __name__ == '__main__':
    usage_example()