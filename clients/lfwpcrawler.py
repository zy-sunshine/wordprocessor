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

logger = logging.getLogger('lfwpcrawler')

import dict4ini
configpath = '/etc/wordp.ini'
CONF = dict4ini.DictIni(configpath)

from wordp.modules import User, Task
from wordp.modules import session

tmpdir = CONF.client1.tmpdir

LF_XMLRPC_URL = CONF.client1.lf_xmlrpc_url
LF_XMLRPC_USER = CONF.client1.lf_xmlrpc_user
LF_XMLRPC_PASS = CONF.client1.lf_xmlrpc_pass

FTP_IMG_DIR = CONF.client1.ftp_img_dir
FTP_IMG_HOST = CONF.client1.ftp_img_host
FTP_HOST = CONF.client1.ftp_host
FTP_USER = CONF.client1.ftp_user
FTP_PASS = CONF.client1.ftp_pass

CRAWLER_CLASS = CONF.client1.crawler_class
WEIXIN_TRY_TIME = CONF.weixin.try_time
CLIENT_NAME = CONF.client1.name

class CanNotDownloadException(Exception):
    pass
class CanNotUploadException(Exception):
    pass

def copy_to_web_server(img_paths, hex_dir='pre', check_unique=False):
    '''if <check_unique> is True, we will check whether the directory is exists, or we
    just use the <hex_dir> to store the image.
    RETURN: the file's(image) URL'''
    sub_dir = time.strftime("%Y-%m-%d", time.localtime())
    #dest_dir = os.path.join(today_tmpdir, hex_dir)

    from ftplib import FTP
    ftp = FTP(FTP_HOST, timeout=60)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd(FTP_IMG_DIR)
    if sub_dir not in ftp.nlst():
        ftp.mkd(sub_dir)
    ftp.cwd(sub_dir)

    if hex_dir not in ftp.nlst():
        ftp.mkd(hex_dir)
    ftp.cwd(hex_dir)
    img_host_list = []
    url_root = urljoin(FTP_IMG_HOST,
                  os.path.join(sub_dir, hex_dir))
    logger.debug('Enter passive mode ...')
    ftp.set_pasv(True)
    logger.debug('Enter passive mode success!')
    for img_path in img_paths:
        fname = os.path.basename(img_path)
        i = 0
        while i < 4:
            i+=1
            try:
                logger.debug('Upload image... %s' %img_path)
                ftp.storbinary('STOR %s' % fname, open(img_path, 'rb'))
                logger.debug('Upload image success %s' %img_path)
                img_host_list.append(urljoin(url_root, fname))
                break
            except Exception as e:
                pass
        else:
            raise CanNotUploadException('ftp upload "%s" errmsg: %s' % (img_path, str(e)))

    return img_host_list

class WeixinClassifier(Classifier):
    def __init__(self):
        Classifier.__init__(self)
        self.name = 'weixin'
        self.dog_list = ['http://mp.weixin.qq.com', ]
    def get_name(self):
        return self.name

    def get_class(self, content_obj, url):
        parsed_uri = urlparse(url)
        domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
        if domain in self.dog_list:
            return 'weixin'
        else:
            return False

class WeixinProcessor(Processor):
    def __init__(self):
        Processor.__init__(self)
        self.name = 'weixin'
        self.name_cn = u'微信'
        #self.remove_class = ['page-toolbar', ]
        self.remove_class = []
        self.remove_name = ['script', ]
        self.clean_tags = {
            'p': [],
            'img': ['src'],
            'div': [],
            }
        self.content = ''
        self.title = ''
        self.first_img = ''

        self.img_src_alias_attr = 'data-src'

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

        if self.img_src_alias_attr:
            for x in content.find_all('img', recursive=True):
                if x.has_attr(self.img_src_alias_attr):
                    x.attrs['src']=x.attrs.get(self.img_src_alias_attr)

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
        msg = 'HTTPError = ' + str(e.code)
        logger.error(msg)
        return False, msg
    except urllib2.URLError, e:
        msg = 'URLError = ' + str(e.reason)
        logger.error(msg)
        return False, msg
    except httplib.HTTPException, e:
        msg = 'HTTPException'
        logger.error(msg)
        return False, msg
    except Exception:
        import traceback
        msg = 'generic exception: ' + traceback.format_exc()
        logger.error(msg)
        return False, msg
    else:
        content = response.read()
        return True, content

