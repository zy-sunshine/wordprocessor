import sys
import zmq

import dict4ini
from django.conf import settings
CONF = dict4ini.DictIni(settings.CONFIG_PATH)

REQUEST_TIMEOUT = int(CONF.weixin.zmq_req_request_timeout)
REQUEST_RETRIES = int(CONF.weixin.zmq_req_retry_time)
SERVER_ENDPOINT = CONF.weixin.zmq_req_server_url

import logging
# Get an instance of a logger
logger = logging.getLogger()

def send_message_to_task_manager(worker_name, msg):
    context = zmq.Context()

    logger.info("I: Connecting to server %s..." % SERVER_ENDPOINT)
    client = context.socket(zmq.REQ)
    client.connect(SERVER_ENDPOINT)

    poll = zmq.Poller()
    poll.register(client, zmq.POLLIN)

    retries_left = REQUEST_RETRIES
    ret = True
    while retries_left:
        request = '%s %s' % (worker_name, msg)
        logger.info("I: Sending (%s)" % request)
        try:
            client.send(request)
        except Exception as e:
            # send exception, we should exit
            logger.error(str(e))
            logger.error("E: Server seems to be offline, abandoning")
            ret = False
            break

        socks = dict(poll.poll(REQUEST_TIMEOUT))
        if socks.get(client) == zmq.POLLIN:
            reply = client.recv()
            if not reply:
                ret = False
                break
            if reply == 'OK':
                # success
                client.close()
                ret = True
                logger.info("I: Server replied OK (%s)" % reply)
                break
            else:
                ret = False
                client.close()
                logger.error("E: Malformed reply from server: %s" % reply)
                break

        else:
            logger.warn("W: No response from server, retrying...")
            # Socket is confused. Close and remove it.
            client.setsockopt(zmq.LINGER, 0)
            client.close()
            poll.unregister(client)
            retries_left -= 1
            if retries_left == 0:
                logger.error("E: Server seems to be offline, abandoning")
                ret = False
                break
            logger.info("I: Reconnecting and resending (%s)" % request)
            # Create new connection
            #client = context.socket(zmq.REQ)
            #client.connect(SERVER_ENDPOINT)
            #poll.register(client, zmq.POLLIN)
            #client.send(request)

    logger.debug('Start close zmq context')
    context.term()
    logger.debug('Return from zmqclient %s' % ret)
    return ret

