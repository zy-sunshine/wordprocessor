#!/usr/bin/python
import zmq

context = zmq.Context()

client = context.socket(zmq.REQ)
ret = client.connect("ipc:///tmp/wordp.server.exit.ipc")
if ret:
    client.send("EXIT")

