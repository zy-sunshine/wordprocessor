"""

   Multithreaded Hello World server

   Author: Guillaume Aubert (gaubert) <guillaume(dot)aubert(at)gmail(dot)com>

"""
import os, sys
import time
import threading
import zmq
import multiprocessing

USE_MULTI_PROCESS = False
WORKER_NUM = 3

#url_worker = "inproc://workers"
url_worker = "ipc:///tmp/_wordp.worker.ipc"
#url_client = "tcp://*:5555"
url_client = "ipc:///tmp/wordp.client.ipc"
url_exitsocket = "ipc:///tmp/wordp.server.exit.ipc"
url_exitworker = "ipc:///tmp/_wordp.worker.exit.ipc"

def worker_routine(context, idx):
    """ Worker routine """

    # Socket to talk to dispatcher
    socket0 = context.socket(zmq.REP)

    socket0.connect(url_worker)
    worker_id = 'Worker-%s' % idx
    socket0.setsockopt(zmq.IDENTITY, worker_id)

    socket_exit = context.socket(zmq.SUB)
    socket_exit.connect(url_exitworker)
    socket_exit.setsockopt(zmq.SUBSCRIBE, '')
    poller = zmq.Poller()
    poller.register(socket0, zmq.POLLIN)
    poller.register(socket_exit, zmq.POLLIN)
    while True:
        events = dict(poller.poll(2000))
        if events.get(socket0) == zmq.POLLIN:
            # Deal with message
            msg  = socket0.recv()

            print("Received request: [%s]\n" % (msg))

            # do some 'work'
            time.sleep(1)

            #send reply back to client
            socket0.send("OK")
        if events.get(socket_exit) == zmq.POLLIN:
            cmd = socket_exit.recv()
            print '%s CMD %s' % (worker_id, cmd)
            sys.stdout.flush()
            if cmd == 'EXIT':
                break
            else:
                pass
    socket0.close()
    socket_exit.close()

class BrokerProcess(multiprocessing.Process):

    def __init__(self, context):
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()
        self.context = context

    def run(self):
        """ server routine """

        # Prepare our context and sockets
        context = self.context
        # Socket to talk to clients
        clients = context.socket(zmq.ROUTER)
        clients.bind(url_client)

        # Socket to talk to workers
        workers = context.socket(zmq.DEALER)
        workers.bind(url_worker)

        print "Start Router <--> Dealer mode"
        ###!!! use my device function from green.device
        self.green_device(zmq.QUEUE, clients, workers)

        # Send exit signal to all workers
        print "Send exit signal to all workers"

        print "You exited!"

        clients.close()
        workers.close()

    def shutdown(self):
        print "Shutdown initiated"
        self.exit.set()

    def green_device(self, device_type, isocket, osocket):
        """Start a zeromq device (gevent-compatible).

        Unlike the true zmq.device, this does not release the GIL.

        Parameters
        ----------
        device_type : (QUEUE, FORWARDER, STREAMER)
            The type of device to start (ignored).
        isocket : Socket
            The Socket instance for the incoming traffic.
        osocket : Socket
            The Socket instance for the outbound traffic.
        """
        p = zmq.Poller()
        if osocket == -1:
            osocket = isocket
        p.register(isocket, zmq.POLLIN)
        p.register(osocket, zmq.POLLIN)

        while not self.exit.is_set():
            events = dict(p.poll(1000))
            if isocket in events:
                osocket.send_multipart(isocket.recv_multipart())
            if osocket in events:
                isocket.send_multipart(osocket.recv_multipart())


def main():

    context = zmq.Context(1)

    process = BrokerProcess(context)
    process.start()

    # Launch pool of worker threads
    process_pool = None
    worker_list = []
    if USE_MULTI_PROCESS:
        print "Use process mode"
        pool_size = WORKER_NUM
        process_pool = multiprocessing.Pool(processes=pool_size)
        for i in xrange(WORKER_NUM):
            process_pool.apply_async(worker_routine, (context, i, ))
    else:
        # To start a worker use:
        print "Use thread mode"
        for i in xrange(WORKER_NUM):
            thread = threading.Thread(target=worker_routine, args=(context, i, ))
            thread.start()
            worker_list.append(thread)

    exitsocket = context.socket(zmq.REP)
    exitsocket.bind(url_exitsocket)
    poller = zmq.Poller()
    poller.register(exitsocket, zmq.POLLIN)

    workers_exit_pub = context.socket(zmq.PUB)
    workers_exit_pub.bind(url_exitworker)
    time.sleep(0.5)
    workers_exit_pub.send('HELLO')

    while True:
        events = dict(poller.poll(2000))
        if events.get(exitsocket) == zmq.POLLIN:
            msg = exitsocket.recv()
            exitsocket.send("OK")
            break
    print "Start exit form main ..."
    print "Exit BrokerProcess ..."
    process.shutdown()
    process.join()

    workers_exit_pub.send('EXIT')

    print "Exit %s ..." % (USE_MULTI_PROCESS and "processes" or "threads")
    if USE_MULTI_PROCESS:
        process_pool.close()
        print "Close pool sucess"
        process_pool.join()
        print "wait process sucesss"
    else:
        for worker in worker_list:
            worker.join()
        print "wait threads success"

    # We never get here but clean up anyhow
    print 'context term...'
    workers_exit_pub.close()
    exitsocket.close()
    context.term()
    print 'context term over'

if __name__ == "__main__":
    main()

