

'''
Executive decisions re: what defines a rhyme:

one-syllable words with the same end_sound are rhymes.
one-syllable words rhyme with all multi-syllabic words with the same end_sound
two-syllable words rhyme if their end_sound matches and their penultimate vowel
sound matches
words of more than two syllable will only be considered by their last two syllables

THIS IS SUBJECT TO CHANGE AT ANY time
'''

from collections import Counter, defaultdict
import nltk
from nltk.corpus import cmudict
from nltk.tokenize import word_tokenize, wordpunct_tokenize, sent_tokenize
import numpy as np
import os.path
import pandas as pd
import pickle
import random
import re
import requests
import string
import sys


#dictionary to look up pronounciations
master_dict = cmudict.dict()

def save_obj(obj, fname ):
    with open(fname, 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(fname ):
    with open(fname, 'rb') as f:
        return pickle.load(f)

class Poem(object):

    def __init__(self, text, fname=None):
        #remove punctuation
        text = text.translate(str.maketrans(' ', ' ', string.punctuation)).lower()
        #all the text in order
        self.fulltext = (text.split())
        #all unique words, as strings
        self.str_words = set(self.fulltext)
        #all unique words, as Word objects
        self.obj_words = [Word(w) for w in self.str_words]
        #all words as keys, all words that precede the keyword with counts
        self.pairs_dict = self.make_doubles(self.fulltext)
        #bigrams as keys with preceding words as values
        self.triples_dict = self.make_triples(self.fulltext)

        #open or create a dictionary with the pronounciation of all unique words
        if fname:
            dict_name = 'pron_dict_' + fname +  '.pkl'
            if os.path.isfile('dicts/{}'.format(dict_name)):
                print("loading pronounciation dictionary")
                self.pron_dict = load_obj(dict_name)
            else:
                self.make_pron_dict()
                save_obj(self.pron_dict, dict_name)

        #open or create a dictionary with all rhymes of all unique words
            rh_dict_name = 'rh_dict_' + fname +  '.pkl'
            if os.path.isfile('dicts/{}'.format(rh_dict_name)):
                print("loading rhyming dictionary")
                self.rhyme_dict = load_obj(rh_dict_name)
            else:
                self.make_rhyme_dict()
                save_obj(self.rhyme_dict, rh_dict_name)

    def make_pron_dict(self):
        self.pron_dict = {}
        print("\n\nNow creating pronounciation dictionary")
        for w in self.obj_words:
            if w.end_sound:
                self.pron_dict[w.word] = w.pron
            # else:
            #     self.pron_dict[w.word] = ['X']

    def make_rhyme_dict(self):
        self.rhyme_dict = {}
        count = 0
        print("Now creating rhyme dictionary")
        for w in self.obj_words:
            if w.syls == 0:
                continue
            elif w.syls == 1:
                self.rhyme_dict[w.word] = self.find_onesyl_rhymes(w)
            else:
                self.rhyme_dict[w.word] = self.find_twosyl_rhymes(w)
            count += 1
            if count % 1000 == 0:
                print("...")

    def make_triples(self, txt):
        this_txt = ['SPACE', 'SPACE'] + txt
        triplet_dict = defaultdict(Counter)
        for i in range(len(this_txt) - 2):
            triplet_dict[(this_txt[i+1], this_txt[i+2])].update({this_txt[i]:1})

        return triplet_dict

    def make_doubles(self, txt):
        this_txt = ['SPACE'] + txt
        pairs_dict = defaultdict(Counter)
        for i in range(len(this_txt) - 1):
            pairs_dict[this_txt[i+1]].update({this_txt[i]:1})

        return pairs_dict

    def find_onesyl_rhymes(self, base_word_obj):
        rhymes = []
        for w in self.obj_words:
            try:
                if base_word_obj.word != w.word and \
                                    base_word_obj.end_sound == w.end_sound:
                    rhymes.append(w.word)
            except KeyError:
                continue
        return rhymes


    def find_twosyl_rhymes(self, base_word_obj):
        rhymes = []
        for w in self.obj_words:
            if w.syls >= 2:
                try:
                    if base_word_obj.word != w.word and \
                                    base_word_obj.end_sound == w.end_sound and \
                                    base_word_obj.penul_vowel == w.penul_vowel:
                        rhymes.append(w.word)
                except KeyError:
                    continue
        return rhymes

    def get_next_word(self, anchor_pos, next_pos):
        '''Given an anchor part of speech and the part of speech of the word it should rhyme with,
        generate potential pairs of words and return a random option'''

        pot_next_words = []
        while pot_next_words == []:
            anchor = self.make_pos_rhyme_pairs((first_pos, first_pos))[1]
            pot_next_words = [w for w in list(self.count_dict[anchor].keys()) \
                                            if Word(w).pos == next_pos]
        return anchor, random.choice(pot_next_words)


    def make_sent(self, sent_temp, seed=0):
        '''
        INPUT: sent_temp, a template of parts of speech
        OUTPUT: a new sentence that follows this template
        '''
        random.seed(seed)
        s_len = len(sent_temp)

        #This will find an anchor word and build the sentence around it

        anchor, next_word = get_next_word(sent_temp[-1][1], sent_temp[-2][1])

        for i in range(-3, -1*s_len, -1):
            this_pos = sent_temp[i][1]
            print(this_pos)
            pot_next_words = []
            tries = 0
            while pot_next_words == [] and tries < 10:
                try:
                    pot_next_words = [w for w in list(count_dict[next_word].keys()) \
                                                    if Word(w).pos == this_pos]
                except KeyError:
                    pass
                tries += 1
            if pot_next_words == []:
                pot_next_words = random.choice([w.word for w in \
                                        self.obj_words if w.pos == this_pos])
            pot_next_words = [w for w in pot_next_words if len(w) > 1]
            new_next_word = random.choice(pot_next_words)
            w1 = next_word
            next_word = new_next_word
            line.append(next_word)
            print('line: ', line)

        line_rev = list(reversed(line))
        print(" ".join(line_rev))

    def preceding_word_from_single(self, word):
        next_word = random.choice(list(self.pairs_dict[word].keys()))
        return next_word

    def preceding_word_from_tup(self, tup):
        next_word = random.choice(list(self.triples_dict[tup].keys()))
        return next_word

    def make_pentameter(self, anchor, seed=0):

        line = []
        syl_len = 0

        syl_len += Word(anchor).syls

        random.seed(seed)

        line.append(anchor)
        next_word = self.preceding_word_from_single(anchor)
        syl_len += Word(next_word).syls

        line.append(next_word)
        word_tup = (next_word, anchor)
        #import pdb; pdb.set_trace()

        while syl_len < 10:
            next_word = self.preceding_word_from_tup(word_tup)
            syl_len += Word(next_word).syls
            line.append(next_word)
            word_tup = (next_word, word_tup[0])

        line_rev = list(reversed(line))
        print(" ".join(line_rev))

    def make_rhyme_pairs(self):
        seed = random.choice(range(1000000000))
        random.seed(seed)
        word_1 = random.choice(list(self.rhyme_dict.keys()))
        while self.rhyme_dict[word_1] == [] or Word(word_1).pron == None:
            word_1 = random.choice(list(self.rhyme_dict.keys()))
        word_2 = random.choice(self.rhyme_dict[word_1])
        return [word_1, word_2]

    def make_pos_rhyme_pairs(self, pos_tup):
        seed = random.choice(range(1000000000))
        random.seed(seed)
        pot_keys = [w for w in self.obj_words if w.pos == pos_tup[0]]
        word_1 = random.choice(pot_keys)
        pot_pairs = [w for w in poem.rhyme_dict[word_1.word] if Word(w).pos == pos_tup[1]]
        while pot_pairs == []:
            word_1 = random.choice(pot_keys)
            pot_pairs = [w for w in poem.rhyme_dict[word_1.word] if Word(w).pos == pos_tup[1]]
        word_2 = random.choice(pot_pairs)
        return pos_tup, word_1.word, word_2

    def make_shakes_scheme(self):
        rhymes = []
        ordered_rhymes = []
        for i in range(7):
            rhymes += self.make_rhyme_pairs()
        scheme = [0, 2, 1, 3, 4, 6, 5, 7, 8, 10, 9, 11, 12, 13]
        for j in scheme:
            ordered_rhymes.append(rhymes[j])
        return ordered_rhymes

    def shakes_poem(self):
        rhymes = self.make_shakes_scheme()
        poem = []
        line_no = 0
        for rhyme in rhymes:
            if line_no % 4 == 0:
                print('\n')
            poem.append(self.make_pentameter(rhyme))
            line_no += 1
        # for line in poem:
        #     print(line)



    def poem_pos(self, text):
        '''takes tokenized text'''
        text = text.split('.')
        poem_breakdown = nltk.pos_tag(text)
        pos_to_use = []
        for element in poem_breakdown:
            pos = element[1]
            pos_to_use.append(pos)
        return pos_to_use




class Word(object):

    def __init__(self, word):
        self.word = word.lower()
        try:
            self.pron = master_dict[self.word]
            #self._num_syls()
            self.pos = nltk.pos_tag([self.word])[0][1]
            self._get_end_sound()
            self._ph_breakdown()
            self._get_penul_vowel()

        except KeyError:
            self.pron = None
            self.pos = None
            #if a word is not found but we still want to be able to count it syllables,
            #we use an ave of 3.5 letters per syl.
            self.syls = int(len(self.word)/3.5)
            self.end_sound = None
            self.penul_vowel = None
            self.breakdown = None


    def ph_type(self, phoneme):
        if phoneme[-1].isdigit():
            ph_type = 1
        else:
            ph_type = 0
        return ph_type


    def _get_end_sound(self):
        self.end_sound = []
        if self.pron:
            for phon in self.pron[0][-1::-1]:
                self.end_sound.append(phon)
                if self.ph_type(phon) == 1:
                    break

    def _ph_breakdown(self):
        self.breakdown = []
        for phon in self.pron[0]:
            self.breakdown.append(self.ph_type(phon))
        if self.breakdown != []:
            self.syls = sum(self.breakdown)

    def _get_penul_vowel(self):
        if self.syls < 2:
            self.penul_vowel = None
        else:
            vowel_sounds = [ph for ph in self.pron[0] if self.ph_type(ph) == 1]
            #print vowel_sounds
            self.penul_vowel = vowel_sounds[-2]




    def find_rhyme(self):

        pass

def removeNonAscii(s):
    return "".join(i for i in s if ord(i)<128)


if __name__ == '__main__':
    path = input('''
    Enter the location of a text file.
    https://www.gutenberg.org/browse/scores/top
    is a great place to find public domain literature.



    ''')
    text = requests.get(path).text
    name = input('  What is the name of this text? ')
    poem = Poem(removeNonAscii(text), name)
    print('\n\nA sonnet based on the text of {}'.format(name))
    poem.shakes_poem()
