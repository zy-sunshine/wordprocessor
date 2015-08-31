#encoding=utf-8
import sys
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
import datetime, time
from base import BaseRequestHandler

import werobot
import hashlib
from werobot.parser import parse_user_msg
from werobot.replies import create_reply
py3k = sys.version_info >= (3, 0, 0)

import logging
# Get an instance of a logger
logger = logging.getLogger()

from werobot.robot import BaseRoBot
import urllib2
import json

import dict4ini
from django.conf import settings
from django.utils.translation import ugettext as _
from myweixin.utils.zmqclient import send_message_to_task_manager

from wordp.modules import User, Option, Task
from wordp.modules import session

CONF = dict4ini.DictIni(settings.CONFIG_PATH)
WEIXIN_TOKEN = CONF.weixin.token
WEIXIN_APPID = CONF.weixin.appid
WEIXIN_SECRET = CONF.weixin.secret
WEIXIN_RETRY_TIME = CONF.weixin.retry_time
CLIENT_NAME_LIST = CONF.weixin.client_name_list
ADMIN_MAIL = CONF.weixin.admin_mail

class WeRoBot(BaseRoBot):
    def __init__(self, token, request, response):
        BaseRoBot.__init__(self, token=token, logger=logger, enable_session=False, session_storage=None)
        self.request = request
        self.response = response
        self.debug = False

    def GET(self):
        return self.POST()
        method = getattr(self.request, self.request.method)
        if not self.debug and not self.request.GET.get('debug'):
            if not self.check_signature(
                self.request.GET.get('timestamp'),
                self.request.GET.get('nonce'),
                self.request.GET.get('signature'),
            ):
                logger.error('Can not handle request GET (please check signature)')
                return False # 403 Error
            else:
                logger.debug('Check signature pass(GET)')

        return method.get('echostr')

    def POST(self):
        method = getattr(self.request, self.request.method)
        if not self.debug and not self.request.GET.get('debug'):
            logger.debug('timestamp: %s, nonce: %s, signature: %s' % (
                self.request.GET.get('timestamp'),
                self.request.GET.get('nonce'),
                self.request.GET.get('signature'),
            ))
            if not self.check_signature(
                self.request.GET.get('timestamp'),
                self.request.GET.get('nonce'),
                self.request.GET.get('signature'),
            ):
                logger.error('Can not handle request POST (please check signature)')
                return False # 403 Error
            else:
                logger.debug('Check signature pass(POST)')

        body = self.request.read().decode('utf-8')
        try:
            message = parse_user_msg(body)
        except Exception as e:
            logger.error('Can not parse body: "%s"' % body)
        else:
            logger.debug('parse body success')
        #logging.debug("Receive message %s" % message.MsgId)

        # Find a user from database, if not exists pull user information form weixin
        #sql = u'select id from wordp_user where openid = "%s"' % message.source
        #cur = db.query(sql)
        #result=cur.fetchone()
        #logger.debug('get user info from database %s' % str(result))
        # !!! Because we can not get user information from weixin server if we
        # not use TEST WEIXIN PUBLIC ACCOUNT.. so we should let user send
        # it's name manually, oops
        #if not result:
        #    #logger.debug('Can not find user info in database, request it from weixin server!')
        #    self.get_user_info(message.source)


        #cursor.execute('INSERT INTO wordp_task (uid, status, param1, add_time) VALUES()'
        reply = self.get_reply(message)
        print reply
        if not reply:
            self.logger.warning("No handler responded message %s"
                                % message)
            return _('Can not get the reply from messages handler. This is a \
debug message.')
        self.response['Content-Type'] = 'application/xml'
        return create_reply(reply, message=message)

    ### Get user information is not support now in weixin, so we should wait some
    #     day use it, and change the database option to sqlalchemy.
    #def get_user_info(self, openid):
    #    #https://api.weixin.qq.com/cgi-bin/user/info?access_token=ACCESS_TOKEN&openid=OPENID
    #    token = self.get_token()
    #    req = urllib2.Request("https://api.weixin.qq.com/cgi-bin/user/info?access_token=%s&openid=%s" % (token, openid))
    #    try:
    #        f = urllib2.urlopen(req)
    #    except:
    #        return None
    #    else:
    #        jsonstr = f.read().decode('utf-8')
    #    jsonobj = json.loads(jsonstr)
    #    if jsonobj.has_key('errcode'):
    #        logger.error('Can not get user info errcode: %s errmsg: %s' % (jsonobj.get('errcode'), jsonobj.get('errmsg')))
    #        return None
    #    sql = u'INSERT INTO wordp_user (openid, nickname, sex, groupid, add_time, misc) VALUES ("%s", "%s", %s, %s, %s, \'%s\')' \
    #            % (jsonobj.get('openid'), jsonobj.get('nickname'), jsonobj.get('sex'), 0, int(time.time()), jsonstr)
    #    try:
    #        cur = db.query(sql)
    #        db.conn.commit()
    #        cur.close()
    #    except:
    #        db.conn.rollback()
    #        return None
    #    else:
    #        return jsonobj

    #def get_token(self):
    #    #https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET
    #    sql = u'select option_value from wordp_options where option_name="%s"' % 'access_token'
    #    cur = db.query(sql)
    #    result=cur.fetchone()
    #    if not result:
    #        return self._update_token()
    #    token = result['option_value']
    #    sql = u'select option_value from wordp_options where option_name = "%s"' % 'access_token_ctime'
    #    cur = db.query(sql, cur)
    #    result = cur.fetchone()
    #    cur.close()
    #    if not result:
    #        return self._update_token()
    #    ctime = result['option_value']

    #    if int(time.time()) - int(ctime) + 60 > 7200:
    #        return self._update_token()
    #    else:
    #        return token

    #def _update_token(self):
    #    req = urllib2.Request("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s"
    #            % (WEIXIN_APPID, WEIXIN_SECRET))
    #    try:
    #        f = urllib2.urlopen(req)
    #    except:
    #        return None
    #    else:
    #        token = f.read()
    #    # update into db
    #    token = json.loads(token)

    #    sql = u'UPDATE `wordp_options` SET `option_value`="%s" WHERE `option_name`="%s"' % (str(token['access_token']), 'access_token')
    #    try:
    #        cur = db.query(sql)
    #    except:
    #        sql = u'INSERT INTO wordp_options (option_name, option_value) VALUES ( "%s", "%s")' % ('access_token', token['access_token'])
    #        ret, cur = db.query(sql, cur)
    #    else:
    #        pass

    #    sql = u'UPDATE wordp_options SET option_value="%s" WHERE option_name="%s"' % (int(time.time()), 'access_token_ctime')
    #    try:
    #        cur = db.query(sql, cur)
    #    except:
    #        sql = u'INSERT INTO wordp_options (option_name, option_value) VALUES ( "%s", "%s")' % ('access_token_ctime', int(time.time()))
    #        cur = db.query(sql, cur)
    #    else:
    #        pass

    #    try:
    #        db.conn.commit()
    #    except:
    #        db.rollback()

    #    return token['access_token']


    #def test(self):
    #    self.get_user_info('o3bWXtyTB18MO5BnILDmwFvPPIjI')

