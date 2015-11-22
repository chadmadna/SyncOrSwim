# server.py
# Implementation of shared folder client-server file synchronization
# Created for Fasilkom UI 2015 Computer Networking course
# Irsyad Nabil 1406546134

import os, sys, select, shutil, json, time, datetime, traceback
from socketserver import ThreadingMixIn
from threading import *
from socket import *

LOCAL_DIR = r''
TCP_IP = '127.0.0.1'
TCP_PORT = 9001
BUF_SIZE = 4096
COUNT = 0

C_LOCK = Lock() # Count mutex
Q_LOCK = Lock() # Queue mutex
S_LOCK = Lock() # Socket mutex
P_LOCK = RLock() # Print mutex

S_SEM = Semaphore(1) # Semaphore for sync threads
W_SEM = Semaphore(0) # Semaphore for worker threads

SERVER_INDEX = dict()
THREADS = dict()
JOBQUEUE = []

class ClientThread(Thread):
    """The client thread is started after a connection from a client
    is received, then the thread waits for a SYNC command from the
    client."""
    def __init__(self, ip, port, sock, serverdir, serverindex, jobqueue):
        Thread.__init__(self)
        self.ip, self.port, self.sock = ip, port, sock
        self.serverdir, self.serverindex = serverdir, serverindex
        self.jobqueue = jobqueue
        self.threadID = self.getID()
        self.clientdir = self.receive()
        self.updateIndex()
        self.sendTime()

    def run(self):
        """The client thread enters a loop that parses client requests
        sent over the socket connection and calls the corresponding
        functions."""
        print('ClientThread[{}] is running!'.format(self.threadID))
        while True:
            request = self.receive()
            try:
                requestcode = request.split(',')[0]
                if requestcode == 'SYNCFROM':
                    self.syncToClient()
                    continue
                elif requestcode == 'SYNCTO':
                    self.syncFromClient()
                    continue
                elif requestcode == 'GETINDEX':
                    self.sendIndex()
                    continue
                elif requestcode == 'CLOSE':
                    print('Connection to {}:{} closed'.format(self.ip,self.port))
                    self.tcpsock.close()
                    break
                elif not request:
                    continue
                else:
                    print(request, type(request))
                    raise Exception('Unexpected bytes from client.')
            except KeyboardInterrupt:
                sys.exit()
            except Exception as err:
                traceback.print_exc()
                continue
            self.tcpsock.close()
            print('ClientThread[{}] exiting..'.format(self.threadID))

    def send(self, pkg, isFile=False):
        """This is a universal send function that waits for the socket to
        become available, then sends an encoded byte package. If the
        package is a file, it will be already in byte format. The function
        includes a self-terminating stop-word, which is '?magic?'."""
        time.sleep(0.1)
        inready, outready, exready = select.select([],[self.sock],[])
        for sock in outready:
            if sock == self.sock:
                if not isFile:
                    self.sock.sendall(pkg.encode())
                elif isFile:
                    self.sock.sendall(pkg)
                self.sock.sendall('?magic?'.encode())

    def receive(self, isFile=False):
        """This is a universal receive function that waits for the socket
        to become available, then receives a byte sequence which will be
        either decoded to string or kept in byte format."""
        inready, outready, exready = select.select([self.sock],[],[])
        for sock in inready:
            time.sleep(0.01)
            if sock == self.sock:
                s = self.sock
                ret = b''
                while True:
                    buf = s.recv(BUF_SIZE)
                    if buf:
                        ret += buf
                        if b'?magic?' in buf:
                            ret = ret.replace(b'?magic?',b'')
                            break
                return ret if isFile else ret.decode()

    def updateIndex(self):
        """Updates the index of the files in the server directory."""
        for root, dirs, files in os.walk(self.serverdir):
            for d in dirs:
                if not d.startswith('.'):
                    relpath = os.path.relpath(os.path.join(root, d), self.serverdir)
                    self.serverindex[relpath] = (self.getNametype(os.path.join(root,d)), os.path.getmtime(os.path.join(root, d)))
            for f in files:
                if not f.startswith('.'):
                    relpath = os.path.relpath(os.path.join(root, f), self.serverdir)
                    self.serverindex[relpath] = (self.getNametype(os.path.join(root,f)), os.path.getmtime(os.path.join(root, f)))

    def syncFromClient(self):
        """Sync local files from client machine by examining client's file index and then
        send sync and file operation protocols."""

        # Acquire the client thread semaphore
        S_SEM.acquire()
        try:
            # Wait for signal then sends server's directory
            print('Started sync from client...')
            self.wait('OK')
            self.send(LOCAL_DIR)

            # Update index before proceeding
            self.updateIndex()

            # Encode, wait for signal then send index to client
            outpkg = json.dumps(self.serverindex)
            self.wait('OK')
            self.send(outpkg)

            # Receive requests and files from client
            Q_LOCK.acquire()
            while True:
                request = self.receive()
                if request:
                    job = tuple(request.split(','))
                    self.send('OK')

                    # Atomically add a single batch of sync jobs
                    # Wait and receive file for all copy jobs
                    # Put job and file in queue
                    if job[0] == 'CP':
                        file = self.receive(isFile=True)
                        self.send('OK')
                        self.jobqueue.append((job, file))

                    # Finish adding jobs to the client
                    elif job[0] == 'DONE':
                        self.jobqueue.append((job, None))
                        print('Done syncing from client!')
                        Q_LOCK.release()
                        break

                    # Put job into jobqueue if not copy job
                    else:
                        self.jobqueue.append((job, None))

            # Start worker thread that will write to the local directory
            # Release the semaphore for the worker thread
            workerthread = WorkerThread(self.jobqueue, self)
            workerthread.start()
            THREADS['WorkerThread[{}]'.format(self.threadID)] = workerthread
            W_SEM.release()
            workerthread.join()
        except:
            S_SEM.release()

    def syncToClient(self):

        # Acquire the client thread semaphore
        S_SEM.acquire()

        # Sync server from client
        print('Started sync to client...')

        # Update index before proceeding
        self.updateIndex()
        self.send('OK')

        # Receive client directory
        clientdir = self.receive()
        self.send('OK')

        # Receive and decode index from client
        # Blocks until index received
        inpkg = self.receive()
        clientindex = json.loads(inpkg)

        # Setup index and server directory
        serverindex = self.serverindex
        serverdir = self.serverdir

        # Initiate joblist for writing into jobqueue
        joblist = []
        joblist.append('SYNCFROM,{}'.format(LOCAL_DIR))

        # Setup files and dirs to iterate over
        serverfiles = []
        for key in serverindex.keys(): serverfiles.append(key)
        serverfiles.sort()
        clientfiles = []
        for key in clientindex.keys(): clientfiles.append(key)
        clientfiles.sort()

        # Iterate over remote files, add to joblist
        for name in clientfiles:

            localpath = os.path.join(serverdir, name)
            remotepath = os.path.join(clientdir, name)
            localroot = os.path.split(localpath)[0]
            remoteroot = os.path.split(remotepath)[0]

            # Case 1: File/dir exists in remote but doesn't exist in local
            # Remove files/dirs in remote that do not exist in local
            if not os.path.exists(localpath) and name in clientfiles:

                if clientindex[name][0] == 'dir':
                    joblist.append('RMDIR,{}'.format(remotepath))
                elif clientindex[name][0] == 'file':
                    joblist.append('RM,{}'.format(remotepath))

        # Iterate over local files, add to joblist
        for name in serverfiles:
            
            localpath = os.path.join(serverdir, name)
            remotepath = os.path.join(clientdir, name)
            localroot = os.path.split(localpath)[0]
            remoteroot = os.path.split(remotepath)[0]

            # Case 2: File/dir doesn't exist in remote but exists in local
            # Copy over files/dirs in local to remote
            if not name in clientfiles and os.path.exists(localpath):

                if os.path.isdir(localpath):
                    joblist.append('CPDIR,{},{}'.format(localpath, remotepath))
                else:
                    joblist.append('CP,{},{}'.format(localpath, remotepath))

            # Case 3: File/dir exists both in local and remote
            # Compare both files/dirs and keep newest in both local and remote
            elif name in clientfiles and os.path.exists(localpath):

                if serverindex[name][1] > clientindex[name][1]:
                    if os.path.isdir(localpath):
                        joblist.append('CPDIR,{},{}'.format(localpath, remotepath))
                    else:
                        joblist.append('CP,{},{}'.format(localpath, remotepath))

        # End the job list
        joblist.append('DONE')

        # Sort and iterate over jobs in joblist, send file if necessary
        # Sort jobs so that directories get created first
        cpdirjobs = []
        for entry in joblist:
            if entry.split(',')[0] == 'CPDIR':
                cpdirjobs.append(joblist.pop(joblist.index(entry)))
        for entry in reversed(cpdirjobs):
            joblist.insert(1, entry)

        for job in joblist:
            jobcode = job.split(',')
            self.send(job)
            self.wait('OK')

            # Send file for each copy jobs
            if jobcode[0] == 'CP':
                with open(jobcode[1], 'rb') as f:
                    self.send(f.read(), isFile=True)
                self.wait('OK')

        # End of a sync protocol
        print('Done syncing to client!')
        S_SEM.release()

    def getNametype(self, path):
        """Returns a string representing the type of a path name."""
        if os.path.isdir(path):
            return 'dir'
        elif os.path.isfile(path):
            return 'file'
        else: return None
        
    def sendTime(self):
        """Sends a timestamp to the client."""
        timestamp = datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")
        self.send(timestamp)

    def sendIndex(self):
        """Sends the server index to the client."""
        self.updateIndex()
        outpkg = json.dumps(self.serverindex)
        self.send(outpkg)

    def wait(self, signal):
        """Waits for a signal from the client in the form of a string."""
        while True:
            s = self.receive()
            if s == signal:
                break

    def getID(self):
        """Returns the ID for a thread."""
        global COUNT, C_LOCK
        with C_LOCK:
            COUNT += 1
        return COUNT
    
    def __repr__(self):
        """Represents the thread in readable string format."""
        return "{}:{}".format(self.ip, self.port)
    
