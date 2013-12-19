import zmq

context = zmq.Context()
client = context.socket(zmq.REQ)
#client.connect("tcp://localhost:5555")
client.connect("ipc:///tmp/wordp.client.ipc")

for request in range(1,2):
    client.send("Hello")
    message = client.recv()
    print "Received reply ", request, "[", message, "]"

client.setsockopt(zmq.LINGER, 0)
client.close()

client = context.socket(zmq.REQ)
client.connect("ipc:///tmp/wordp.server.exit.ipc")
client.send("EXIT")

