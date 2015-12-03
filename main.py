import random
import unittest
import string
import copy
import os
from bs4 import BeautifulSoup
import urllib2
import mechanize
import pypdfocr
import sys
import subprocess
import pdfminer


#### #### #### #### #### #### #### #### #### #### #### #### #### ####

class Catalog(object):
    ''' The Catalog class consists of a collection (dictionary), a
    rootURL to pull information from, and a totalNumBooks.
    
    The collection will have key-value pairs where the key is a
    four digit integer (book identification number) associated
    with the book's web page on e-booksdirectory.com and where
    the value is another dictionary. The totalNumBooks acts as
    a size cap so we can limit the size of our collection during
    testing. The collection dictionary takes the following form:
        collection[book] = {\
            'title':'Jurassic Park', \
            'author':'Michael Crichton', \
            'downloadLinks':['http://www.google.com']}
    '''
    def __init__(self):
        self.collection = {}
        self.rootURL = \
            'http://www.e-booksdirectory.com/mathematics-all.html'
        self.totalNumBooks = -1
        self.badPDFkeyList = [6146]
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def build_catalog(self, mode="offline"):
        '''
        The build_catalog, depending on the mode, will either build
        self.collection from a file with lines of the form
            book, title, author, ..., downloadLinks, \n
        or if mode!="offline", this function will pull the catalog 
        self.collection information rom the web. Pulling from the 
        web is slow, so we prefer to pull from a local copy if we can.
        '''
        print "\n\n Building catalog."
        filename = "primary.dat"
        self.collection = {}

        if mode != "offline":
            print "Performing initial pull..."            
            self.initial_pull()
            #del self.collection[6146]
            print "Writing data to file..."
            self.write_data_to_file(filename)
        elif os.path.isfile(filename):
            self.build_catalog_from_file()
            #del self.collection[6146]
        else:
            print "Error in build_catalog! You specified to not pull from the web, but there is no local copy."
        pass
            
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def initial_pull(self):
        '''
        Entry function for web pulling. Use BeautifulSoup to parse
        html information at the rootURL to populate self.collection
        by using write_entry_to_catalog (which gets everything like
        author, title, year of publication, publisher) and by using
        pull_download_links (which retrieves links under 'Download
        Links' on the book webpage).
        '''
        print "\n\n Starting initial pull..."
        self.collection={}
        page = BeautifulSoup(urllib2.urlopen(self.rootURL), \
            'html.parser')
        entries = page.find_all('p')
        
        count = 0
        
        for entry in entries:
            if count < self.totalNumBooks or self.totalNumBooks < 0:
                count += 1
                #print "Writing entry to catalog..."
                book, url = self.write_entry_to_catalog(entry)
                if book not in self.badPDFkeyList:
                    print "Getting download links for book ", book
                    self.pull_download_links(book) #,'http://www.e-booksdirectory.com/' + url)
                else:
                    temp_d = dict(self.collection)
                    del temp_d[book]
                    self.collection = dict(temp_d)
            else:
                break
        pass

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def write_entry_to_catalog(self, entry, mode="url"):
        '''
        This function takes an entry from the html of the main page
        and extracts book key, title, author, book page url, year
        of publication, and publisher, and throws it into the
        self.collection dictionary.
        '''
        result = []
        if mode=="url":
            url = entry.find('a')['href']
            book = int(url[url.index('=')+1:])
            self.collection[book] = {}

            tempTitle = (entry.find('strong').text).encode('utf-8')
            tempTitle = (tempTitle.translate(None, \
                string.punctuation)).lower()
            tempTitle = (tempTitle.lstrip()).rstrip()
            self.collection[book]['title'] = tempTitle
            
            # Get the author and publisher
            author_pub = entry.contents[4].split(' | ')
            
            tempAuthor = author_pub[0].strip().encode('utf8')
            tempAuthor = tempAuthor.replace(","," and ")
            tempAuthor = (tempAuthor.translate(None, \
                string.punctuation)).lower()
            tempAuthor = (tempAuthor.lstrip()).rstrip()
            self.collection[book]['author'] = tempAuthor
             
            tempPub = author_pub[1].strip().encode('utf8')
            tempPub = tempPub.replace(","," and ")
            tempPub = (tempPub.translate(None, \
                string.punctuation)).lower()
            tempPub = (tempPub.lstrip()).rstrip()
            self.collection[book]['publisher'] = tempPub
            
            # Get the year
            tempYear = (entry.contents[6].split( \
                ', ')[0][-4:]).encode('utf8')
            tempYear = (tempYear.translate(None, \
                string.punctuation)).lower()
            tempYear = (tempYear.lstrip()).rstrip()
            if any(char.isdigit() for char in tempYear):
                self.collection[book]['year'] = tempYear
            else:
                self.collection[book]['year'] = str(0)
            # Lastly, a list of download links.
    
            self.collection[book]['downloadLinks'] = []
            result = [book, url]
        else:
            # If mode != "url" then entry = [book_number, \
            #    book_url, book_dict]
            book = entry[0]
            url = entry[1]
            for item in entry[2]:
                self.collection[book][item] = copy.deepcopy(\
                    entry[1][item])
            result = [book, url]
        return result

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def pull_download_links(self, book):
        ''' 
        This function takes a look at a book's web page and extracts
        all of the <a href> tags from the 'Download Links' section
        and puts them into a big array. We store that into the
        self.collection[book] dictionary with key 'downloadLinks'
        '''
        url = "http://www.e-booksdirectory.com/details.php?ebook=" + \
            str(book)

        try:
            bookPage = BeautifulSoup(urllib2.urlopen(url), \
                'html.parser')
            divisions = bookPage.find_all("div")
            if divisions:
                for div in divisions:
                    if 'class' in div.attrs:
                        if div.attrs['class'][0]=="lftdownload":
                            toAdd = div.find_all('a')
                            self.collection[book]['downloadLinks'] = \
                                [ x.get('href').encode('utf8') for \
                                x in toAdd]
        except:
            print "Error: urlopen error for book ", book

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def write_data_to_file(self, filename):
        '''
        This one is simple: take self.collection and dump into a file.
        '''
        try:
            f = open(filename, "w")
        except IOError:
            filename = filename[:-4] + "_temp" + filename[-4:]
            f = open(filename, "w")
        for book in self.collection:
            f.write(str(book)) 
            f.write(", " + self.collection[book]['title'])
            f.write(", " + self.collection[book]['author'])
            f.write(", " + self.collection[book]['publisher'])
            f.write(", " + self.collection[book]['year'])
            linkString = ""
            if len(self.collection[book]['downloadLinks']) > 0:
                for link in self.collection[book]['downloadLinks']:
                    linkString += ", " + link
            linkString += " \n"
            f.write(linkString)
        f.close()
        pass

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def build_catalog_from_file(self):
        ''' Take the dump file from previous function and reconstruct
        self.collection '''
        if os.path.isfile("primary.dat"):
            tempFile = open("primary.dat", "r")
            f = tempFile.readlines()
            tempFile.close()
            self.collection = {}

            if self.totalNumBooks < 0:
                for line in f:
                    line = line.replace("\n","")
                    line = line.split(",")
                    if len(line)> 4:
                        key = int(line[0])
                        self.collection[key] = {}
                        self.collection[key]['title'] = (str(\
                            line[1]).lstrip()).rstrip()
                        self.collection[key]['author'] = (str(\
                            line[2]).lstrip()).rstrip()
                        self.collection[key]['publisher'] = (str(\
                            line[3]).lstrip()).rstrip()
                        self.collection[key]['year'] = (str( \
                            line[4]).lstrip()).rstrip()
                        self.collection[key]['downloadLinks'] = []
                        if len(line) > 5:
                            for item in line[5:]:
                                item = (item.lstrip()).rstrip()
                                #print "<item ", item, " end item>"
                                if item:
                                    self.collection[key][ \
                                        'downloadLinks'].append(item)
                    else:
                        print "Found dangling line!", line
            else:
                count = self.totalNumBooks            
                for line in f:
                    if count > 0:
                        line = line.replace("\n","")
                        line = line.split(",")
                        if len(line) > 4:
                            count -= 1
                            key = int(line[0])
                            self.collection[key] = {}
                            self.collection[key]['title'] = (str(\
                                line[1]).lstrip()).rstrip()
                            self.collection[key]['author'] = (str(\
                                line[2]).lstrip()).rstrip()
                            self.collection[key]['publisher'] = (str(\
                                line[3]).lstrip()).rstrip()
                            self.collection[key]['year'] = (str( \
                                line[4]).lstrip()).rstrip()
                            self.collection[key]['downloadLinks'] = []
                            if len(line) > 5:
                                for item in line[5:]:
                                    item = (item.lstrip()).rstrip()
                                    #print "<item ", item, " end item>"
                                    if item:
                                        self.collection[key][ \
                                            'downloadLinks'].append(item)
                        else:
                            print "Found dangling line!", line
                    else:
                        break
        else:
            print "Error: no collection.dat file found! Pulling from the web instead. \n"
            self.initial_pull()
            self.write_data_to_file(filename)
        pass
         
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

