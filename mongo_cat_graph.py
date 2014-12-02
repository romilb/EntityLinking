#!/usr/bin/env python
# encoding: utf-8
"""
knowledge_graph.py: Provides access to concepts in knowledge
graphs and computes various metrics.

"""

from pymongo import MongoClient
import datetime
import re
import json 
import traceback
from insertMongo import mongo_titles
from variables import mongo_url


'''Memoize function f.'''
def memo(f):
    table = {}
    def fmemo(*args,**kwargs):
        #print args,kwargs
        if 'clear' in kwargs:
            table.clear()
            #print 'MEM1 CLEARED'
        if args[1:] not in table:
            table[args[1:]] = f(*args,**kwargs)
        return table[args[1:]]
    fmemo.memo = table
    return fmemo

def memo2(f):
    table2 = {}
    def fmemo(*args,**kwargs):
        #print args,kwargs
        if 'clear' in kwargs:
            table2.clear()
            #print 'MEM2 CLEARED'
        if args[1:] not in table2:
            table2[args[1:]] = f(*args,**kwargs)
        return table2[args[1:]]
    fmemo.memo = table2
    return fmemo

class DBPediaCategories(object):
    
    def __init__(self):
        self.clients = MongoClient(mongo_url, 27017)
        self.db = self.clients.wikiCategories
        self.parent = self.db.parents
        self.child = self.db.children
        self.mon = mongo_titles()

    @memo2
    def outdegree(self,category,clear=False):
        if category=='' and clear==True:
            return -1
        t=self.parent.find({'page':category}).count()
        t1 = self.mon.out_degree(category)
        if t ==0 and t1 == 0:
            return 1000000
        else:
            return max(t,t1)
            
    def get_neighbors(self, category, distance=1):
        if distance == 0:
            return []
        else:
            neighbors = self.get_parents(category) + self.get_children(category)
            for neighbor in neighbors:
                neighbors = neighbors + self.get_neighbors(neighbor,distance=distance-1)
            return list(set(neighbors))

    def get_entity_parent(self,category):
        neighbors1 = self.mon.find({"title":category.strip()})
        if neighbors1 != None:
            neighbors1 = neighbors1['cat']
        else:
            neighbors1 = []
        neighbors2 = self.parent.find_one({"page":category.strip()})
        if neighbors2 != None:
            neighbors2 = neighbors2['link']
        else:
            neighbors2 = []
        neighbors = list(set(neighbors1 + neighbors2))
        if u'' in neighbors:
            neighbors.remove(u'')
        return neighbors

    def get_parents(self, category, distance=1):
        """Returns a list of neighbors for a given category"""
        if distance == 0:
            return []
        neighbors = self.get_entity_parent(category)
        #print "Q",neighbors
        next_neighbors = []
        overall_neighbors = set(neighbors)
        for iteration in range(distance):
            #print iteration
            for i in neighbors:
                next_neighbors += self.get_entity_parent(i)
            #print "H",i,next_neighbors
            next_neighbors = set(next_neighbors)
            if next_neighbors is not None and len(next_neighbors)>0:
                overall_neighbors = overall_neighbors | next_neighbors
            neighbors = set(next_neighbors)
            next_neighbors = []

        return list(overall_neighbors)

    @memo
    def get_parents_recursive(self, category, distance, clear = False):
        if category == '' and clear==True:
            self.outdegree(category,clear=True)
            return set([])
        if distance == 0:
            return set([])
        neighbors = self.get_entity_parent(category)
        next_neighbors = set([])
        overall_neighbors = set(neighbors)
        for i in overall_neighbors:
            next_neighbors = next_neighbors | self.get_parents_recursive(i,distance-1)
        return overall_neighbors | next_neighbors

    def get_children(self, category, distance = 1):
        try:
            if distance == 0 or category == "" or category == None:
                return []
            else:
                childern1 = self.child.find_one(category.strip())
                if childern1 != None:
                    childern1 = childern1['link']
                else:
                    childern1 = []
                childern2 = self.mon.get_children(category.strip())
                if childern2 != None:
                    pass
                else:
                    childern2 = []
                childern = list(set(childern1 + childern2))
                for child in childern:
                    childern = childern + self.get_children(child,distance-1)
            return list(set(childern2))
        except:
            #traceback.print_exc()
            return []

    def get_topic_sim(self,entity1,entity2,distance=1):
        ca1 = self.get_parents_recursive(entity1,distance)
        ca2 = self.get_parents_recursive(entity2,distance)
        score = 0
        den = 0.00001
        intersection = ca1 & ca2
        union = ca1 | ca2
        #print 'length',len(intersection),len(union)
        for i in union:
            weight = 1.0/self.outdegree(i)
            den += weight
            if i in intersection:
                score += weight
        return score/den
    
def usage_example():
    # Running the script
    dbpedia_categories = DBPediaCategories()
    #print len(dbpedia_categories.get_parents('Orange_(fruit)',distance=2))
    #print len(dbpedia_categories.get_parents_recursive('Orange_(fruit)',3))
    #print dbpedia_categories.get_children('Category:Rape')
    #print dbpedia_categories.get_topic_sim("Apple","Orange_(fruit)",3)
    print dbpedia_categories.get_topic_sim("Apple_Inc.","Steve_Jobs",3)
    #print dbpedia_categories.get_topic_sim("Apple_Inc.","IPad",2)
    #print dbpedia_categories.get_topic_sim("Apple_Inc.","Nokia",2)
    #print dbpedia_categories.get_topic_sim("Pineapple","Orange_(fruit)",2)
    #print len(dbpedia_categories.get_children('Category:Rape'))
                          
if __name__ == '__main__':
    usage_example()
