#!/usr/bin/python
#encoding=utf-8
import os, sys
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(CUR_DIR, '../libs'))
import time
import urllib2
import urllib
import imghdr
import shutil
from bs4 import BeautifulSoup
from urlparse import urlparse, urljoin
from MyCrawlerClass import Classify, Classifier, Processor, DefaultClassifier, DefaultProcessor

from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc.methods import media, posts

from webtool import get_img_to_tmpdir

import logging, logging.handlers
rootLogger = logging.getLogger('')
rootLogger.setLevel(logging.DEBUG)
socketHandler = logging.handlers.SocketHandler('localhost',
                    logging.handlers.DEFAULT_TCP_LOGGING_PORT)
rootLogger.addHandler(socketHandler)

logger = logging.getLogger('mywpcrawler')

tmpdir = os.path.join(CUR_DIR, 'tmp')

import dict4ini
configpath = '/etc/wordp.ini'
CONF = dict4ini.DictIni(configpath)

CRAWLER_CLASS = CONF.client0.crawler_class
WEBSERVER_DOC_DIR = CONF.client0.webserver_doc_dir
WEBSERVER_IMAGE_DIR = CONF.client0.webserver_image_dir
WEBSERVER_IMAGE_HOST = CONF.client0.webserver_image_host
WP_XMLRPC_URL = CONF.client0.wp_xmlrpc_url
WP_XMLRPC_USER = CONF.client0.wp_xmlrpc_user
WP_XMLRPC_PASS = CONF.client0.wp_xmlrpc_pass

from wordpDB import DB

db = DB()

def copy_to_web_server(img_path, hex_dir='pre', check_unique=False):
    '''if <check_unique> is True, we will check whether the directory is exists, or we
    just use the <hex_dir> to store the image.
    RETURN: the file's(image) URL'''
    def get_a_valid_dpath(tmpdir, dn, idx=0):
        dpath = os.path.join(tmpdir, dn)
        if os.path.exists(dpath):
            n, e = os.path.splitext(dn)
            if idx != 0:
                r = n.rfind('-')
                if r != -1:
                    n = n[:r]
                name_n = '%s-%s%s' % (n, idx, e)
            else:
                name_n = '%s%s' % (n, e)
            return get_a_valid_dpath(tmpdir, name_n, idx+1)
        else:
            return dpath

    sub_dir = time.strftime("%Y-%m-%d", time.localtime())
    today_tmpdir = os.path.join(WEBSERVER_IMAGE_DIR, sub_dir)
    if check_unique == True:
        dest_dir = get_a_valid_dpath(today_tmpdir, hex_dir)
    else:
        dest_dir = os.path.join(today_tmpdir, hex_dir)

    sub_dir = dest_dir[len(WEBSERVER_DOC_DIR):]
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    shutil.copy2(img_path, dest_dir)
    url = urljoin(WEBSERVER_IMAGE_HOST,
                  os.path.join(sub_dir, os.path.basename(img_path)))
    return url

class WeixinClassifier(Classifier):
    def __init__(self):
        Classifier.__init__(self)
        self.name = 'weixin'
        self.domain_list = ['http://mp.weixin.qq.com', ]
    def get_name(self):
        return self.name

    def get_class(self, content_obj, url):
        parsed_uri = urlparse(url)
        domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
        if domain in self.domain_list:
            return 'weixin'
        else:
            return False

class WeixinProcessor(Processor):
    def __init__(self):
        Processor.__init__(self)
        self.name = 'weixin'
        self.name_cn = u'微信'
        self.remove_class = ['page-toolbar', ]
        self.remove_name = ['script', ]
        self.clean_tags = {
            'p': [],
            'img': ['src'],
            'div': [],
            }
        self.content = ''
        self.title = ''
        self.first_img = ''

    def get_name(self):
        return self.name

    def _get_content(self, soup):
        ''' Get content from html tags
            and content will extract from it.
        '''
        tag = soup.find('div', class_ = 'page-content')
        if tag.attrs:
            for k, v in tag.attrs.items():
                del tag.attrs[k]
        return tag and tag or ''

    def process(self, soup):
        self.title = soup.title.text
        content = self._get_content(soup)
        if not content:
            self.content = ''
            return False
        # Remove all tag which has class in self.remove_class
        t1 = [ x.extract() for x in content.find_all(class_=lambda b: b in self.remove_class, recursive=True) ]
        # Remove all tag which its name is in self.remove_name
        t2 = [ x.extract() for x in content.find_all(lambda b: b.name in self.remove_name, recursive=True) ]

        def clean_tags(tag):
            if tag.attrs and tag.name in self.clean_tags.keys():
                for k, v in tag.attrs.items():
                    if k not in self.clean_tags[tag.name]:
                        del tag.attrs[k]
        # Clean tags attributes use self.clean_tags
        [ x.extract() for x in content.find_all(clean_tags, recursive=True) ]

        first_img_tag = content.find('img', recursive=True)
        if first_img_tag and first_img_tag.has_attr('src'):
            self.first_img = first_img_tag.attrs['src']
        else:
            self.first_img = ''

        self.content = content
        return True