class TestCatalog(unittest.TestCase):
    ''' Test Class for testing Catalog class.'''
    def test_build_catalog(self):
        print "Testing build_catalog"
        c = Catalog()
        c.build_catalog()

        ground_truth = {'publisher': 'san francisco state university', \
            'author': 'matthias beck and  gerald marchesi and  dennis pixton', \
            'year': '2007', 'downloadLinks': [\
            'http://math.sfsu.edu/beck/complex.html', \
            'http://math.sfsu.edu/beck/complex.html'], 'title': \
            'a first course in complex analysis'}
        test_entry = c.collection[250]

        #print "\n\n Printing the ground_truth : \n\n"
        #print ground_truth
        #print "\n\n Printing test_entry (should be same) : \n\n"
        #print test_entry
        x = abs(cmp(ground_truth, test_entry))
        self.assertEqual(x,0)

        print "Pulling data from web..."
        c.build_catalog(mode="web")
        test_entry = c.collection[250]
        y = abs(cmp(ground_truth, test_entry))

        self.assertEqual(y, 0)

    
    def test_initial_pull(self):
        print "Testing initial_pull"
        c = Catalog()
        c.build_catalog()
        c.initial_pull()
        ground_truth = {'publisher': 'project gutenberg', \
            'author': 'wallace c boyden', 'year': '2004', \
            'downloadLinks': ['http://www.gutenberg.org/ebooks/13309',\
            'http://www.gutenberg.org/ebooks/13309'],
            'title': 'a first book in algebra'}
        test_entry = c.collection[4697]
        value = cmp(ground_truth,test_entry)
        self.assertEqual(value,0)

    def test_write_entry_to_catalog(self):
        print "Testing write_entry_to_catalog"
        html = "<p>4.<br /><a href=\"details.php?ebook=61\"><strong>A Computational Introduction to Number Theory and Algebra</strong></a><br />Victor Shoup | Cambridge University Press<br />Published in 2005, 534 pages</p>"

        c = Catalog()
        page = BeautifulSoup(html, 'html.parser')
        entries = page.find_all('p')
        for entry in entries:
            c.write_entry_to_catalog(entry)
        ground_truth = {61: \
            {'publisher': 'cambridge university press', \
            'author': 'victor shoup', 'year': '2005', \
            'downloadLinks': [], \
            'title': 'a computational introduction to number theory and algebra'}}
        value = cmp(ground_truth, c.collection)
        self.assertEqual(value,0)

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def test_pull_download_links(self):
        print "Testing pull_download_links"
        c = Catalog()
        c.build_catalog()
        c.pull_download_links(1853)
        ground_truth = ['http://www.math.vt.edu/people/day/ProofsBook/', \
            'http://www.math.vt.edu/people/day/ProofsBook/IPaMV.pdf']
        self.assertEqual(c.collection[1853]['downloadLinks'], \
            ground_truth)
        #print c.collection[1853]
        #pass
    
    def test_write_data_to_file(self):
        print "Testing write_data_to_file"
        c = Catalog()
        c.build_catalog()
        filename = "test_data.dat"
        c.write_data_to_file(filename)
        self.assertTrue(os.path.isfile(filename))
        
    def test_build_catalog_from_file(self):
        print "Testing build_catalog_from_file"
        c = Catalog()
        c.build_catalog()
        url_correct = abs(cmp(c.rootURL, \
            'http://www.e-booksdirectory.com/mathematics-all.html'))
        total_num_books_correct = abs(cmp(c.totalNumBooks, 40))
        correct = url_correct + total_num_books_correct
        self.assertTrue(correct==0)
        test_entry = c.collection[106]
        #print "\n\n Printing test_entry in test_build_catalog_from_file \n\n", test_entry
        ground_truth = {\
            'publisher': 'university of puget sound', \
            'author': 'robert a beezer', \
            'year': '2010', \
            'downloadLinks': ['http://linear.ups.edu/index.html', \
            'http://linear.ups.edu/download.html'], 'title': 'a first course in linear algebra'}
        #print "\n\n Printing ground_truth in test_build_catalog_from_file \n\n", ground_truth
        #print "\n\n Printing comparison, cmp(*,*) = ", cmp(test_entry, ground_truth)
        test_value = cmp(test_entry, ground_truth)
        self.assertEqual(test_value,0)
    
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