def process_content(content, url):
    classify = Classify(content , url)

    classify.regist_classifier(WeixinClassifier())
    classify.regist_classifier(DefaultClassifier())
    classify.regist_processor(WeixinProcessor())
    classify.regist_processor(DefaultProcessor())

    classify.process()
    processor_name = classify.proc.get_name()
    return processor_name, classify.proc;

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
    client = Client(LF_XMLRPC_URL, LF_XMLRPC_USER, LF_XMLRPC_PASS)

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
            raise CanNotUploadException('xmlrpc upload %s' % img_path)

    attachment_id = ret

    # Download all image file, and put it into static directory in web server,
    # and replace URL in the article content.

    content_obj = BeautifulSoup(content)
    img_tags = content_obj.find_all('img', recursive=True)
    from hashlib import md5
    hex_dir = md5(title.encode('utf-8')).hexdigest()
    img_paths = []
    img_src_list = []
    for img in img_tags:
        if img and img.has_attr('src'):
            img_path = get_img(img.attrs['src'], tmpdir)
            img_paths.append(img_path)
            img_src_list.append(img.attrs['src'])

    img_host_list = copy_to_web_server(img_paths, hex_dir)
    if len(img_host_list) != len(img_src_list):
        raise CanNotUploadException('ftp upload file length not match, local(%s), remote(%s)' % (len(img_src_list), len(img_host_list)))

    for x in xrange(len(img_src_list)):
        img_src_list[x] = img_host_list[x]

    post = WordPressPost()
    post.title = title
    post.content = str(content_obj)
    #post.post_status = 'publish'
    if first_img:
        post.thumbnail = attachment_id
    post.terms_names = {
        # TODO: add tags
        #'post_tag': ['tagA', 'another tag'],
        'category': ['公社推送', ],
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

def set_task_status_99(id_, redo, status=-99):
    '''Set task status to -99 to lock it'''
    result = session.query(Task).filter(Task.id==id_).with_lockmode('update').all()
    status = redo and 0 or -88

    if result:
        status = redo and 0 or result[0].status

        if (redo or (result[0].status < WEIXIN_TRY_TIME and result[0].status >= 0)):
            if not redo and (result[0].status > 0 and result[0].ret == 0):
                # NOTE: Task has been done, and the result is success, so we
                # just exit
                logger.debug('Task has been done, exit task %s' % id_)
                return sys.exit(0)
            # We locked the item
            try:
                session.query(Task).filter(Task.id==id_).update({Task.status: status,})
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error('Can not update task(%s) status msg: %s' % (id_, str(e)))
                return False, status
        else:
            return False, status

    return True, status

def set_task_ret(id_, status, ret, retmsg):
    result = session.query(Task).filter(Task.id==id_).with_lockmode('update').all()
    if result and result[0].status < WEIXIN_TRY_TIME and result[0].status >= 0:
        # We locked the item
        try:
            session.query(Task).filter(Task.id==id_).update({Task.status: status, Task.ret: ret, Task.retmsg: retmsg})
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error('Can not update task(%s) status msg: %s' % (id_, str(e)))
            return False
    else:
        return False

    return True

g_ret = 0
g_ret_msg = ''
g_id_ = -1
g_oldstatus = -88

def main():
    try:
        url = sys.argv[1]
    except:
        sys.stderr.write("Please input crawler url\n")
        sys.exit(-1)

    if len(sys.argv) > 2 and sys.argv[2].strip() == 'redo':
        redo = True
    else:
        redo = False

    ### Get task from database, and determine the task's status is unfinished(0)
    #   That status(1,2,3) represent try execute time, There is an option in
    #   database to limit the retry time.
    global g_id_
    global g_ret
    global g_ret_msg
    global g_oldstatus
    g_id_ = int(sys.argv[1].strip())
    g_ret = 0
    g_ret_msg = ''
    g_oldstatus = -1

    author = 'testuser'
    class_ = CRAWLER_CLASS
    delivery_url = 'http://weixin.qq.com'
    delivery_name = author
    url = None

    ret = session.query(Task).filter(Task.id == g_id_).scalar()
    if ret and ret.client_name != CLIENT_NAME:
        logger.error('We got a error request, let me do task %s, but this is %s\'s task' % (g_id_, ret.client_name))
        # NOTE: we do not record this error in database, just exit.
        sys.exit(0)

    #sql = 'UPDATE wordp_task SET status=%s where id=%s' % (-99, g_id_) # status(-99) indicate that we are processing
    ret, g_oldstatus = set_task_status_99(g_id_, redo)
    if not ret:
        g_ret_msg = 'Get task(%s) failed' % g_id_
        logger.error(g_ret_msg)
        g_ret = -3
        return

    #sql = 'select t.*, u.nickname from wordp_task t LEFT JOIN wordp_user u ON \
    #(t.uid = u.id) where t.id=%s' % g_id_
    result = session.query(Task, User.nickname).join(User, User.id == Task.uid).filter(Task.id==g_id_).all()
    if result:
        url = result[0].Task.param1.strip()
        author = result[0].nickname.strip()
        delivery_name = author
    else:
        g_ret_msg = 'Can not get the task %s' % g_id_
        logger.error(g_ret_msg)
        g_ret = -3
        return

    logger.debug('Get task(%s) information author(%s) url(%s)' % (g_id_, author, url))

    try:
        ret, msg = get_content_from_url(url)
        if not ret:
            g_ret_msg = msg
            g_ret = -1
            return

        processor_name, proc = process_content(msg, url)

        today_tmpdir = os.path.join(tmpdir, time.strftime("%Y-%m-%d", time.localtime()))
        if not os.path.exists(today_tmpdir):
            os.makedirs(today_tmpdir)
        # Notice, please input all parameter use unicode
        try:
            post_article(proc.title, str(proc.content), proc.first_img,
                author, url, proc.name_cn, delivery_url, delivery_name, class_, today_tmpdir)
            g_ret = 0
            return
        except CanNotUploadException as e:
            g_ret = -2
            g_ret_msg = 'CanNotUploadException %s' % str(e)
            return

    except Exception as e:
        import traceback
        msg = 'generic exception: ' + traceback.format_exc()
        logger.error(msg)
        g_ret_msg = 'Unknown error %s \nError: %s' % (url, str(e))
        logger.error(g_ret_msg)
        g_ret = -4
        return


if __name__ == '__main__':
    main()
    if g_ret == -3: # error not caused by get taks error
        set_task_ret(g_id_, g_oldstatus, g_ret, g_ret_msg)
    else:
        set_task_ret(g_id_, g_oldstatus+1, g_ret, g_ret_msg)

    logger.debug('Return with ret %s ret_msg %s' % (g_ret, g_ret_msg))
    sys.exit(g_ret)

