import inspect
import hashlib
import logging

from .parser import parse_user_msg
from .reply import create_reply
from .utils import py3k

__all__ = ['BaseRoBot']


class BaseRoBot(object):
    message_types = ['subscribe', 'unsubscribe', 'click',  # event
                     'text', 'image', 'link', 'location', 'voice']

    def __init__(self, token=None, logger=None, enable_session=False,
                 session_storage=None):
        self._handlers = dict((k, []) for k in self.message_types)
        self._handlers['all'] = []
        self.token = token
        if logger is None:
            logger = logging.getLogger()
        self.logger = logger

        if enable_session and session_storage is None:
            from .session.filestorage import FileStorage
            session_storage = FileStorage()
        self.session_storage = session_storage

    def handler(self, f):
        """
        Decorator to add a handler function for every messages
        """
        self.add_handler(f, type='all')
        return f

    def text(self, f):
        """
        Decorator to add a handler function for ``text`` messages
        """
        self.add_handler(f, type='text')
        return f

    def image(self, f):
        """
        Decorator to add a handler function for ``image`` messages
        """
        self.add_handler(f, type='image')
        return f

    def location(self, f):
        """
        Decorator to add a handler function for ``location`` messages
        """
        self.add_handler(f, type='location')
        return f

    def link(self, f):
        """
        Decorator to add a handler function for ``link`` messages
        """
        self.add_handler(f, type='link')
        return f

    def subscribe(self, f):
        """
        Decorator to add a handler function for ``subscribe event`` messages
        """
        self.add_handler(f, type='subscribe')

    def unsubscribe(self, f):
        """
        Decorator to add a handler function for ``unsubscribe event`` messages
        """
        self.add_handler(f, type='unsubscribe')

    def click(self, f):
        """
        Decorator to add a handler function for ``click`` messages
        """
        self.add_handler(f, type='click')

    def voice(self, f):
        """
        Decorator to add a handler function for ``voice`` messages
        """
        self.add_handler(f, type='voice')

    def add_handler(self, func, type='all'):
        """
        Add a handler function for messages of given type.
        """
        if not inspect.isfunction(func):
            raise TypeError
        self._handlers[type].append(func)

    def get_handlers(self, type):
        return self._handlers[type] + self._handlers['all']

    def get_reply(self, message):
        """
        Return the raw xml reply for the given message.
        """
        session_storage = self.session_storage
        if session_storage:
            if hasattr(message, "FromUserName"):
                _id = message.FromUserName
                session = session_storage[_id]
            else:
                _id = None
                session = None
        handlers = self.get_handlers(message.MsgType)
        try:
            for handler in handlers:
                if session_storage:
                    reply = handler(message, session)
                    if _id:
                        session_storage[_id] = session
                else:
                    reply = handler(message)
                if reply:
                    return reply
        except:
            self.logger.warning("Catch an exception", exc_info=True)

    def check_signature(self, timestamp, nonce, signature):
        if not (timestamp and nonce and signature):
            return False
        sign = [self.token, timestamp, nonce]
        sign.sort()
        sign = ''.join(sign)
        if py3k:
            sign = sign.encode()
        sign = hashlib.sha1(sign).hexdigest()
        return sign == signature