class BookDataPoint(object):
    ''' BookDataPoint class is a simple object. We have two
        dictionaries, one self.data and one self.hist. We will take
        book information like author, title, etc, place it into self.data
        and we will take a histogram of word frequency and store it into
        self.hist
    '''
    def __init__(self):
        self.data = {}
        self.hist = {}
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
        
    def assign_data(self, sentence, bookData):
        ''' 
        This function takes in a string, sentence, and an object,
        bookData. The name of the variable sentence is a bit of a
        misnomer, for this string represents the whole of the book 
        text.  
        
        This function stores bookdata into self.data and constructs
        a relative word frequency histogram to store in self.hist of
        the form
            {word:frequency}
        where word is a string ("hello") and frequency is a float
        (0.001284).
        '''
        sentence = (sentence.translate(None,\
            string.punctuation)).lower()
        sentence = sentence.split()
        if len(sentence) > 0:
            self.data = bookData
            for word in sentence:
                if word in self.hist.keys():
                    self.hist[word] += 1.0
                else:
                    self.hist[word] = 1.0
            for word in self.hist:
                self.hist[word] = float( \
                    float(self.hist[word])/float(len(sentence)))
        else:
            print "Error in BookDataPoint: tried to assign book data to empty sentence."
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

class TestBookDataPoint(unittest.TestCase):
    ''' This lass tests the BookDataPoint class. '''
    def test_assign_data(self):
        print "Testing BookDataPoint's assign_data function"
        sentence = "Jane sees Dick run. Run, Dick, run! Dick sees Jane play with Spot. Play, Jane, play!"
        title = "A magnum opus by Brandon Goodell."
        data_point = BookDataPoint()
        data_point.assign_data(sentence, title)
        one = float(float(1)/float(16))
        two = float(float(2)/float(16))
        three = float(float(3)/float(16))
        testhist = {"jane":copy.deepcopy(three), \
            "sees":copy.deepcopy(two), "dick":copy.deepcopy(three), \
            "run":copy.deepcopy(three), "play":copy.deepcopy(three), \
            "with":copy.deepcopy(one), "spot":copy.deepcopy(one)}
        
        self.assertEqual(data_point.data, \
            "A magnum opus by Brandon Goodell.")
        self.assertEqual(data_point.hist, testhist)

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

