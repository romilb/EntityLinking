import math
import numpy as np
import math
import csv
import cPickle
# import pandas
from optparse import OptionParser
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from collections import defaultdict
from copy import deepcopy
from multiprocessing import Pool
from itertools import chain
import time

class Ensemble:
    def __init__(self, rate):
        self.trees = []
        self.rate = rate

    def __len__(self):
        return len(self.trees)

    def add(self, tree):
        self.trees.append(tree)

    def eval_one(self, object):
        return self.eval([object])[0]

    def eval(self, objects):
        results = np.zeros(len(objects))
        for tree in self.trees:
            results += tree.predict(objects) * self.rate
        return results

    def remove(self, number):
        self.trees = self.trees[:-number]


def groupby(score, query):
    result = []
    this_query = None
    this_list = -1
    for s, q in zip(score, query):
        if q != this_query:
            result.append([])
            this_query = q
            this_list += 1
        result[this_list].append(s)
    result = map(np.array, result)
    return result


def compute_point_dcg(arg):
    rel, i = arg
    return (2 ** rel - 1) / math.log(i + 2, 2)


def compute_point_dcg2(arg):
    rel, i = arg
    if i == 0:
        return rel
    else:
        return rel / (math.log(1 + i, 2))
    return


def compute_dcg(array):
    dcg = map(compute_point_dcg, zip(array, range(len(array))))
    return sum(dcg)


def compute_ndcg(page, k=10):
    idcg = compute_dcg(np.sort(page)[::-1][:k])
    dcg = compute_dcg(page[:k])

    if idcg == 0:
        return 1

    return dcg / idcg


def ndcg(prediction, true_score, query, k=10):
    true_pages = groupby(true_score, query)
    pred_pages = groupby(prediction, query)

    total_ndcg = []
    for q in range(len(true_pages)):
        total_ndcg.append(compute_ndcg(true_pages[q][np.argsort(pred_pages[q])[::-1]], k))
    return sum(total_ndcg) / len(total_ndcg)


def query_lambdas(page):
    true_page, pred_page = page
    worst_order = np.argsort(true_page)
    true_page = true_page[worst_order]
    pred_page = pred_page[worst_order]

    page = true_page[np.argsort(pred_page)]
    idcg = compute_dcg(np.sort(page)[::-1])
    position_score = np.zeros((len(true_page), len(true_page)))

    for i in xrange(len(true_page)):
        for j in xrange(len(true_page)):
            position_score[i, j] = compute_point_dcg((page[i], j))

    lambdas = np.zeros(len(true_page))

    for i in xrange(len(true_page)):
        for j in xrange(len(true_page)):
                if page[i] > page[j]:

                    delta_dcg = position_score[i][j] - position_score[i][i]
                    delta_dcg += position_score[j][i] - position_score[j][j]

                    delta_ndcg = abs(delta_dcg / idcg)

                    rho = 1 / (1 + math.exp(page[i] - page[j]))
                    lam = rho * delta_ndcg

                    lambdas[i] -= lam
                    lambdas[j] += lam
    return lambdas


def compute_lambdas(prediction, true_score, query, k=10):
    true_pages = groupby(true_score, query)
    pred_pages = groupby(prediction, query)

    print len(true_pages), "pages"

    pool = Pool()
    lambdas = pool.map(query_lambdas, zip(true_pages, pred_pages))
    return list(chain(*lambdas))


def mart_responces(prediction, true_score):
    return true_score - prediction