class Home(BaseRequestHandler):
    def __init__(self):
        BaseRequestHandler.__init__(self)
        self.token = WEIXIN_TOKEN

    def initialize(self, request):
        #BaseRequestHandler.initialize(request)
        self.werobot = WeRoBot(self.token, self.request, self.response)
        self.werobot.text(Home.text)

    @staticmethod
    def send_task_request(client_name, taskid):
        logger.debug('send_task_request %s %s' % (client_name, taskid))
        return send_message_to_task_manager(client_name, taskid)

    @staticmethod
    def assign_content_to_client(user_id, user_groupid, client_name, content):
        # Save url to taks list in database
        # Frist, we should find url in database, which user insert in 7
        # days, if find same url, we reject the request.(There have some
        # `status` and `ret` check)
        #sql = 'SELECT * from wordp_task where param1=\'%s\' and add_time>=%s \
        #and uid=%s' \
        #% (content, int(time.time())-3600*24*7, user_id)
        t_before_7_day = int(time.time())-3600*24*7
        result = session.query(Task).filter(Task.uid==user_id).filter(Task.add_time>=t_before_7_day).filter(Task.param1==content).filter(Task.client_name==client_name).scalar()
        if result:
            def common_resend():
                # NOTE: send signal to clients
                ret = Home.send_task_request(client_name, result.id)
                if ret:
                    return _('Your request have some error(status%s ret%s), \
and we have send the process request') % (result.status, result.ret)
                else:
                    return _('Can not deal with your request, (Something about client manager \
error), please inform administrator %s. Thanks.') % ADMIN_MAIL

            if (result.status == 0):
                return common_resend()

            elif (result.status > 0 and result.status < WEIXIN_RETRY_TIME):
                # Resend the request
                if result.ret != 0:
                    return common_resend()
                else:
                    # process successfully
                    return _('''Do not submit request duplicated(status%s ret%s), your \
request been processed successfully.''') % (result.status, result.ret)
            elif (result.status >= WEIXIN_RETRY_TIME):
                # The task has been processed out of retry time, and we
                # will not process it again
                if result.status == -99:
                    return _('''Your request is being processed, please wait.''')
                if result.ret != 0:
                    return _('''Your request has been processed, but not \
success, is %s, please contact with administrator %s''') % (result.ret, ADMIN_MAIL)
                else:
                    return _('''Do not submit request duplicated(status%s ret%s), your \
request been processed successfully.''') % (result.status, result.ret)

            return _('''ERROR, duplicated URL.''')

        # This is a new URL request, we should insert it into task list.
        #sql = 'INSERT INTO wordp_task (uid, status, param1, param2, param3, \
        #add_time) VALUES (%s, %s, \'%s\', \'%s\', \'%s\', %s)' % (user_id, 0,
        #content, '', '', int(time.time()))
        try:
            task = Task(uid=user_id, status=0, param1=content, param2='', 
                        param3='', add_time=int(time.time()), ret=0, retmsg='', client_name=client_name)
            session.add(task)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error('Can not insert URL into database %s' % content)
            logger.error(str(e))
            return _('Can not deal with your request, (Something about database \
error), please inform administrator %s. Thanks.') % ADMIN_MAIL
        else:
            # NOTE: send signal to clients
            ret = Home.send_task_request(client_name, task.id)
            if ret:
                return _('We have received your URL request, please wait to processing (taskid%s).') % task.id
            else:
                return _('Can not deal with your request, (Something about client manager \
error), please inform administrator %s. Thanks.') % ADMIN_MAIL

    @staticmethod
    def text(message):
        logger.debug(str(message))
        # Find uesr information from database, if not exists, ask user to send to me
        logger.debug(dir(message))
        logger.debug(message.source)
        logger.debug(message.target)
        result = session.query(User).filter(User.openid == message.source).scalar()
        #sql = u'select id, openid from wordp_user where openid = "%s"' % message.source
        logger.debug('get user info from database %s' % str(result))
        # This text will be insert into database, so we must escape some
        # special character.
        #import MySQLdb
        #content = MySQLdb.escape_string(message.Content)
        content = message.content
        if not result:
            if content.startswith('id:'):
                # insert uesr info into database, and send hello message.
                ret = Home.insert_user_info(message.source, content[len('id:'):].strip())
                if ret is not None:
                    return _('''Success insert your information, and you are at \
default group to post articles to Linuxfans, and if you want to \
post articles to HackOS, please contact with administrator %s''') % ADMIN_MAIL
                else:
                    return _('''Can not insert your information, please contact \
with administrator %s''') % ADMIN_MAIL
            else:
                return ('''We have no information about you, please SEND me your \
information at least your username with format id:<username> \
thanks.''')
        user_id = result.id
        user_groupid = result.groupid
        ## Now we can insert the url into task list
        # First we should check the url format
        from django.core.validators import URLValidator
        from django.core.exceptions import ValidationError
        val = URLValidator()
        try:
            val(content)
        except ValidationError, e:
            return _('''Your URL format is malformed, please give me a correct URL.''')
        else:
            def get_client_conf_by_name(client_name):
                for client_id in CONF.clients.clients_list:
                    client_conf = getattr(CONF, client_id)
                    if client_name == client_conf.name:
                        return client_conf
            retmsg = ''

            for client_name in CLIENT_NAME_LIST:
                client_conf = get_client_conf_by_name(client_name)
                if user_groupid in client_conf.group_id_list:
                    _retmsg = Home.assign_content_to_client(user_id, user_groupid, client_name, content)
                    if hasattr(client_conf, 'hide_message') and client_conf.hide_message == True:
                        pass
                    else:
                        retmsg = '%s\n%s' % (retmsg, _retmsg)
            return retmsg.strip()

        return _(''' We have received your message, Thanks! (Nothing will happend) ''')

    @staticmethod
    def insert_user_info(id_, name, sex=0, jsonstr=''):
        #sql = u'INSERT INTO wordp_user (openid, nickname, sex, groupid, add_time, misc) VALUES ("%s", "%s", %s, %s, %s, \'%s\')' \
        #        % (id_, name, sex, 0, int(time.time()), jsonstr)
        user = User(openid=id_, nickname=name, sex=sex, groupid=0, add_time=int(time.time()), misc=jsonstr)
        session.add(user)
        session.commit()
        return name

    def GET(self):
        # do the request logging
        #if self.param('Content'):
        #    # do some Content Type check
        #    #self.do_content_check()
        #    pass
        #else:
        #    # verify_signature
        #    self.do_verify_signature()
        ret = self.werobot.GET()
        if ret:
            self.write(ret)
        else:
            # 403 error
            raise PermissionDenied

    def POST(self):
        ret = self.werobot.POST()
        if ret:
            self.write(ret)
        else:
            raise PermissionDenied
        #if self.param('Content'):
        #    self.do_content_check()

    def do_verify_signature(self):
        # register domain on mp weixin platform
        timestamp = self.param('timestamp')
        nonce = self.param('nonce')
        signature = self.param('signature')
        sign = [self.token, timestamp, nonce]
        sign.sort()
        sign = ''.join(sign)
        if sign:
            if py3k:
                sign = sign.encode()
            sign = hashlib.sha1(sign).hexdigest()
            if sign == signature:
                self.write(self.param('echostr'))
            else:
                logger.error('do_verify_signature failed')

    def do_content_check(self):
        params = {
            'ToUserName' : self.param('ToUserName'),
            'FromUserName' : self.param('FromUserName'),
            'CreateTime' : self.param('CreateTime'),
            'Content' : self.param('Content'),
            'MsgType' : self.param('MsgType'),
            'MsgId' : self.paramlong('MsgId')
        }
        logger.debug(str(params))

