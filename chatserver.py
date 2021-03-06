import socket
import select
import sys

class Server:
    def __init__(self):
        self.host    = ''
        self.port    = 5555
        self.server  = None
        self.inputs  = []
        self.running = True
	self.rooms = {'weebyEngineers':[], 'weebyfungroup': []}

    # Open the Main Server Socket
    def open_socket(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(5)
            self.server.setblocking(0)

            print "Listening on %s:%s" % (self.host, self.port)

        except socket.error, (value, message):
            if self.server:
                self.server.close()
            print "Could not open socket: " + message
            sys.exit(1)

    # Handle a new incomming client connection
    def process_new_client(self):
        print "Incoming Connection"
        c = Client(self.server.accept())
        self.inputs.append(c)
        c.send("-------------------------------------\n")
        c.send("Welcome to the Weeby Chat Server\n")
        c.send("-------------------------------------\n")
        c.send("<= Login Name?\n")
        c.send("=> ")

    # handle room display's
    def displayrooms(self, client):
        client.send("<= Active rooms are: \n")
	for key in self.rooms.keys():
           client.send("<= " + "* " + key + "("+ str(len(self.rooms[key])) +")" + "\n") 
        client.send("<= end of the list. \n")
        client.send("=> ")
    
    # handle room joining's
    def joinroom(self, roomname, client):
        client.send("<= Entering room: " + roomname + "." + "\n")
        # check if room is there
        if roomname in self.rooms.keys():
            users = self.rooms[roomname]
            
            # notify other for new user addition
            for user in users:
		user.send("* new user joined "+ roomname + ": " + user.screenname)
            users.append(client)
            
            # format the message
	    for user in users:
                if user.screenname == client.screenname:
                    client.send("<= " + "* " + str(user.screenname) + " (** This is you )" + "\n")
                else:
                    client.send("<= " + "* " + str(user.screenname) + "\n")
            client.send("<= end of the list. \n")
            client.send("=> ")
	else:
            client.send("<= Wrong room name. \n")
            client.send("=> ")
    
    # handle chat leaving's               
    def leavechat(self, client):
        client.send("<= * User has left chat: " + client.screenname + "(** This is you)" +"\n")
        self.inputs.remove(client)
        client.send("=> ")

    # Process a command received on the local console
    def process_console_command(self, cmd, client):
        print "console: %s" % cmd

        if (cmd == "/quit"):
            self.shutdown()
	elif (cmd.split(' ')[0] == "/join"):
            roomname = cmd.split(' ')[1]
	    self.joinroom(roomname, client)
	elif (cmd == "/leave"):
            self.leavechat(client)
        elif (cmd == "/rooms"):
            self.displayrooms(client)
        else:
            return False
      
    # Process a message from a connected client
    def process_client_message(self, client):
        # Message from a client
        data = client.socket.recv(1024)
        # Use Flag to print message one time
        flag = False
        if data:
            msg = data.rstrip()     # Remove any line return
            
	    if msg:
 		flag = self.process_console_command(msg, client)
            
            if not flag:
		if client.screenname:   
		# This client session has set a screen name
		    self.sendall(msg, client.screenname)            # Send message to all the connected clients
		else:
		    # The client session has not set a screenname
		    # The first message we receive from them should contain the screen name
		    #   (limit 12 characters)
		    for c in self.inputs:
			if isinstance(c, Client):
			    if (msg[:12] == c.screenname):
				client.send("<= Sorry, Name Taken.\n")
				client.send("=> ")
				break
			    else:
				client.screenname = msg[:12]
			        client.send("=> Welcome %s!\n" % client.screenname)
			        client.send("=> ")
			        break

        else:
            # Close the connection with this client
            client.socket.close()
            self.inputs.remove(client)
            print "client disconnecting"

            if client.screenname:
                self.sendall("%s disconnected" % client.screenname)


    # Send a message to all connected clients
    def sendall(self, data, fromuser=None):
        for c in self.inputs:
            if isinstance(c, Client):
                # Only send a message if the user has "logged in" (we have a username)
                if c.screenname:
                    if fromuser:
                        c.send("<= "+ ":".join([fromuser, data]) + "\n")
                        c.send("=> ")
                    else:
                        c.send("<= "+ data + "\n")
                        c.send("=> ")
            elif c == sys.stdin:
                # Print to the local console
                print "%s -> %s" % (fromuser, data)
    

    # Shutdown the server
    def shutdown(self):
        # Close all the connected clients
        for c in self.inputs:
            if isinstance(c, Client):
                self.inputs.remove(c)
                c.send("<= Server Shutting Down!\n")
                c.socket.close()

        # Now close the server socket
        if self.server:
            self.server.close()

        # And stop running
        self.running = False


    # Main Server Loop
    def run(self):
        # Input Sources
        self.inputs = [self.server, sys.stdin]

        self.running = True
        while self.running:

            # Check if any of our input sources have data ready for us
            inputready, outputready, exceptready = select.select(self.inputs, [], [])

            for s in inputready:
                if s == self.server:
                    self.process_new_client()

                elif s == sys.stdin:
                    # Handle standard input
                    inp = sys.stdin.readline().rstrip()
                    #self.process_console_command(inp)

                elif isinstance(s, Client):
                    # Process a message from a connected client
                    self.process_client_message(s)

        # Shutdown the Server
        self.shutdown()


# Class to keep track of a connected client
class Client:
    def __init__(self, (socket, address)):
        self.socket     = socket
        self.address    = address
        self.size       = 1024

        self.screenname = None

        self.socket.setblocking(0)

    # Pass along the server's fileno() refernce.
    # This lets the Client class pretend to be a socket
    def fileno(self):
        return self.socket.fileno()

    # Send message to Client
    def send(self, data):
        self.socket.send(data)

if __name__ == "__main__":
    # Create our server instance
    s = Server()
    # Start Listening for incomming connections
    s.open_socket()
    # Main loop of our server
    s.run()
