#!/usr/bin/env python3

import tornado.web
import tornado.websocket
import os.path
import uuid
import json

from hotqueue import HotQueue

from tornado.options import define, options, parse_command_line

define("port", default=8080, help="run on the given port", type=int)
define("debug", default=True, help="run in debug mode")

queue = HotQueue("text-updates")


class QueueWebSocket(tornado.websocket.WebSocketHandler):
    def open(self):
        self.client_id = uuid.uuid4()

    def on_message(self, message):
        data = json.loads(message)
        data["client_id"] = self.client_id
        queue.put(data)

    def on_close(self):
        pass

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

def main():
    parse_command_line()
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/realtime/", QueueWebSocket),
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        debug=options.debug,
    )
    app.listen(options.port, "0.0.0.0")
    print("Server available at http://0.0.0.0:{}/".format(options.port))
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
