import bisect
import re

from variables import page_sec,page_view,page_old_sec,page_old

class PageviewsSearcher:
	def __init__(self): 
		self.f = open(page_sec)
		self.f_main = open(page_view)
		self.oldf = open(page_old_sec)
		self.oldf_main = open(page_old)
		self.arr = []
		self.oldarr = []
		for i in self.f:
			self.arr.append(i.strip())
		for i in self.oldf:
			self.oldarr.append(i.strip())

	def searcher(self,term,old=False):
		if old:
			arr = self.oldarr
			fil = self.oldf_main
		else:
			arr = self.arr
			fil = self.f_main
		#term = re.sub('[^a-zA-Z0-9]','',term).lower()
		try:
			pointer = bisect.bisect_left(arr,term) - 2
		except:
			return 0
		#print term,self.arr[pointer]
		if pointer <= 0:
			pointer = 0
		else:
			pointer = int(arr[pointer].split(' ')[1])

		fil.seek(pointer)

		counter = 0

		for i in fil:
			counter += 1
			#print i
			#break
			striped = i.split(' ')
			word = striped[1].strip()
			#print word
			if word == term:
				return striped[2].strip()
			if counter > 300:
				return 0

	def get_normalized_pageview(self,terms):
		#print 'terms',terms
		results = []
		for term in terms:
			#print term,self.searcher(term)
			results.append(int(self.searcher(term)))
		summ = sum(results)*1.0
		if summ == 0:
			return results
		results = [i/summ for i in results]
		return results

	def get_change(self,term):
		return int(self.searcher(term)) - int(self.searcher(term,True))

	def get_percent_change(self,term):
		new = int(self.searcher(term)) 
		original = int(self.searcher(term,True))
		if original == 0 and new != 0:
			return new
		elif original == 0:
			return 0
		return (new-original)/(original*1.0)
				
	def destroy(self):
		self.f.close()
		self.f_main.close()
		self.oldf.close()
		self.oldf_main.close()


if __name__ == '__main__':
	g = PageviewsSearcher()
	print g.get_normalized_pageview(['Apple_Inc.','Apple'])
	print g.searcher('Netherlands',True)
	print g.searcher('Netherlands_national_football_team')
	print g.get_normalized_pageview(['Netherlands_national_football_team','Netherlands'])
	print g.get_change('Netherlands'),g.get_percent_change('Netherlands')
	g.destroy()