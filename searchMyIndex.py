import bisect
import re

from variables import gcd_sec,gcd_dir

class GCDSearcher:
	def __init__(self): 
		self.f = open(gcd_sec)
		self.f_main = open(gcd_dir)
		self.arr = []
		for i in self.f:
			self.arr.append(i.strip())

	def searcher(self,term):
		term = re.sub('[^a-zA-Z0-9]','',term).lower()
		pointer = bisect.bisect_left(self.arr,term) - 2
		#print term,self.arr[pointer]
		if pointer <= 0:
			pointer = 0
		else:
			pointer = int(self.arr[pointer].split('|')[1])

		self.f_main.seek(pointer)

		counter = 0

		for i in self.f_main:
			counter += 1
			striped = i.split('|')
			word = striped[0].strip()
			#print word
			if word == term:
				ans = []
				for i in range(1,len(striped)-1,2):
					ans.append((striped[i].strip(),float(striped[i+1].strip())))
				return ans
			if counter > 300:
				return []
				
	def destroy(self):
		self.f.close()
		self.f_main.close()


if __name__ == '__main__':
	g = GCDSearcher()
	print g.searcher('st ann')
	print g.searcher('Avatar')
	g.destroy()