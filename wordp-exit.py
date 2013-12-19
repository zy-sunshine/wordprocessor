#!/usr/bin/python
import zmq

context = zmq.Context()

client = context.socket(zmq.REQ)
client.connect("ipc:///tmp/wordp.server.exit.ipc")
client.send("EXIT")

