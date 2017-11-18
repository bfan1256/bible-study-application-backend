# -*- coding: utf-8 -*-
"""Similarity Class to handle verse similarities

Authors: Brandon Fan
Last Edit Date: 11/16/2017
"""

import os
import string
import json
import csv
import copy
import pandas as pd
import numpy as np
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import cosine_similarity
nltk.download('stopwords')
nltk.download('punkt')

MAX_LEN = 24


class Similarity(object):
    """Similarity class that utilizes deep learning to find similar verses

    Uses gensim Doc2Vec and scikit-learn TF-IDF to calculate similar verses

    Attributes:
        bible_file (str): Bible file path to load JSON file.
        glove_file (str): GloVe file path to load text file.
        _testing (boolean | optional): creates dummy matrix for testing purposes (i.e. Travis CI)
    """

    def __init__(self, bible_file, glove_file, _testing=False):
        if self._check_file(bible_file, '.json'):
            self.bible_data = json.load(
                open(bible_file, encoding='utf-8-sig'))
            self.verse_data = []
            self.bible_verses = []
        else:
            self._throw_value_error('Please enter a proper bible .json file')
        for book in self.bible_data:
            for chapter in book['data']:
                for verses in chapter['verses']:
                    self.verse_data.append(verses)
        if _testing:
            self.bible_verses = self.verse_data
            print('**** Warning Using Testing Environment ****')
            print(' - Generating Test Similarity Matrix...')
            self.sim_matrix = np.zeros((len(self.verse_data), len(self.verse_data)))
            return
            
        print(' - Loading GloVe File...')
        if self._check_file(glove_file, '.txt'):
            self.glove_words = pd.read_table(glove_file,
                                             sep=" ", index_col=0,
                                             header=None, quoting=csv.QUOTE_NONE)
        else:
            self._throw_value_error('Please enter a proper glove .txt file')

        # preprocess text corpus
        self.bible_verses = copy.deepcopy(self.verse_data)
        self.stopwords_list = set(stopwords.words('english'))
        self.exclude = set(string.punctuation)
        print(' - Tokenizing Data...')
        self.verse_data = self.tokenize_data(self.verse_data)
        assert self.verse_data[0].keys() != self.bible_verses[0].keys()
        print(' - Converting GloVe Vectors...')
        self.verse_data = self.convert_to_glove_vectors(self.verse_data)
        assert self.verse_data[0].keys() != self.bible_verses[0].keys()
        print(' - Creating Cosine Similarity Matrix...')
        self.sim_matrix = cosine_similarity(
            [verse['vector'] for verse in self.verse_data])

    def tokenize_data(self, verse_data):
        """Tokenizes passed in verse data
        Uses nltk word_tokenize to tokenize sentences into words

        Args:
            verse_data (dict): dictionary of verse data
        """
        tokenized_result = []
        for verse in verse_data:
            text = ''.join(
                ch for ch in verse['text'] if ch not in self.exclude)
            tokenized_text = word_tokenize(text)
            final_text = []
            for val in tokenized_text:
                if val not in self.stopwords_list:
                    if 'Yahweh' in val:
                        val = val.replace('Yahweh', 'God')
                    final_text.append(val)
            verse['tokenized_text'] = final_text
            tokenized_result.append(verse)
        return tokenized_result

    def convert_to_glove_vectors(self, verse_data):
        """Converts verse tokenized text into GloVe vectors
        Uses GloVe embeddings to convert verse tokenized text
        into vectors of size 200

        Args:
            verse_data (dict): verse_data run after tokenized_data

        Returns:
            verse_data_with_glove (dict): verse_data with GloVe vectors
            response is below::
                {
                    'verse': (str),
                    'verse_number': (str),
                    'text': (str),
                    'tokenized_text': (list),
                    'vector': (list)
                }
        """
        verse_data_with_glove = []
        for verse in verse_data:
            vector = np.array([])
            for word in verse['tokenized_text'][:MAX_LEN]:
                try:
                    vector = np.append(vector, self.get_glove_vector(word))
                except ValueError:
                    vector = np.append(vector, np.zeros(200))
            if vector.shape[0] < MAX_LEN * 200:
                vector = np.append(vector, np.zeros(
                    [MAX_LEN * 200 - vector.shape[0]]))
            verse['vector'] = list(vector)
            verse_data_with_glove.append(verse)
        return verse_data_with_glove

    def get_glove_vector(self, word):
        """Grabs GloVe vector representation of word
        Uses GloVe embeddings to reference word vector

        Args:
            word (str): word to find vector for

        Returns:
            (list): the GloVe representation of word

        Raises:
            ValueError: if word is not found in embeddings
        """
        try:
            return self.glove_words.loc[word].as_matrix()
        except KeyError:
            self._throw_value_error(
                '{0} was not found in the glove embeddings.'.format(word))

    def get_similar_values(self, verse, total_values=10, _testing=False):
        """Gets similar values using GloVe and Cosine Sim.
        Uses GloVe embeddings and cosine similarity matrix to find
        similar bible verses

        Args:
            verse (str): verse reference (i.e. 'Genesis 1:1' or 'Exodus 2:3')
            total_values (int | optional): number of values to return

        Returns:
            final_text (list): list of similar verses
            response is below::
                [
                    {
                        'verse': (str),
                        'verse_number': (str),
                        'text': (str),
                        'tokenized_text': (list),
                    }
                    ...
                ] (length of list = total_values)
        """
        proper_index = None
        for index, verse_text in enumerate(self.verse_data):
            if verse_text['verse'] == verse:
                proper_index = index
                break
        sim_text = self.sim_matrix[proper_index][1:]
        final_text = []
        final_indices = list(reversed(np.argsort(sim_text)))[:total_values]
        for i in final_indices:
            final_text.append(self.bible_verses[i])
        return list(final_text)

    @staticmethod
    def _check_file(file_path, ending):
        return file_path.endswith(ending) and os.path.isfile(file_path)

    @staticmethod
    def _throw_value_error(information):
        raise ValueError(information)

if __name__ == '__main__':
    sim = Similarity('../../bible-files/english-web-bible.json', '../../dl-files/glove.6B.200d.txt', _testing=True)