def learn(train_file, n_trees=10, learning_rate=0.1, k=10):
    print "Loading train file"
    train = np.array(train_file)
    # train = np.loadtxt(train_file, delimiter=",", skiprows=1)
    # validation = np.loadtxt(validation_file, delimiter=",", skiprows=1)

    scores = train[:, 0]
    # val_scores = train[:, 0]

    queries = train[:, 1]
    # val_queries = validation[:, 1]

    features = train[:, 2:11]
    # val_features = validation[:, 3:]

    ensemble = Ensemble(learning_rate)

    print "Training starts..."
    model_output = np.array([float(0)] * len(features))
    # val_output = np.array([float(0)] * len(validation))

    # print model_output
    # best_validation_score = 0
    time.clock()
    for i in range(n_trees):
        print " Iteration: " + str(i + 1)

        # Compute psedo responces (lambdas)
        # witch act as training label for document
        start = time.clock()
        print "  --generating labels"
        # lambdas = compute_lambdas(model_output, scores, queries, k)
        lambdas = mart_responces(model_output, scores)
        print "  --done", str(time.clock() - start) + "sec"

        # create tree and append it to the model
        print "  --fitting tree"
        start = time.clock()
        tree = DecisionTreeRegressor(max_depth=2)
        #tree = GradientBoostingRegressor(n_estimators=300, random_state=1, verbose=1)
        #tree = LinearRegression()
        # print "Distinct lambdas", set(lambdas)
        tree.fit(features, lambdas)

        print "  ---done", str(time.clock() - start) + "sec"
        print "  --adding tree to ensemble"
        ensemble.add(tree)

        # update model score
        print "  --generating step prediction"
        prediction = tree.predict(features)
        # print "Distinct answers", set(prediction)

        print "  --updating full model output"
        model_output += learning_rate * prediction
        # print set(model_output)

        # train_score
        start = time.clock()
        print "  --scoring on train"
        train_score = ndcg(model_output, scores, queries, 10)
        print "  --iteration train score " + str(train_score) + ", took " + str(time.clock() - start) + "sec to calculate"

    print "Finished sucessfully."
    print "------------------------------------------------"
    return ensemble

def predict_best(queries, results, comment, features):
    query_n = queries[0]
    max_q = (-1,-1000,-1)
    return_arr = []
    for i in zip(queries, results, comment):
        if query_n != i[0]:
            return_arr.append(max_q)
            query_n = i[0]
            max_q = (-1,-1000,-1)
        if max_q[1] < i[1]:
            max_q = i
    return_arr.append(max_q)   
    return return_arr

def predict_fuzzy(queries, results, comment, features):
    cut_off = .1*max(results)
    pass

def my_eval(features):
    w = np.array([100,100,80,50,10,15,20,10])
    #print 'this',features,w,map(lambda x:np.dot(w,x), features)
    #print map(lambda x:np.dot(w,x), features)
    return map(lambda x:np.dot(w,x), features)


def evaluate(model, fn, comment):
    # predict = np.loadtxt(fn, delimiter=",", skiprows=1)
    predict = np.array(fn)
    queries = predict[:, 1]
    #doc_id  = predict[:, 2]
    features = predict[:, 2:]

    #results = model.eval(features)
    results = my_eval(features)
    #writer = csv.writer(open("result.csv",'w'))
    disamb = []
    for line in predict_best(queries, results, comment, features):
            #writer.writerow(line)
            disamb.append(line)
            #print line
    return disamb

def load_file(fn):
    f = open(fn)
    data = f.readlines()
    f.close()
    arr = []
    comment = []
    for i in data:
        comment.append(i[i.find('#'):].strip())
        i = i.split()
        feature = []
        feature.append(int(i[0]))
        for j in i[1:]:
            if j=='#':
                break
            if j[0]=='q':
                feature.append(int(j.split(':')[1]))
            else:
                feature.append(float(j.split(':')[1]))
        if len(feature) > 10:
            feature.pop(-2)
        print feature,comment[-1]
        arr.append(feature)
    return arr,comment


class Disambiguate:
    def __init__(self):
        self.model = None
        with open('./data/lambdamart.model') as fid:
            self.model = cPickle.load(fid)

    def predict_score(self,data):
        qid_data = []
        results = self.model.eval([data])
        #results = my_eval([data])
        return results


def main():
    model = None
    arr,comment = load_file('./data/ltr_mydata.svm')
    model = learn(arr,
                   n_trees=20)
    with open('./data/lambdamart.model','w') as fid:
        cPickle.dump(model,fid)
    with open('./data/lambdamart.model') as fid:
        model = cPickle.load(fid)
    arr,comment = load_file('./data/ltr_test.svm')
    print evaluate(model,arr,comment)



if __name__ == "__main__":
    main()