class WorkerThread(Thread):
    """Performs high-level file operations from the job queue
    from a sync job."""

    def __init__(self, jobqueue, clientthread):
        Thread.__init__(self)
        self.jobqueue = jobqueue
        self.threadID = clientthread.threadID

    def run(self):
        """Iterates over the jobqueue and writes changes to
        local directory."""

        os.chdir(LOCAL_DIR)
        print('Writing to local directory..')
        W_SEM.acquire()
        if not self.jobqueue:
            print('No files in jobqueue.')
            S_SEM.release()
        else:
            while self.jobqueue:
                job_tuple = self.jobqueue.pop(0)
                job, file = job_tuple
                jobcode = job[0]
                if jobcode[:4] == 'SYNC':
                    continue
                if jobcode == 'CP':
                    src, dest = job[1], job[2]
                    with open(dest, 'wb') as f:
                        f.write(file)
                        f.close()
                if jobcode == 'CPDIR':
                    src, dest = job[1], job[2]
                    try:
                        os.mkdir(dest)
                    except FileExistsError:
                        print(dest,' already exists.')
                elif jobcode == 'RM':
                    dest = job[1]
                    os.remove(dest)
                elif jobcode == 'RMDIR':
                    dest = job[1]
                    shutil.rmtree(dest)
                if jobcode == 'DONE':
                    print('Done writing to local directory!')
                    S_SEM.release()
                    break

    def __repr__(self):
        return "WorkerThread"