class WordSpace(object):
    ''' The WordSpace object does several things.
    This represents the ambient euclidean space in which all texts
    have been measured: each new word is a new dimension. 
    
    This class has variable self.space, which is a dictionary
    of values unique strings/words and with keys the same word.
    This class has variable self.observations, which is a dictionary
    whose keys are BookDataPoint.data and whose values are
    BookDataPoints. This class has two similar variables
    self.initial_roots and self.new_initial_roots: these are 
    both dictionaries, and they store sets of points from
    our WordSpace (high dimensional euclidean space) which are 
    disguised as BookDataPoints (although they don't correspond to
    books).
    
    This class has a function, add_observation, that is used 
    to add a BookDataPoint to self.observations, and to update
    self.space with new unseen words. This class also has the
    functions distance_metric_ell_one* to compute the ell_one
    norm between two texts.
    
    This class can generate initial roots by randomly generating
    sentences from it's ambient WordSpace, and this class can
    use initial_roots to find clusters within self.observations 
    with cluster_observations. To do so, it has to compute means
    with find_mean and find_cluster_means, it has to reset
    roots with set_roots_to_means, it has to associate a root
    with a BookdataPoint with ass_root_to_point, and it has to
    compare whether two clusterings are equivalent with both
    check_cluster_in_clustering and check_equiv_clsuterings
    '''
    def __init__(self):
        self.space = {}
        self.observations = {}
        self.initial_roots = {}
        self.new_initial_roots = {}
        self.space_filename = "word_space_space.txt"
        self.obs_filename = "word_space_observations.txt"

    def write_word_space_to_file(self):
        if os.path.isfile(self.space_filename):
            os.remove(self.space_filename)
        f = open(self.space_filename,"w")
        for word in self.space:
            f.write(str(word) + "\n")
        f.close()
        
        if os.path.isfile(self.obs_filename):
            os.remove(self.obs_filename)
        f = open(self.obs_filename,"w")
        for obs in self.observations:
            line = str(obs) + ";{"
            for word in self.observations[obs].hist:
                line += str(word) + ":" + str(self.observations[obs].hist[word]) + ", "
            line += "}\n"
        f.close()

    def build_word_space_from_file(self):
        result = False
        if os.path.isfile(self.space_filename) and os.path.isfile(\
            self.obs_filename):
            self.space = {}
            self.observations = {}

            f = open(self.space_filename, "r")
            lines = f.readlines()
            f.close()
            for line in lines:
                line = (line.translate(None, string.punctuation)).lower()
                line = line.split()
                self.found_word(line[0])
            
            f = open(self.obs_filename, "r")
            lines = f.readlines()
            f.close()
            for line in lines:
                line = line.split(";")
                obs_data = line[0]
                obs_hist = line[1]
                obs_hist = obs_hist[1:-1]
                obs_hist = obs_hist.split(",")
                thishist = dict()
                for entry in obs_hist:
                    entry = entry.split(":")
                    word = entry[0]
                    frequency = entry[1]
                    thishist.update({word:frequency})
                book = BookDataPoint()
                book.data = obs_data
                book.histogram = copy.deepcopy(thishist)
                self.add_observation(book)
            result = True

        return result
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
        
    def found_word(self, word):
        ''' Ping this for every word we see. '''
        if word not in self.space.keys():
            self.space[word] = str(word)
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
            
    def get_random_sentence(self, sentence_length=7):
        ''' Generates a random sentence from the wordspace with lenth
        sentence_length. '''
        sentence = []
        for i in range(sentence_length):
            randomKey = random.choice(list(self.space.keys()))
            sentence.append(copy.deepcopy(self.space[randomKey]))
        return sentence
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
    
    def add_observation(self, data_point):
        ''' Take BookDataPoint as input and include it into the
        self.observations dictioanry with key BookDataPoint.data
        and, for each word in the text, call found_word
        '''
        if data_point.data not in self.observations.keys():
            self.observations[data_point.data] = data_point
            for word in data_point.hist:
                self.found_word(word)
        else:
            pass
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def distance_metric_ell_one_keys(self, key1, key2):
        ''' One of several ell_one distance metrics: given
        keys in the observation dictionary, compute the distance
        between two observations'''
        for word in self.observations[key1].hist:
            if word not in self.observations[key2].hist:
                self.observations[key2].hist[word] = 0.0
        for word in self.observations[key2].hist:
            if word not in self.observations[key1].hist:
                self.observations[key1].hist[word] = 0.0
        sum = 0.0
        for word in self.observations[key1].hist:
            sum += abs(self.observations[key1].hist[word] - self.observations[key2].hist[word])
        return sum
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
        
    def distance_metric_ell_one_histos(self, hist1, hist2):
        ''' One of several ell_one distance metrics: given
        two histograms in the WordSpace, compute the distance
        between the two histograms. These need not be observations.
        '''
        for word in hist1:
            if word not in hist2.keys():
                hist2[word] = 0.
        for word in hist2:
            if word not in hist1.keys():
                hist1[word] = 0.
        sum = 0.0
        for word in hist1:
            sum += abs(hist1[word] - hist2[word])
        return sum
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def distance_metric_ell_one(self, book_data_point1, \
        book_data_point2):
        ''' One of several ell_one distance metrics: given
        two BookDataPoints, compute the distance between them. They
        need not be included in our ambient WordSpace (although we
        should probably include them!)
        '''
        for word in book_data_point1.hist:
            if word not in book_data_point2.hist.keys():
                book_data_point2.hist[word] = 0.0
        for word in book_data_point2.hist:
            if word not in book_data_point1.hist.keys():
                book_data_point1.hist[word] = 0.0
        sum = 0.0
        for word in book_data_point1.hist:
            sum += abs(book_data_point1.hist[word] - \
                book_data_point2.hist[word])
        return sum
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
        
    def generate_initial_roots(self, number_roots=5):
        '''
        Pick initial cluster centers.
        '''
        self.initial_roots = {}
        for i in range(number_roots):
            randomKey = random.choice(list(self.observations.keys()))
            self.initial_roots[randomKey] = self.observations[randomKey]
        #if not self.initial_roots:
        #    self.initial_roots = {}
        #    for i in range(number_roots):
        #        title = "root " + str(i)
        #        random_sentence = " ".join(self.get_random_sentence( \
        #            sentence_length=7))
        #        
        #        data_point = BookDataPoint()
        #        data_point.assign_data(random_sentence, title)
        #        
        #        self.initial_roots[title] = data_point
        pass
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
    
    def find_mean(self, cluster):
        '''
        Given a cluster of the form
            cluster = { 'key' : BookDataPoint }
        find the average BookDataPoint
        '''
        mean = {}
        for key in cluster:
            for word in cluster[key].hist:
                if word in mean.keys():
                    mean[word] += cluster[key].hist[word]
                else:
                    mean[word] = cluster[key].hist[word]
        for word in mean:
            mean[word] = float(mean[word])/float(len(cluster))
        return mean
                
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def ass_root_to_point(self, data_point):
        ''' 
        Arguments: data_point is a BookDataPoint object.
        This function looks through self.initial_roots for the 
        BookDataPoint entry that is closest in the ell_one metric 
        to the data_point, and returns the associated root.
        '''
        result = None
        minDist = -1.0
        for root in self.initial_roots:
            thisDist = self.distance_metric_ell_one( \
                self.initial_roots[root], data_point)
            if minDist < 0 or thisDist < minDist:
                result = root
                minDist = thisDist
        return result
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
    
    def cluster_observations(self, number_clusters):
        '''
        Looks through self.observations and assigns a color (root)
        from self.initial_roots to each. Constructs a dictionary whose
        keys are the roots, and whose values are themselves dictionaries.
        These dictionaries are filled with all of the books colored by 
        the associated root, the keys are the BookDataPoints.data, 
        like 'title', and the values are the BookDataPoints themselves.
        
        That is, we end up with a dictionary of dictionaries in form
            {root_one: {book_data_one: BookDataPoint_one, ..., }, ...}
        where root_one from initial_roots may be interpreted as the
        color of the BookDataPoints in the value.
        '''
        result = {}
        print "We have ", len(self.observations), " observations to work with..."

        for obs in self.observations:
            key = self.observations[obs].data
            hist = self.observations[obs].hist
            print "Finding root for point ", obs, self.observations[obs]
            root = self.ass_root_to_point(self.observations[obs])

            if root:
                print "Found root for point. Adding to result dictionary."
                if root not in result:
                    result[root] = {self.observations[obs].data : self.observations[obs]}
                else:
                    result[root][self.observations[obs].data]= self.observations[obs]
            else:
                print "Error finding nearest root in cluster_observations with book ", obs
            #result[root][self.observations[obs].data] = self.observations[obs]
        print result
            
        return result
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def find_clustering_means(self, clustering):
        '''
        Given a clustering (the result of cluster_observations),
        we wish to assign the geometric mean of the separate clusters
        to the self.new_initial_roots object.
        '''
        for cluster in clustering:
            self.new_initial_roots[cluster] = self.find_mean( \
                clustering[cluster])
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def check_cluster_in_clustering(self, cluster, clustering):
        ''' 
        Given a dictionary, cluster, of BookDataPoints and a 
        clustering (the result of cluster_observations), check if
        cluster is one of the values of clustering.
        '''
        found = False
        for compare_cluster in clustering:
            if cmp(cluster, clustering[compare_cluster]) == 0:
                found = True
                break
        return found
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
        
    def check_equivalent_clusterings(self, clustering_one, clustering_two):
        '''
        Check if two clusterings (the result of cluster_observations)
        are equivalent by double containment. For each cluster in 
        clustering_one, we check if cluster is in clustering_two by 
        using check_cluster_in_clustering and vice versa.
        '''
        same = True
        for cluster in clustering_one:
            if not self.check_cluster_in_clustering(\
                clustering_one[cluster], clustering_two):
                same = False
                break
        for cluster in clustering_two:
            if not self.check_cluster_in_clustering(\
                clustering_two[cluster], clustering_one):
                same = False
                break
        return same
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def set_roots_to_means(self):
        '''
        sets self.initial_roots to the new_initial_roots
        '''
        self.initial_roots = copy.deepcopy(self.new_initial_roots)
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def report_clustering(self, clustering=None):
        '''
        Fancy print function: print book keys by cluster, so we can
        kind of what clusters we ended up with. Here, we cluster
        with initial_roots if clustering=None, or we simply
        print the clustering scheme passed in otherwise.
        '''
        print "\n\n Printing clustering \n\n"
        number_clusters = len(self.initial_roots)
        clustering = self.cluster_observations(number_clusters)

        if clustering==None:
            print "Error, null clustering"
        else:
            print clustering
            for key in clustering:
                print key
                for book in clustering[key]:
                    print " "*5 + book
        pass

#### #### #### #### #### #### #### #### #### #### #### #### #### ####    

