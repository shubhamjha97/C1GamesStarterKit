import time
from xmlrpc.server import SimpleXMLRPCServer
from gamelib.util import get_command as get_command_
from gamelib.util import send_command as send_command_
from gamelib.util import debug_write
import signal
import threading

def send_command(command):
    send_command_(command)

def get_command():
    response = get_command_()
    return response


class KillSupportedRPCServer(SimpleXMLRPCServer):
    def serve_forever(self):
        self.register_function(self.kill)
        self.quit = 0
        while not self.quit:
            self.handle_request()

    def kill(self):
        debug_write("Killing RPC.")
        self.quit = 1
        return 1


class RelayServer:
    def __init__(self):
        address = ('localhost', 50000)
        self.rpc = KillSupportedRPCServer(address, bind_and_activate=False, allow_none=True, logRequests=False)
        self.rpc.allow_reuse_address = True
        debug_write(self.rpc.server_address)
        self.rpc.server_bind()
        self.rpc.server_activate()
        self.rpc.register_function(send_command)
        self.rpc.register_function(get_command)
        signal.signal(signal.SIGINT, self.rpc.kill)
        signal.signal(signal.SIGTERM, self.rpc.kill)
        debug_write("Started RPC.")

    def start(self):
        self.rpc.serve_forever()


if __name__ == '__main__':
    rs = RelayServer()
    try:
        rs.start()
    except:
        rs.rpc.kill()
