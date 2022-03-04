import time
from pyRpc import PyRpc
from gamelib.util import get_command as get_command_
from gamelib.util import send_command as send_command_
from gamelib.util import debug_write

def send_command(command):
    debug_write("sending command:", command[0:200])
    send_command_(command)


def get_command():
    response = get_command_()
    debug_write("receiving command:", response[0:200])
    return response


if __name__ == '__main__':
    myRpc = PyRpc("TerminalServer")
    time.sleep(.1)

    myRpc.publishService(send_command)
    myRpc.publishService(get_command)
    myRpc.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        myRpc.stop()