class TestWordSpace(unittest.TestCase):
    ''' This class tests the WordSpace class. '''
    def test_report_clustering(self):
        print "Testing report_clustering in WordSpace"
        ws = WordSpace()
        sentences = ["Jane says hello to Spot.", \
            "Dick says hello to Spot. Hello, Spot, Hello", \
            "Jane asks Dick where Spot has gotten to. Ask, Jane, ask.", 
            "Jane and Dick are confused about Spot."]
        root_sents = ["Dick Jane Spot", "says asks gotten are", \
            "to hello where has and confused about"]
        for s in sentences:
            book = BookDataPoint()
            book.assign_data(s, s)
            ws.add_observation(book)
        for s in root_sents:
            book = BookDataPoint()
            book.assign_data(s, s)
            ws.initial_roots[s] = book
        #clustering = ws.cluster_observations(number_clusters=3)
        ws.report_clustering()
        pass
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
    
    def test_report_equiv_cluster(self):
        print "Testing report_equiv_cluster in WordSpace"
        sentences = ["Red blue blue blue blue blue blue blue blue blue blue", \
            "Blue red red red red red red red red red red", \
            "Red red blue blue blue blue blue blue blue blue blue blue blue", \
            "Blue blue red red red red red red red red red red red"]
        ws = WordSpace()
        for s in sentences:
            book = BookDataPoint()
            book.assign_data(s,s)
            ws.add_observation(book)
        
        root_set_one = sentences[:2]
        #print "Printing root_set_one \n\n", root_set_one
        ws.initial_roots = {}
        for s in root_set_one:
            book = BookDataPoint()
            book.assign_data(s,s)
            ws.initial_roots[s] = book
        first_clustering = ws.cluster_observations(number_clusters=2)
        
        root_set_two = sentences[2:]
        #print "Printing root_set_two \n\n", root_set_two
        ws.initial_roots = {}
        for s in root_set_two:
            book = BookDataPoint()
            book.assign_data(s,s)
            ws.initial_roots[s] = book
        second_clustering = ws.cluster_observations(number_clusters=2)
        
        #print "Printing first_cluster \n\n", first_clustering
        
        #print "\n\n Printing second_cluster \n\n", second_clustering
        
        result = ws.check_equivalent_clusterings(first_clustering, second_clustering)
        self.assertTrue(result)
        pass
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
    
    def test_cluster_given_roots(self):
        print "Testing cluster_given_roots in WordSpace"
        ws = WordSpace()
        sentences = ["Jane says hello to Spot.", \
            "Dick says hello to Spot. Hello, Spot, Hello", \
            "Jane asks Dick where Spot has gotten to. Ask, Jane, ask.", 
            "Jane and Dick are confused about Spot."]
        root_sents = ["Dick Jane Spot", "says asks gotten are", \
            "to hello where has and confused about"]
        for s in sentences:
            book = BookDataPoint()
            book.assign_data(s, s)
            #print book.hist
            ws.add_observation(book)
        for s in root_sents:
            book = BookDataPoint()
            book.assign_data(s, s)
            ws.initial_roots[s] = book
            #print ws.initial_roots[s].hist
        result = ws.cluster_observations(number_clusters=3)
        #print "\n\n Printing cluster results from test \n\n ", result
        test_one = "Dick Jane Spot" in result
        test_two = "says asks gotten are" in result
        test_three = "to hello where has and confused about" in result
        
        result = test_one and test_three and not test_two
        self.assertTrue(result)
        pass
            
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def test_find_clustering_means(self):
        print "Testing find_clustering_means in WordSpace"
        clusters = {}
        clusters['cluster_one'] = {}
        sentences = ["Jane says hello to Spot.", \
            "Dick says hello to Spot. Hello, Spot, Hello", \
            "Jane asks Dick where Spot has gotten to. Ask, Jane, ask.", 
            "Jane and Dick are confused about Spot."]
        for sen in sentences:
            clusters['cluster_one'][sen] = BookDataPoint()
            clusters['cluster_one'][sen].assign_data(sen, sen)
        
        theoretical_mean_one = {}
        theoretical_mean_one['jane'] = float(101)/float(770)
        theoretical_mean_one['says'] = float(13)/float(160)
        theoretical_mean_one['hello'] = float(23)/float(160)
        theoretical_mean_one['to'] = float(183)/float(1760)
        theoretical_mean_one['spot'] = float(1053)/float(6160)
        theoretical_mean_one['dick'] = float(221)/float(2464)
        theoretical_mean_one['asks'] = float(1)/float(44)
        theoretical_mean_one['ask'] = float(2)/float(44)
        theoretical_mean_one['where'] = float(1)/float(44)
        theoretical_mean_one['has'] = float(1)/float(44)
        theoretical_mean_one['gotten'] = float(1)/float(44)
        theoretical_mean_one['and'] = float(1)/float(28)
        theoretical_mean_one['are'] = float(1)/float(28)
        theoretical_mean_one['confused'] = float(1)/float(28)
        theoretical_mean_one['about'] = float(1)/float(28)
            
        clusters['cluster_two'] = {}
        sentences = ["99 red balloons", "Floating in the summer sky", \
            "Panic bells it's red alert", "There's something here from somewhere else", \
            "The war machine it springs to life", "Opens up one eager eye", \
            "Focusing it on the sky", "As 99 red balloons go by"]
            
        theoretical_mean_two = {}
        theoretical_mean_two['99'] = float(1)/float(16)
        theoretical_mean_two['red'] = float(7)/float(80)
        theoretical_mean_two['balloons'] = float(1)/float(16)
        theoretical_mean_two['floating'] = float(1)/float(40)
        theoretical_mean_two['in'] = float(1)/float(40)
        theoretical_mean_two['the'] = float(19)/float(280)
        theoretical_mean_two['summer'] = float(1)/float(40)
        theoretical_mean_two['sky'] = float(1)/float(20)
        theoretical_mean_two['panic'] = float(1)/float(40)
        theoretical_mean_two['bells'] = float(1)/float(40)
        theoretical_mean_two['its'] = float(1)/float(40)
        theoretical_mean_two['alert'] = float(1)/float(40)
        theoretical_mean_two['theres'] = float(1)/float(48)
        theoretical_mean_two['something'] = float(1)/float(48)
        theoretical_mean_two['here'] = float(1)/float(48)
        theoretical_mean_two['from'] = float(1)/float(48)
        theoretical_mean_two['somewhere'] = float(1)/float(48)
        theoretical_mean_two['else'] = float(1)/float(48)
        theoretical_mean_two['war'] = float(1)/float(56)
        theoretical_mean_two['machine'] = float(1)/float(56)
        theoretical_mean_two['it'] = float(3)/float(70)
        theoretical_mean_two['springs'] = float(1)/float(56)
        theoretical_mean_two['to'] = float(1)/float(56)
        theoretical_mean_two['life'] = float(1)/float(56)
        theoretical_mean_two['opens'] = float(1)/float(40)
        theoretical_mean_two['up'] = float(1)/float(40)
        theoretical_mean_two['one'] = float(1)/float(40)
        theoretical_mean_two['eager'] = float(1)/float(40)
        theoretical_mean_two['eye'] = float(1)/float(40)
        theoretical_mean_two['focusing'] = float(1)/float(40)
        theoretical_mean_two['on'] = float(1)/float(40)
        theoretical_mean_two['as'] = float(1)/float(48)
        theoretical_mean_two['go'] = float(1)/float(48)
        theoretical_mean_two['by'] = float(1)/float(48)

        for sen in sentences:
            clusters['cluster_two'][sen] = BookDataPoint()
            clusters['cluster_two'][sen].assign_data(sen,sen)
            
        ws = WordSpace()
        ws.find_clustering_means(clusters)
        
        dist1 = ws.distance_metric_ell_one_histos(theoretical_mean_one, ws.new_initial_roots['cluster_one'])
        self.assertTrue(dist1 < 0.0001)
        
        #print "\n\n PRINTING THEORETICAL MEAN \n\n ", theoretical_mean_two
        #print "\n\n PRINTING ws.new_initial_roots \n\n ", ws.new_initial_roots['cluster_two']
        dist2 = ws.distance_metric_ell_one_histos(theoretical_mean_two, ws.new_initial_roots['cluster_two'])
        self.assertTrue(dist2 < 0.0001)
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
    
    def test_find_mean(self):
        print "Testing find_mean in WordSpace"
        cluster = {}
        sentences = ["Jane says hello to Spot.", \
            "Dick says hello to Spot. Hello, Spot, Hello", \
            "Jane asks Dick where Spot has gotten to. Ask, Jane, ask.", 
            "Jane and Dick are confused about Spot."]
        for sen in sentences:
            cluster[sen] = BookDataPoint()
            cluster[sen].assign_data(sen, sen)
        
        ws = WordSpace()
        observed_mean = ws.find_mean(cluster)
        
        theoretical_mean = {}
        theoretical_mean['jane'] = float(101)/float(770)
        theoretical_mean['says'] = float(13)/float(160)
        theoretical_mean['hello'] = float(23)/float(160)
        theoretical_mean['to'] = float(183)/float(1760)
        theoretical_mean['spot'] = float(1053)/float(6160)
        theoretical_mean['dick'] = float(221)/float(2464)
        theoretical_mean['asks'] = float(1)/float(44)
        theoretical_mean['ask'] = float(2)/float(44)
        theoretical_mean['where'] = float(1)/float(44)
        theoretical_mean['has'] = float(1)/float(44)
        theoretical_mean['gotten'] = float(1)/float(44)
        theoretical_mean['and'] = float(1)/float(28)
        theoretical_mean['are'] = float(1)/float(28)
        theoretical_mean['confused'] = float(1)/float(28)
        theoretical_mean['about'] = float(1)/float(28)

        dist = ws.distance_metric_ell_one_histos(theoretical_mean, observed_mean)
        self.assertTrue(dist < 0.001)
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
    
    def test_ass_root_to_point(self):
        print "Testing ass_root_to_point in WordSpace"
        ws = WordSpace()
        sentences = ["Jane says hello to Spot.", \
            "Dick says hello to Spot.", \
            "Jane asks Dick where Spot has gotten to.", 
            "Jane and Dick are confused about Spot."]
        for s in sentences:
            book = BookDataPoint()
            book.assign_data(s,s)
            for word in s:
                ws.add_observation(book)
                ws.initial_roots = {}
                root_sents = ["Dick Jane Spot", \
                    "says asks gotten are", \
                    "to hello where has and confused about"]
                for root in root_sents:
                    ws.initial_roots[root] = BookDataPoint()
                    ws.initial_roots[root].assign_data(root, root)
                
        thisSentence = "Jane says hello to Spot."
        data_point = BookDataPoint()
        data_point.assign_data(thisSentence,thisSentence)
        key = ws.ass_root_to_point(data_point)
        self.assertEqual(key, "Dick Jane Spot")
        
        thisSentence = "Jane asks Dick where Spot has gotten to."
        data_point = BookDataPoint()
        data_point.assign_data(thisSentence,thisSentence)
        key = ws.ass_root_to_point(data_point)
        self.assertEqual(key, "to hello where has and confused about")
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

    def test_gen_init_roots(self):
        # We aren't really willing to test how random the randomly
        # generated sentences are, but we are willing to test whether
        # the randomly generated sentences are really drawn from the
        # correct wordspace.

        print "Testing gen_init_roots in WordSpace"
        
        ws = WordSpace()
        sentence = "Jane sees Dick run. Run, Dick, run! Dick sees Jane play with Spot. Play, Jane, play!"
        sentence = (sentence.translate(None,\
            string.punctuation)).lower()
        sentence = sentence.split()
        for word in sentence:
            ws.found_word(word)

        ws.generate_initial_roots(number_roots=5)
        vectorsContainedInWordSpace = True
        for root in ws.initial_roots:
            for word in ws.initial_roots[root].hist:
                if word not in ws.space:
                    vectorsContainedInWordSpace = False
        
        self.assertEqual(True,vectorsContainedInWordSpace)
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####
    
    def test_metric(self):
        # We generate two sentences with a known distance (1.0)
        # and then compute that distance.
        print "Testing metric in WordSpace"
        
        sentence_one = "Say hello, Bob, please."
        title_one = "Title One"
        data_point_one = BookDataPoint()
        data_point_one.assign_data(sentence_one, title_one)
        sentence_two = "Please, Bob, say hello!"
        title_two = "Title Two"
        data_point_two = BookDataPoint()
        data_point_two.assign_data(sentence_two, title_two)

        ws = WordSpace()
        ws.add_observation(data_point_one)
        ws.add_observation(data_point_two)
        d = ws.distance_metric_ell_one_keys(title_one, title_two)
        self.assertEqual(d, 0.)
        
        sentence_one = "Nancy says hello, Bob."
        title_one = "Title One"
        data_point_one = BookDataPoint()
        data_point_one.assign_data(sentence_one, title_one)
        
        sentence_two = "Please, Bob, say hello!"
        title_two = "Title Two"
        data_point_two = BookDataPoint()
        data_point_two.assign_data(sentence_two, title_two)
        
        ws = WordSpace()
        ws.add_observation(data_point_one)
        ws.add_observation(data_point_two)
        d = ws.distance_metric_ell_one_keys(title_one, title_two)
        self.assertEqual(d, 1.0)
        
