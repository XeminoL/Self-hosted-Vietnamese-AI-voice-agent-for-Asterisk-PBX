import socket

AMI_HOST = "127.0.0.1"
AMI_PORT = 5038
AMI_USER = "switchboard"
AMI_SECRET = "local-only"
AMI_TIMEOUT_SECONDS = 3
CALL_FAMILY = "calls"
STAFF_CONTEXT = "internal"
STAFF_EXTENSION = "1002"


class TransferFailed(Exception):
    pass


class ManagerSession:
    def __init__(self):
        self.sock = socket.create_connection((AMI_HOST, AMI_PORT), timeout=AMI_TIMEOUT_SECONDS)
        self.reader = self.sock.makefile("r", encoding="utf-8", newline="\r\n")
        self.reader.readline()

    def send(self, action, **fields):
        lines = [f"Action: {action}"] + [f"{key}: {value}" for key, value in fields.items()]
        self.sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("utf-8"))

    def read_message(self):
        message = {}
        for line in self.reader:
            line = line.rstrip("\r\n")
            if not line:
                if message:
                    return message
                continue
            key, _, value = line.partition(": ")
            message[key] = value
        raise TransferFailed("manager closed the connection")

    def ask(self, action, **fields):
        self.send(action, **fields)
        reply = self.read_message()
        while "Response" not in reply:
            reply = self.read_message()
        if reply.get("Response") != "Success":
            raise TransferFailed(f"{action}: {reply.get('Message', reply)}")
        return reply

    def wait_for_event(self, name):
        while True:
            message = self.read_message()
            if message.get("Event") == name:
                return message

    def close(self):
        try:
            self.send("Logoff")
        finally:
            self.sock.close()


def transfer_to_staff(call_id):
    try:
        session = ManagerSession()
    except OSError as error:
        raise TransferFailed(f"cannot reach the Asterisk manager: {error}")
    try:
        session.ask("Login", Username=AMI_USER, Secret=AMI_SECRET, Events="off")
        session.ask("DBGet", Family=CALL_FAMILY, Key=call_id)
        channel = session.wait_for_event("DBGetResponse").get("Val")
        if not channel:
            raise TransferFailed(f"no channel stored for call {call_id}")
        session.ask("Redirect", Channel=channel, Context=STAFF_CONTEXT,
                    Exten=STAFF_EXTENSION, Priority=1)
        return channel
    except OSError as error:
        raise TransferFailed(str(error))
    finally:
        session.close()
