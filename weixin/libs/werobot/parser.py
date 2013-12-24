from xml.etree import ElementTree

from .messages import TextMessage, LocationMessage, ImageMessage, EventMessage
from .messages import LinkMessage, VoiceMessage, UnknownMessage, VideoMessage
from .utils import to_unicode


def parse_user_msg(xml):
    """
    Parse xml from wechat server and return an Message
    :param xml: raw xml from wechat server.
    :return: an Message object
    """
    if not xml:
        return

    xml = to_unicode(xml)

    _msg = dict((child.tag, to_unicode(child.text))
                for child in ElementTree.fromstring(xml.encode('utf-8')))

    msg_type = _msg.get('MsgType')
    touser = _msg.get('ToUserName')
    fromuser = _msg.get('FromUserName')
    create_at = int(_msg.get('CreateTime'))
    msg = dict(
        MsgType=msg_type,
        ToUserName=touser,
        FromUserName=fromuser,
        CreateTime=create_at,
        MsgId=_msg.get('MsgId'),
        raw=xml
    )
    if msg_type == 'text':
        msg["Content"] = _msg.get('Content')
        return TextMessage(**msg)
    elif msg_type == 'location':
        msg["Location_X"] = _msg.get('Location_X')
        msg["Location_Y"] = _msg.get('Location_Y')
        msg["Scale"] = int(_msg.get('Scale'))
        msg["Label"] = _msg.get('Label')
        return LocationMessage(**msg)
    elif msg_type == 'image':
        msg["PicUrl"] = _msg.get('PicUrl')
        msg["MediaId"] = _msg.get('MediaId')
        return ImageMessage(**msg)
    elif msg_type == 'event':
        msg["Event"] = _msg.get('Event')
        if msg["Event"] == "click":
            msg["EventKey"] = _msg.get('EventKey')
        return EventMessage(**msg)
    elif msg_type == 'link':
        msg["Title"] = _msg.get('Title')
        msg["Description"] = _msg.get('Description')
        msg["Url"] = _msg.get('Url')
        return LinkMessage(**msg)
    elif msg_type == 'voice':
        msg["MediaId"] = _msg.get('MediaId')
        msg["Format"] = _msg.get('Format')
        #msg["Recognition"] = _msg.get('Recognition')
        return VoiceMessage(**msg)
    elif msg_type == 'video':
        msg['MediaId'] = _msg.get('MediaId')
        msg['ThumbMediaId'] = _msg.get('ThumbMediaId')
        return VideoMessage(**msg)
    else:
        return UnknownMessage(xml)