#### #### #### #### #### #### #### #### #### #### #### #### #### ####

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

class Librarian(object):
    ''' This class is the controller of everything. Variables:
    self.cat : Catalog
    self.ws  : WordSpace()
    
    Functions:
    rm : remove a file with file name 'filename'
    consider_catalog : instantiate self.cat and call build_catalog
    retrieve_book_pdf_with_keys : given the book key in self.cat, 
        find the url and generate a filename and call the more usual
        retrieve_book_pdf function
    retrieve_book_pdf : given a url and a local filename pdf_filename,
        download the file at the url to pdf_filename if possible.
    retrieve_catalog : fetch every available pdf file in the catalog
        to a local copy. This takes a long time and a lot of downloading.
    pdf_to_text : Given a pdf_filename, generate a text file by first
        generating an OCR-made searchable pdf, and then generating the
        searchable PDF into a text file.
    pdf_to_ocr : The first half of the above puzzle... turn a PDF file
        into a searchable PDF file with OCR
    ocr_to_text : The second half... retrieve the text from the searchable
        pdf
    ocr_catalog : Given a catalog, generate all the text files.
    build_word_space : Given a bunch of text files, build BookDataPoints
        out of them and add them to self.ws WordSpace()
    cluster_word_space : Perform some iterations of k-means clustering
        and report the results
    display_solution : This is the main entry into the Librarian class.
        first consider a catalog, then build a WordSpace with build_word_space,
        then find clusters with cluster_word_space, then report the solution
        with report_clustering.
    '''
    def __init(self):
        self.cat = Catalog()
        self.ws = WordSpace()
        
        pass

    def rm(self,filename):
        value = None
        if os.path.isfile(filename):
            try: 
                os.remove(filename)
                value = True
            except:
                value = False
        return value
    
    def consider_catalog(self):
        print "\n\n Beginning to consider catalog."
        self.cat = Catalog()
        self.cat.build_catalog()

    def retrieve_book_pdf_with_key(self, key='2960'):
        worked = False
        pdf_filename = str(key) + ".pdf"
        for link in self.cat.collection[key]['downloadLinks']:
            if link[-4:] == ".pdf":
                worked = self.retrieve_book_pdf(link, pdf_filename)
                break
        return worked

    def retrieve_book_pdf(self, url="http://www.orimi.com/pdf-test.pdf", \
        pdf_filename = "pdf-test.pdf"):
        # Takes file at url and stores it as localFilename
        worked = False
        browser = mechanize.Browser()
        browser.set_handle_robots(False)
        try:
            browser.retrieve(url,pdf_filename)
            worked = True
        except:
            print "Error! Something went wrong retrieving file ", pdf_filename
        return worked

    def retrieve_catalog(self):
        for book in self.cat.collection:
            pdf_filename = str(book) + ".pdf"
            if not os.path.isfile(pdf_filename):
                for link in self.cat.collection[book]['downloadLinks']:
                    if link[-4:] == ".pdf":
                        self.retrieve_book_pdf(link,pdf_filename)                    
                        break
        pass

    def pdf_to_text(self, pdf_filename):
        # Given the file name of a local pdf file,
        # we first call pdf_to_ocr and then ocr_to_text
        # to generate a text file.
        ocr_filename = self.pdf_to_ocr(pdf_filename)
        if ocr_filename != None:
            txt_filename = self.ocr_to_text(ocr_filename)
        else:
            text_filename = None
        return txt_filename, ocr_filename

    def pdf_to_ocr(self, pdf_filename):
        # Given the file name of a local pdf file,
        # we use ocr to construct a searchable pdf
        # version of the file.
        #subprocess.call(["pypdfocr","-d",pdf_filename])
        try:
            subprocess.call(["pypdfocr",pdf_filename])
            ocr_filename = pdf_filename[:-4] + "_ocr.pdf"
        except:
            ocr_filename = None
        return ocr_filename

    def ocr_to_text(self,ocr_filename):
        # Given the file name of a searchable pdf,
        # we generate a text file.
        txt_filename = ocr_filename[:-4] + ".txt"
        try:
            subprocess.call(["pdf2txt.py","-o", txt_filename,  ocr_filename])
        except:
            text_filename = None
        return txt_filename

    def ocr_catalog(self, mode="offline", active_conversion=False):
        # Takes each downloaded pdf file and converts it to a text file.
        print "\n\n Starting ocr_catalog \n\n"
        file_names_dict = {}
        offline = (mode=="offline")
        if active_conversion:
            print "\n\n Download each available PDF files unless they or ",\
                "their text version exists. If the text file does not yet",\
                " exist, then perform pdf_to_text on the file first."
            for book in self.cat.collection:
                pdf_filename = str(book) + ".pdf"
                txt_filename = str(book) + "_ocr.txt"
                if os.path.isfile(txt_filename):
                    print "File ", txt_filename, " present, so we don't ",\
                        "need to download..."
                elif not offline:
                    if not os.path.isfile(pdf_filename):
                        print "File ", pdf_filename, " not present, ",\
                            "attempting download..."
                        self.retrieve_book_pdf_with_key(book)
                    else:
                        print "File ", pdf_filename, " present, no need",\
                            " to download."
            print "\n\n PDF files downloaded. Constructing filename ",\
                "dictionary."
            for book in self.cat.collection:
                pdf_filename = str(book) + ".pdf"
                ocr_filename = str(book) + "_ocr.pdf"
                txt_filename = str(book) + "_ocr.txt"
                
                if os.path.isfile(txt_filename):
                    print "File ", txt_filename, " present, so we don't ",\
                        "need to OCR..."
                    file_names_dict[book] = [txt_filename, ocr_filename]
                elif os.path.isfile(pdf_filename) and not offline:
                    print "File ", txt_filename, " not present and we are not",\
                        " in offline mode, so we will convert the pdf to text."
                    txt_filename, ocr_filename = self.pdf_to_text(pdf_filename)
                    file_names_dict[book] = [txt_filename, ocr_filename]
        else:
            print "\n\n Store all available text filenames and return...",\
                "(they have already been OCR'd)"
            for book in self.cat.collection:
                txt_filename = str(book) + "_ocr.txt"
                ocr_filename = str(book) + "_ocr.pdf"
                if os.path.isfile(txt_filename):
                    file_names_dict[book] = [txt_filename, ocr_filename]
        return file_names_dict
        return file_names_dict                
    
    def build_word_space(self, webmode="offline",\
        to_build_from_file=False, active_conversion=False):
        # Builds a catalog of pdf files with consider_catalog.
        # Performs OCR on each and calls ws.found_word on 
        # each unique word to build the ambient word space.
        print "\n\n Starting build_word_space..."

        self.ws = WordSpace()
        if to_build_from_file:
            built = self.ws.build_word_space_from_file()
        else:
            if len(self.cat.collection) <= 0:
                self.consider_catalog()
            file_names_dict = self.ocr_catalog(webmode, active_conversion)
            for book in file_names_dict:
                print "Adding book ", book, " to word_space..."
                if file_names_dict[book][0]:            
                    try:
                        f = open(file_names_dict[book][0], "r")
                        this_sentence = f.read()
                        f.close()
                        this_sentence = (this_sentence.translate(None, \
                            string.punctuation)).lower()
                        book_data =self.cat.collection[book]['title']
                    except:
                        this_sentence = None                    
                        book_data = None
                    if this_sentence and book_data:
                        this_book = BookDataPoint()
                        this_book.assign_data(this_sentence, book_data)
                        self.ws.add_observation(this_book)
                print len(self.ws.observations)
            self.ws.write_word_space_to_file()
            built=True
        return built
        
    def cluster_word_space(self, number_clusters = 3, number_iterations = 3):

        print "\n \n Beginning cluster_word_space on observation set ", self.ws.observations
        converged = False # Stop when True
        

        # Generate some initial roots randomly.
        print "Generating roots, working on iteration ", number_iterations
        self.ws.generate_initial_roots(number_roots=number_clusters)

        # Assign colors/clusters according to initial roots
        print "Assigning colors."
        clustering_one = self.ws.cluster_observations(number_clusters)
        # Find averages of colored clusters
        print "Finding average of color groups."
        self.ws.find_clustering_means(clustering_one)
        # Set these averages to our initial roots
        print "Reassigning roots to averages of color groups."
        self.ws.set_roots_to_means()
        # Assign colors/clusters according to initial roots again
        print "Reassigning colors."
        clustering_two = self.ws.cluster_observations(number_clusters)
        print "Checking if reassigned colors are equivalent to assigned colors."
        # Check if second coloring is the same as the first.
        converged = not self.ws.check_equivalent_clusterings(\
            clustering_one, clustering_two)

        while not converged and number_iterations > 0:
            print "\n\n Working on iteration ", number_iterations, "..."
            # Copy over
            print "Assigning colors."
            clustering_one = copy.deepcopy(clustering_two)
            # Compute means of newest clustering.
            print "Finding average of color groups."
            self.ws.find_clustering_means(clustering_one)
            # Set initial roots to these means.
            print "Reassigning roots to averages of color groups."
            self.ws.set_roots_to_means()
            # Assign colors/clustering according to these initial roots
            print "Reassigning colors."
            clustering_two = self.ws.cluster_observations(\
                number_clusters)
            # Check if the newest coloring is the same as the latest.
            print "Checking if reassigned colors are equivalent to assigned colors."
            converged = self.ws.check_equivalent_clusterings( \
                clustering_one, clustering_two)
            number_iterations = number_iterations -1
        return clustering_two
    
    def display_solution(self, webmode, to_build_from_file, active_conversion):
        self.consider_catalog()
        self.build_word_space(webmode, to_build_from_file, active_conversion)
        soln = self.cluster_word_space()
        self.ws.report_clustering(soln)
    
    def build_librarian_from_file(self):
        # To be implemented
        pass
        
    def write_librarian_to_file(self):
        # To be implemented
        pass