class ListenThread(Thread):
    """Listens to a single port for incoming connections, then creates
    a new ClientThread thread to handle the connection."""

    def __init__(self, tcpsock, threads, serverdir, serverindex, jobqueue):
        Thread.__init__(self)
        self.tcpsock = tcpsock
        self.threadlist = threads
        self.serverdir = serverdir
        self.serverindex = serverindex
        self.jobqueue = jobqueue

    def run(self):
        """Listens for connections and creates new threads to handle
        up to 10 connections."""
        self.tcpsock.listen(5)
        while len(self.threadlist) < 10:
            
            print("Waiting for incoming connections...")

            # Waits for the socket to be available, then creates a thread
            # for incoming client connections.
            inputready, outputready, exceptready = select.select([self.tcpsock],[],[])
            for i in inputready:
                if i == self.tcpsock:
                    (conn, (ip,port)) = self.tcpsock.accept()
                    print('Got connection from ', (ip,port))
                    clientthread = ClientThread(ip, port, conn, self.serverdir, self.serverindex, self.jobqueue)
                    clientthread.start()
                    self.threadlist['ClientThread[{}]'.format(clientthread.threadID)] = clientthread
                    time.sleep(1)

    def displayThreads(self):
        """Pretty-prints the list of spawned threads."""
        print('{:18}  {:20} {}'.format('THREAD NAME','INFO','IS ALIVE'))
        for key in sorted(list(self.threadlist.keys())):
            print('{!s:18}: {!s:20} {}'.format(key,
                    self.threadlist[key], self.threadlist[key].isAlive()))

    def __repr__(self):
        return "ListenThread"

def printThreads(threads):
    """A helper function for printing threads."""
    with P_LOCK:
        print('Current threads list:')
        threads['ListenThread'].displayThreads()
        print('')

def print(*args, **kwargs):
    """Overrides the print function so that it uses a lock
    to print output in order."""
    with P_LOCK:
        __builtins__.print(*args, **kwargs)

def close():
    """Closes the connection and exits the program."""
    sys.exit()

if __name__ == '__main__':

    # Initializes socket and binds address to socket
    tcpsock = socket(AF_INET, SOCK_STREAM)
    tcpsock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    tcpsock.bind(('', TCP_PORT))
    tcpsock.setblocking(0.0)

    # Prompts the user to input the server's shared folder directory path
    while True:
        dirpath = str(input('Enter path to shared folder: '))
        if not os.path.exists(dirpath):
            print("The path you entered does not exist.")
            continue
        LOCAL_DIR = dirpath
        break

    # Creates a new ListenThread thread to listen for connections
    listenthread = ListenThread(tcpsock, THREADS, LOCAL_DIR, SERVER_INDEX, JOBQUEUE)
    listenthread.start()
    THREADS['ListenThread'] = listenthread
