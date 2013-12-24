import zmq
import threading

def client(idx):
    context = zmq.Context()
    client = context.socket(zmq.REQ)
    #client.connect("tcp://localhost:5555")
    client.connect("ipc:///tmp/wordp.client.ipc")
    poll = zmq.Poller()
    poll.register(client, zmq.POLLIN)
    print 'Start send:'
    client.send('Hello')
    message = client.recv()
    print "Received reply ", idx, "[", message, "]"

    #for request in range(1,2):
    #    client.send("Hello")
    #    message = client.recv()
    #    print "Received reply ", request, "[", message, "]"
    #
thread_pool = []
for idx in xrange(1):
    print 'starting thread %d' % idx
    t = threading.Thread(target=client, args=(idx, ))
    t.start()
    thread_pool.append(t)

for t in thread_pool:
    t.join()

#client.setsockopt(zmq.LINGER, 0)
#client.close()

#client = context.socket(zmq.REQ)
#client.connect("ipc:///tmp/wordp.server.exit.ipc")
#client.send("EXIT")
#