testxml = u'''<xml><ToUserName><![CDATA[gh_fe4082a99198]]></ToUserName>
<FromUserName><![CDATA[oZBi2t8uIWLiUcmDl1shYuQOFUE4]]></FromUserName>
<CreateTime>1387823181</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[http://mp.weixin.qq.com/mp/appmsg/show?__biz=MjM5NjAxMzgwMA==&appmsgid=100068372&itemidx=1&sign=768a49de7daf420693fd3be2672f51b2#wechat_redirect]]></Content>
<MsgId>5960655175035689598</MsgId>
</xml>
'''
#<Content><![CDATA[id:sunblackshine]]></Content>

class Test(BaseRequestHandler):
    def GET(self):
        #self.token = WEIXIN_TOKEN
        #self.werobot = WeRoBot(self.token, self.request, self.response)
        #self.werobot.text(Home.text)
        #self.werobot.test()

        #logging.info('This is info info')
        #logging.warning('This is info warning')
        #logging.error('This is info error')
        #logging.debug('This is info debug')
        from werobot.messages import TextMessage
        t = testxml
        self.write(Home.text(parse_user_msg(t)))

rconn = settings.RCONN_QQBOT
class QQView(BaseRequestHandler):
    def GET(self):
        resp = {}
        #self.write(self.request.GET.get('cmd'))
        cmd = self.request.GET.get('cmd')
        if cmd == 'querysc':
            self.getbystemcode(resp, self.request.GET.get('sc'),
                self.request.GET.get('nick'), self.request.GET.get('uid'))
        elif cmd == 'querymsg':
            self.getmsgbyid(resp, self.request.GET.get('id'))

        self.write(json.dumps(resp, ensure_ascii=False).encode('utf8'))

    def getmsgbyid(self, resp, id_):
        curlen = rconn.llen('qqbotmsg')
        if id_ < curlen:
            resp['msglst'] = rconn.lrange('qqbotmsg', id_, curlen)
        else: resp['msglst'] = []

    def getbystemcode(self, resp, stemcode, nick, uid):
        stemcode = stemcode.strip().upper()
        qqmsg = rconn.hget(stemcode, 'qqmsg')
        if qqmsg: resp['qqmsg'] = r'@%s %s %s' % (nick, stemcode, qqmsg)
        else: resp['qqmsg'] = r'@%s 目前没有 %s 的量化信息' % (nick, stemcode)

