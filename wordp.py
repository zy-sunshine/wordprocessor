"""

   Multithreaded Hello World server

   Author: Guillaume Aubert (gaubert) <guillaume(dot)aubert(at)gmail(dot)com>

"""
import os, sys
import time
import threading
import zmq
import multiprocessing
from commandwrapper import WrapCommand

USE_MULTI_PROCESS = False

#url_worker = "inproc://workers"
url_worker = "ipc:///tmp/_wordp.worker.ipc"
#url_client = "tcp://*:5555"
url_client = "ipc:///tmp/wordp.client.ipc"
url_exitsocket = "ipc:///tmp/wordp.server.exit.ipc"
url_worker_cmd = "ipc:///tmp/_wordp.worker.cmd.ipc"

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(CUR_DIR, 'clients-exe.conf')
monitor_files = [config_file, ]
if not os.path.exists(config_file):
    raise Exception("Please configure your config file %s" % config_file)

WORKER_NUM = 2
thread_num_of_worker = 4
worker_exe_path = None
def reload_config():
    global worker_exe_path
    with open(config_file) as f:
        worker_exe_path = f.read().strip()
reload_config()

def worker_routine(context, idx):
    """ Worker routine """
    global worker_exe_path
    # Socket to talk to dispatcher
    socket0 = context.socket(zmq.REP)

    socket0.connect(url_worker)
    worker_id = 'Worker-%s' % idx
    socket0.setsockopt(zmq.IDENTITY, worker_id)

    socket_exit = context.socket(zmq.SUB)
    socket_exit.connect(url_worker_cmd)
    socket_exit.setsockopt(zmq.SUBSCRIBE, '')
    poller = zmq.Poller()
    poller.register(socket0, zmq.POLLIN)
    poller.register(socket_exit, zmq.POLLIN)

    from threadpool import ThreadPool, WorkRequest
    thread_pool = ThreadPool(thread_num_of_worker)

    def thread_work(id_):
        # create a process to execute the worker_exe
        # TODO: add execute timeout
        _cmd = '%s %s' % (worker_exe_path, id_)
        cmd = WrapCommand(_cmd)
        cmd.start()
        print 'Start command start %s' % _cmd
        cmd.join()
        print 'Start command end %s' % _cmd
        return cmd.returncode

    def thread_work_cb(request, ret):
        if ret == 0:
            # run cmd process in thread success
            print "execute %s success %s" % (worker_exe_path, ret)
        else:
            print "execute %s failed %s" % (worker_exe_path, ret)

    def handle_exception(request, exc_info):
        if not isinstance(exc_info, tuple):
            # Something is seriously wrong...
            print request
            print exc_info
            raise SystemExit
        print "**** Exception occured in request #%s: %s" % \
                (request.requestID, exc_info)

    def register_task(id_):
        request = WorkRequest(thread_work, (id_, ), {}, callback=thread_work_cb,
                    exc_callback=handle_exception)
        thread_pool.putRequest(request)

    while True:
        events = dict(poller.poll(2000))
        if events.get(socket0) == zmq.POLLIN:
            # Deal with message
            msg  = socket0.recv()

            print("Received request: [%s]\n" % (msg))
            register_task(msg)

            #send reply back to client
            socket0.send("OK")
        if events.get(socket_exit) == zmq.POLLIN:
            cmd = socket_exit.recv()
            print '%s CMD %s' % (worker_id, cmd)
            sys.stdout.flush()
            if cmd == 'EXIT':
                break
            elif cmd == 'CONFIG_CHANGED':
                reload_config()
            else:
                pass
    thread_pool.close()
    thread_pool.join()
    socket0.close()
    socket_exit.close()

class BrokerProcess(multiprocessing.Process):

    def __init__(self, ):
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()

    def run(self):
        """ server routine """

        # Prepare our context and sockets
        context = zmq.Context()
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
        context.term()

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
                # TODO: send method have exceptional state
                # 'send' operations on the socket shall block until
                # the exceptional state ends or at least one peer
                # becomes available for sending; messages are not discarded.
                # http://methodmissing.github.io/rbczmq/ZMQ/Socket/Dealer.html
                # NOTE:!! Tested this status, the send_multipart would not block
                #    The message send out into socket buffer,
                #    to wait client connected, and then send out.
                osocket.send_multipart(isocket.recv_multipart())
            if osocket in events:
                isocket.send_multipart(osocket.recv_multipart())

_mtimes = {}
_win = (sys.platform == "win32")

def file_changed(monitor_files):
    global _mtimes, _win
    for fn in monitor_files:
        stat = os.stat(fn)
        mtime = stat.st_mtime
        if _win:
            mtime -= stat.st_ctime
        if fn not in _mtimes:
            _mtimes[fn] = mtime
            continue
        if mtime != _mtimes[fn]:
            _mtimes = {}
            return True
    return False

def main():

    context = zmq.Context()

    process = BrokerProcess()
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

    workers_cmd_pub = context.socket(zmq.PUB)
    workers_cmd_pub.bind(url_worker_cmd)
    time.sleep(0.5)
    workers_cmd_pub.send('HELLO')

    while True:
        events = dict(poller.poll(2000))
        # check config files change, and notify clients
        if file_changed(monitor_files):
            workers_cmd_pub.send('CONFIG_CHANGED')

        if events.get(exitsocket) == zmq.POLLIN:
            msg = exitsocket.recv()
            exitsocket.send("OK")
            break
    print "Start exit form main ..."
    print "Exit BrokerProcess ..."
    process.shutdown()
    process.join()

    workers_cmd_pub.send('EXIT')

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
    workers_cmd_pub.close()
    exitsocket.close()
    context.term()
    print 'context term over'

if __name__ == "__main__":
    main()