#### #### #### #### #### #### #### #### #### #### #### #### #### ####

class TestLibrarian(unittest.TestCase):
    ''' Tests the Librarian class '''
    def test_rm(self):
        print "Testing rm in Librarian"
        edith = Librarian()
        filename = "testing_temporary_file.dat"
        f = open(filename, "w")
        f.write("Test test test")
        f.close()
        self.assertTrue(os.path.isfile(filename))
        val = edith.rm(filename)
        self.assertTrue(val)
        pass
    
    def test_consider_catalog(self):
        print "Testing consider_catalog"
        edith = Librarian()
        edith.consider_catalog()
        book = 5113
        ground_truth = {'publisher': 'lulea university of technology', 'author': 'j bystrom and  l persson and  f stromberg', 'year': '2010', 'downloadLinks': ['http://www.scribd.com/doc/37251737/Bystrom-Applied-Mathematics', 'http://www.scribd.com/doc/37251737/Bystrom-Applied-Mathematics'], 'title': 'a basic course in applied mathematics'}
        test_value = cmp(edith.cat.collection[book],ground_truth)
        self.assertEqual(test_value, 0)
        self.assertTrue(True)
        pass

    def test_retrieve_book_pdf(self):
        print "Testing retrieve_book_pdf"
        edith = Librarian()
        url = "http://www.orimi.com/pdf-test.pdf"
        pdf_filename = "pdf-test.pdf"
        edith.retrieve_book_pdf(url, pdf_filename)
        self.assertTrue(os.path.isfile(pdf_filename))
        edith.rm(pdf_filename)
        self.assertFalse(os.path.isfile(pdf_filename))
        pass
    
    def test_pdf_to_text(self):
        print "Testing pdf_to_text"
        edith = Librarian()
        url = "http://www.orimi.com/pdf-test.pdf"
        pdf_filename = "pdf-test.pdf"
        txt_filename = "pdf-test_ocr.txt"
        edith.retrieve_book_pdf(url, pdf_filename)
        self.assertTrue(os.path.isfile(pdf_filename))
        edith.pdf_to_text(pdf_filename)
        self.assertTrue(os.path.isfile(txt_filename))
        pass

    def test_pdf_to_ocr(self):
        print "Testing pdf_to_ocr"
        edith = Librarian()
        url = "http://www.orimi.com/pdf-test.pdf"
        pdf_filename = "pdf-test.pdf"
        ocr_filename = "pdf-test_ocr.pdf"
        edith.retrieve_book_pdf(url, pdf_filename)
        self.assertTrue(os.path.isfile(pdf_filename))
        edith.pdf_to_ocr(pdf_filename)
        self.assertTrue(os.path.isfile(ocr_filename))
        pass

    def test_ocr_to_text(self):
        print "Testing ocr_to_text"
        edith = Librarian()
        ocr_filename = "funky_ocr.pdf"
        text_filename = "funky_ocr.txt"
        edith.ocr_to_text(ocr_filename)
        self.assertTrue(os.path.isfile(text_filename))
        stuff = type(open(text_filename,"r").read())
        self.assertEqual(stuff, type("blah"))
        pass

    def test_retrieve_catalog(self):
        print "Testing retrieve_catalog"
        edith = Librarian()
        edith.consider_catalog()
        edith.retrieve_catalog()
        alleged_file_one = "2860.pdf"
        alleged_file_two = "4903.pdf"
        self.assertTrue(os.path.isfile(alleged_file_one) and os.path.isfile(alleged_file_two))
        pass

    def test_ocr_catalog(self):
        print "Testing ocr_catalog"
        edith = Librarian()
        edith.consider_catalog()
        edith.ocr_catalog()
        alleged_file_one = "2860_ocr.pdf"
        alleged_file_two = "4903_ocr.pdf"
        self.assertTrue(os.path.isfile(alleged_file_one) and os.path.isfile(alleged_file_two))
        pass
    
    def test_build_word_space(self):
        print "Testing build_word_space"
        edith = Librarian()
        edith.consider_catalog()
        edith.build_word_space()
        print edith.ws.get_random_sentence()
        pass


#print "\n\n Testing BookDataPoint object. \n\n"
#suite = unittest.TestLoader().loadTestsFromTestCase(TestBookDataPoint)
#unittest.TextTestRunner(verbosity=1).run(suite)

#print "\n\n Testing WordSpace object. \n\n"
#suite = unittest.TestLoader().loadTestsFromTestCase(TestWordSpace)
#unittest.TextTestRunner(verbosity=1).run(suite)

#print "\n\n Testing Catalog object. \n\n"
#suite = unittest.TestLoader().loadTestsFromTestCase(TestCatalog)
#unittest.TextTestRunner(verbosity=1).run(suite)

#print "\n\n Testing Librarian object. \n\n"
#suite = unittest.TestLoader().loadTestsFromTestCase(TestLibrarian)
#unittest.TextTestRunner(verbosity=1).run(suite)

edith = Librarian()

edith.display_solution(webmode="offline", to_build_from_file = False, active_conversion=False) # Run for offline work, with local text files
#edith.display_solution(webmode="online", to_build_from_file = False, active_conversion=True) # Run for online fetching