def get_content_from_url(url):
    postBackData = None
    request = urllib2.Request(url, postBackData, { 'User-Agent' : 'HackOS Robot' })

    try:
        response = urllib2.urlopen(request)
    except urllib2.HTTPError, e:
        logger.error('HTTPError = ' + str(e.code))
    except urllib2.URLError, e:
        logger.error('URLError = ' + str(e.reason))
    except httplib.HTTPException, e:
        logger.error('HTTPException')
    except Exception:
        import traceback
        logger.error('generic exception: ' + traceback.format_exc())

    content = response.read()
    return content

def process_content(content, url):
    classify = Classify(content , url)

    classify.regist_classifier(WeixinClassifier())
    classify.regist_classifier(DefaultClassifier())
    classify.regist_processor(WeixinProcessor())
    classify.regist_processor(DefaultProcessor())

    classify.process()
    processor_name = classify.proc.get_name()
    return processor_name, classify.proc;

class CanNotDownloadException(Exception):
    pass

def upload_file_to_wp(client, filepath):
    # prepare metadata
    name = os.path.basename(filepath)
    img_type = imghdr.what(filepath)
    if img_type is None:
        img_type = 'jpeg'
    data = {
            'name': name,
            'type': 'image/%s' % img_type,  # mimetype
    }

    # read the binary file and let the XMLRPC library encode it into base64
    with open(filepath, 'rb') as img:
            data['bits'] = xmlrpc_client.Binary(img.read())

    response = client.call(media.UploadFile(data))
    # response == {
    #       'id': 6,
    #       'file': 'picture.jpg'
    #       'url': 'http://www.example.com/wp-content/uploads/2012/04/16/picture.jpg',
    #       'type': 'image/jpg',
    # }
    if response and response.has_key('id'):
        attachment_id = response['id']
        return attachment_id
    else:
        return None

def get_img(url, tmpdir, retry=5):
    img_path = None
    for i in xrange(retry):
        img_path = get_img_to_tmpdir(url, tmpdir)
        if img_path:
            break
    else:
        raise CanNotDownloadException('download %s' % first_img)
    return img_path

def post_article(title, content, first_img, author, source_url, source_name, delivery_url, delivery_name, class_, tmpdir):
    client = Client(WP_XMLRPC_URL, WP_XMLRPC_USER, WP_XMLRPC_PASS)

    retry = 5
    if first_img:
        logger.debug('Download image %s' % first_img)
        img_path = get_img(first_img, tmpdir)
        logger.debug('Download article\'s first image to %s' % img_path)

    ret = None
    if first_img:
        for i in xrange(retry):
            ret = upload_file_to_wp(client, img_path)
            if ret:
                break
        else:
            raise CanNotUploadException('upload %s' % img_path)

    attachment_id = ret

    # Download all image file, and put it into static directory in web server,
    # and replace URL in the article content.

    content_obj = BeautifulSoup(content)
    img_tags = content_obj.find_all('img', recursive=True)
    from hashlib import md5
    hex_dir = md5(title.encode('utf-8')).hexdigest()
    for img in img_tags:
        if img and img.has_attr('src'):
            img_path = get_img(img.attrs['src'], tmpdir)
            img_path2 = copy_to_web_server(img_path, hex_dir)
            img.attrs['src'] = img_path2

    post = WordPressPost()
    post.title = title
    post.content = str(content_obj)
    #post.post_status = 'publish'
    if first_img:
        post.thumbnail = attachment_id
    post.terms_names = {
        # TODO: add tags
        #'post_tag': ['tagA', 'another tag'],
        'category': ['Web-Crawler/新闻资讯', ],
    }
    post.custom_fields = []
    post.custom_fields.append({
        'key': 'source_url',
        'value': source_url
    })
    post.custom_fields.append({
        'key': 'source_name',
        'value': source_name
    })
    post.custom_fields.append({
        'key': 'delivery_name',
        'value': delivery_name
    })
    post.custom_fields.append({
        'key': 'delivery_url',
        'value': delivery_url
    })
    post.id = client.call(posts.NewPost(post))

if __name__ == '__main__':
    try:
        url = sys.argv[1]
    except:
        sys.stderr.write("Please input crawler url\n")
        sys.exit(-1)
    ### Get task from database, and determine the task's status is unfinished(0)
    #   That status(1,2,3) represent try execute time, There is an option in
    #   database to limit the retry time.
    id_ = sys.argv[1]

    author = 'testuser'
    class_ = CRAWLER_CLASS
    delivery_url = 'http://weixin.qq.com'
    delivery_name = author
    url = None

    sql = 'select t.*, u.nickname from wordp_task t LEFT JOIN wordp_user u ON \
    (t.uid = u.id) where t.id=%s' % id_
    cur = db.query(sql)
    result = cur.fetchone()
    cur.close()
    if result:
        url = result['param1'].strip()
        author = result['nickname'].strip()
        delivery_name = author
    else:
        logger.warn('Can not get the wordp_task id %s' % id_)

    processor_name, proc = process_content(get_content_from_url(url), url)

    today_tmpdir = os.path.join(tmpdir, time.strftime("%Y-%m-%d", time.localtime()))
    if not os.path.exists(today_tmpdir):
        os.makedirs(today_tmpdir)
    # Notice, please input all parameter use unicode
    post_article(proc.title, str(proc.content), proc.first_img,
            author, url, proc.name_cn, delivery_url, delivery_name, class_, today_tmpdir)

