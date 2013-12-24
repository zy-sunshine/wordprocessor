# -*- coding: utf-8 -*-
import time
from .messages import WeChatMessage
from .utils import isstring, to_unicode


class Article(object):

    def __init__(self, title, description, img, url):
        self.title = title
        self.description = description
        self.img = img
        self.url = url


class WeChatReply(object):

    def __init__(self, message=None, star=False, **kwargs):
        if isinstance(message, WeChatMessage):
            kwargs["FromUserName"] = message.ToUserName
            kwargs["ToUserName"] = message.FromUserName

        assert 'FromUserName' in kwargs
        assert 'ToUserName' in kwargs
        if 'CreateTime' not in kwargs:
            kwargs["CreateTime"] = int(time.time())
        if star:
            kwargs["FuncFlag"] = 1
        else:
            kwargs["FuncFlag"] = 0

        args = dict()
        for k, v in kwargs.items():
            if isstring(v):
                v = to_unicode(v)
            args[k] = v

        self._args = args

    def render(self):
        raise NotImplementedError()


class TextReply(WeChatReply):
    TEMPLATE = to_unicode("""
    <xml>
    <ToUserName><![CDATA[{ToUserName}]]></ToUserName>
    <FromUserName><![CDATA[{FromUserName}]]></FromUserName>
    <CreateTime>{CreateTime}</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[{Content}]]></Content>
    <FuncFlag>{FuncFlag}</FuncFlag>
    </xml>
    """)

    def render(self):
        return TextReply.TEMPLATE.format(**self._args)


class ArticlesReply(WeChatReply):
    TEMPLATE = to_unicode("""
    <xml>
    <ToUserName><![CDATA[{ToUserName}]]></ToUserName>
    <FromUserName><![CDATA[{FromUserName}]]></FromUserName>
    <CreateTime>{CreateTime}</CreateTime>
    <MsgType><![CDATA[news]]></MsgType>
    <Content><![CDATA[{Content}]]></Content>
    <ArticleCount>{ArticleCount}</ArticleCount>
    <Articles>{items}</Articles>
    <FuncFlag>{FuncFlag}</FuncFlag>
    </xml>
    """)

    ITEM_TEMPLATE = to_unicode("""
    <item>
    <Title><![CDATA[{Title}]]></Title>
    <Description><![CDATA[{Description}]]></Description>
    <PicUrl><![CDATA[{PicUrl}]]></PicUrl>
    <Url><![CDATA[{Url}]]></Url>
    </item>
    """)

    def __init__(self, message=None, star=False, **kwargs):
        super(ArticlesReply, self).__init__(message, star, **kwargs)
        self._articles = []

    def add_article(self, article):
        if len(self._articles) >= 10:
            raise AttributeError("Can't add more than 10 articles"
                                 " in an ArticlesReply")
        else:
            self._articles.append(article)

    def render(self):
        items = []
        for article in self._articles:
            items.append(ArticlesReply.ITEM_TEMPLATE.format(
                title=to_unicode(article.title),
                description=to_unicode(article.description),
                img=to_unicode(article.img),
                url=to_unicode(article.url)
            ))
        self._args["items"] = ''.join(items)
        self._args["ArticleCount"] = len(items)
        if "Content" not in self._args:
            self._args["Content"] = ''
        return ArticlesReply.TEMPLATE.format(**self._args)


class MusicReply(WeChatReply):
    TEMPLATE = to_unicode("""
    <xml>
    <ToUserName><![CDATA[{ToUserName}]]></ToUserName>
    <FromUserName><![CDATA[{FromUserName}]]></FromUserName>
    <CreateTime>{CreateTime}</CreateTime>
    <MsgType><![CDATA[music]]></MsgType>
    <Music>
    <Title><![CDATA[{Title}]]></Title>
    <Description><![CDATA[{Description}]]></Description>
    <MusicUrl><![CDATA[{MusicUrl}]]></MusicUrl>
    <HQMusicUrl><![CDATA[{HQMusicUrl}]]></HQMusicUrl>
    <ThumbMediaId><![CDATA[{ThumbMediaId}]]></ThumbMediaId>
    <FuncFlag>{FuncFlag}</FuncFlag>
    </Music>
    </xml>
    """)

    def render(self):
        return MusicReply.TEMPLATE.format(**self._args)


def create_reply(reply, message=None):
    if isinstance(reply, WeChatReply):
        return reply.render()
    elif isstring(reply):
        message = to_unicode(message)
        reply = TextReply(message=message, Content=reply)
        return reply.render()
    elif isinstance(reply, list) and all([len(x) == 4 for x in reply]):
        if len(reply) > 10:
            raise AttributeError("Can't add more than 10 articles"
                                 " in an ArticlesReply")
        r = ArticlesReply(message=message)
        for article in reply:
            article = Article(*article)
            r.add_article(article)
        return r.render()
    elif isinstance(reply, list) and 3 <= len(reply) <= 4:
        if len(reply) == 3:
            # 如果数组长度为3， 那么高质量音乐链接的网址和普通质量的网址相同。
            reply.append(reply[-1])
        title, description, url, hq_url = reply
        reply = MusicReply(
            message=message,
            title=to_unicode(title),
            description=to_unicode(description),
            url=to_unicode(url),
            hq_url=to_unicode(hq_url)
        )
        return reply.render()

