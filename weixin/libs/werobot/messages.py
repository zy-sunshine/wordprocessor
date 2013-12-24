# -*- coding: utf-8 -*-
from .utils import to_unicode

class WeChatMessage(object):
    def __init__(self, **kwargs):
        #if 'MsgId' in kwargs:
        #    self.MsgId = int(kwargs['MsgId'])
        #if 'MsgType' in kwargs:
        #    self.MsgType = kwargs['MsgType']
        #if 'ToUserName' in kwargs:
        #    self.ToUserName = kwargs['ToUserName']
        #if 'FromUserName' in kwargs:
        #    self.FromUserName = kwargs['FromUserName']
        #if 'CreateTime' in kwargs:
        #    self.CreateTime = int(kwargs['CreateTime'])
        #self.raw = kwargs.get('raw', '')
        for k, v in kwargs.items():
            setattr(self, k ,v)
    def __unicode__(self):
        content = u''
        for k, v in vars(self).items():
            print type(k)
            content = u'%sself.%s = %s\n' % (content, to_unicode(k), to_unicode(v))

        return content

class TextMessage(WeChatMessage):
    def __init__(self, **kwargs):
        super(TextMessage, self).__init__(**kwargs)

class ImageMessage(WeChatMessage):
    def __init__(self, **kwargs):
        super(ImageMessage, self).__init__(**kwargs)


class LocationMessage(WeChatMessage):
    def __init__(self, **kwargs):
        super(LocationMessage, self).__init__(**kwargs)
        self.Location_X = float(self.Location_X)
        self.Location_Y = float(self.Location_Y)

class LinkMessage(WeChatMessage):
    def __init__(self, **kwargs):
        super(LinkMessage, self).__init__(**kwargs)


class EventMessage(WeChatMessage):
    def __init__(self, **kwargs):
        super(EventMessage, self).__init__(**kwargs)
        # TODO: event type
        #assert self.MsgType in ['subscribe', 'unsubscribe', 'click']
        #if self.MsgType == 'click':
        #    self.EventKey = kwargs["EventKey"]


class VoiceMessage(WeChatMessage):
    def __init__(self, **kwargs):
        super(VoiceMessage, self).__init__(**kwargs)


class UnknownMessage(WeChatMessage):
    def __init__(self, raw):
        self.raw = raw

class VideoMessage(WeChatMessage):
    def __init__(self, **kwargs):
        super(VideoMessage, self).__init__(**kwargs)

