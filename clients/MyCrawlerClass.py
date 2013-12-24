#coding=utf-8
import os, sys, re
from bs4 import BeautifulSoup
from urlparse import urlparse

class Classifier():
    def __init__(self):
        pass

    def get_class(self, content, url):
        raise NotImplemented

class DefaultClassifier(Classifier):
    def __init__(self):
        Classifier.__init__(self)
        self.name = 'default'

    def get_name(self):
        return self.name

    def get_class(self, content_obj, url):
        return 'default'

class Processor():
    def __init__(self):
        self.name = None
        self.remove_class = []
        self.remove_name = []
        self.clean_tags = {
            'p': [],
            'img': ['src'],
            'div': [],
            }
        self.content = ''
        self.title = ''
        self.first_img = ''

    def get_name(self):
        raise NotImplemented

class DefaultProcessor(Processor):
    def __init__(self):
        Processor.__init__(self)

    def get_name(self):
        return self.name

    def process(self, content_obj):
        return 'default process output'

class Classify():
    def __init__(self, content, url):
        self.clas_list = []
        self.proc_list = []
        self.url = url
        self.content = content
        self.content_obj = BeautifulSoup(self.content)
        self.proc = None

    def regist_classifier(self, clas):
        self.clas_list.append(clas)

    def regist_processor(self, proc):
        self.proc_list.append(proc)

    def _get_processor(self):
        # Get processor name from classifiers
        proc_name = None
        for clas in self.clas_list:
            proc_name = clas.get_class(self.content_obj, self.url)
            if proc_name:
                # processor got
                break
        else:
            proc_name = None

        if proc_name is None:
            raise Exception("Can not match classifier \"%s\"" % proc_name)

        return clas.get_name(), proc_name

    def get_processor(self):
        clas_name, proc_name = self._get_processor()

        # Get processor
        proc = None
        for proc in self.proc_list:
            if proc.get_name() == proc_name:
                break
        else:
            proc = None

        if proc is None:
            raise Exception("Can not get processor with \"%s\" from clas_name \"%s\"" % (proc_name, clas_name))

        return proc

    def process(self):
        self.proc = self.get_processor()

        return self.proc.process(self.content_obj)

