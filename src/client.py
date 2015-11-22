# client.py
# Implementation of shared folder client-server file synchronization
# Created for Fasilkom UI 2015 Computer Networking course
# Irsyad Nabil 1406546134

from __future__ import print_function
import os, sys, traceback, json, shutil, time, cmd
from ipaddress import ip_address
from threading import *
from socket import *

LOCAL_DIR = r''
TCP_IP = '127.0.0.1'
TCP_PORT = 9001
BUF_SIZE = 4096

S_LOCK = Lock() # Socket mutex
P_LOCK = RLock() # Print mutex

S_SEM = Semaphore(1)
W_SEM = Semaphore(0)

CLIENT_INDEX = dict()
THREADS = dict()
JOBQUEUE = []


class MainThread(Thread):
    """The main thread performs sync operations to and from the
    server machine."""
    
    def __init__(self, ip, port, tcpsock, threads, clientdir, clientindex, jobqueue):
        Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.sock = tcpsock
        self.threadlist = threads
        self.clientdir = clientdir
        self.clientindex = clientindex
        self.jobqueue = jobqueue
        self.send(self.clientdir)
        timestamp = self.receive()
        print("Time from server is {}".format(timestamp))
        self.serverindex = self.getIndex()[0]
        
    def run(self):
        self.updateIndex()

    def send(self, pkg, isFile=False):
        time.sleep(0.1)
        with S_LOCK:
            if not isFile:
                self.sock.sendall(pkg.encode())
            elif isFile:
                self.sock.sendall(pkg)
            self.sock.sendall('?magic?'.encode())

    def receive(self, isFile=False):
        with S_LOCK:
            s = self.sock
            ret = b''
            while True:
                buf = s.recv(BUF_SIZE)
                if buf:
                    ret += buf
                    if b'?magic?' in buf:
                        ret = ret.replace(b'?magic?',b'')
                        break
                elif not buf: break
            return ret if isFile else ret.decode()

    def updateIndex(self):
        for root, dirs, files in os.walk(self.clientdir):
            for d in dirs:
                if not d.startswith('.'):
                    relpath = os.path.relpath(os.path.join(root, d), self.clientdir)
                    self.clientindex[relpath] = (self.getNametype(os.path.join(root,d)), os.path.getmtime(os.path.join(root, d)))
            for f in files:
                if not f.startswith('.'):
                    relpath = os.path.relpath(os.path.join(root, f), self.clientdir)
                    self.clientindex[relpath] = (self.getNametype(os.path.join(root,f)), os.path.getmtime(os.path.join(root, f)))        

    def syncFromServer(self):
        """Sync local files from server machine by examining client's file index and then
        send sync and file operation protocols."""

        # Acquire the sync thread semaphore
        S_SEM.acquire()
        try:
            # Send request, wait for signal then send client's directory
            print('Started sync from server...')
            self.send('SYNCFROM')
            self.wait('OK')
            self.send(LOCAL_DIR)

            # Update index before proceeding
            self.updateIndex()

            # Encode, wait for signal and send index to server
            outpkg = json.dumps(self.clientindex)
            self.wait('OK')
            self.send(outpkg)

            # Receive requests and files from server
            while True:
                request = self.receive()
                if request:
                    job = tuple(request.split(','))
                    self.send('OK')

                    # Atomically add a single batch of sync jobs
                    # Wait and receive file for all copy jobs
                    if job[0] == 'CP':
                        file = self.receive(isFile=True)
                        self.send('OK')
                        # Put job and file in jobqueue
                        self.jobqueue.append((job, file))
                    # Put job into jobqueue if not copy job
                    else:
                        self.jobqueue.append((job, None))
                    if job[0] == 'DONE':
                        print('Done syncing from server!')
                        break
            global workerthread
            workerthread = WorkerThread(self.jobqueue)
            workerthread.start()
            THREADS['WorkerThread'] = workerthread
            W_SEM.release()
            workerthread.join()
        except:
            S_SEM.release()

    def syncToServer(self):
        S_SEM.acquire()
        # Sync client to server
        try:
            print('Started sync to server...')
            # Send sync signal
            self.send('SYNCTO,{}'.format(LOCAL_DIR))
            # Update index before proceeding
            self.updateIndex()
            self.send('OK')
            serverdir = self.receive()
            self.send('OK')
            # Receive and decode index from client
            # Blocks until index received
            inpkg = self.receive()
            serverindex = json.loads(inpkg)

            # Setup index and client directory
            clientindex = self.clientindex
            clientdir = self.clientdir

            # Initiate joblist for writing into jobqueue
            joblist = []
            joblist.append('SYNCTO,{}'.format(LOCAL_DIR))

            # Setup files and dirs to iterate over
            serverfiles = []
            for key in serverindex.keys(): serverfiles.append(key)
            serverfiles.sort()
            clientfiles = []
            for key in clientindex.keys(): clientfiles.append(key)
            clientfiles.sort()

            # Iterate over remote files, add to joblist
            for name in serverfiles:

                localpath = os.path.join(clientdir, name)
                remotepath = os.path.join(serverdir, name)
                localroot = os.path.split(localpath)[0]
                remoteroot = os.path.split(remotepath)[0]

                # Case 1: File/dir exists in remote but doesn't exist in local
                # Remove files/dirs in remote that do not exist in local
                if not os.path.exists(localpath) and name in serverfiles:

                    if serverindex[name][0] == 'dir':
                        joblist.append('RMDIR,{}'.format(remotepath))
                    elif serverindex[name][0] == 'file':
                        joblist.append('RM,{}'.format(remotepath))
                        
            # Iterate over local files, add to joblist
            for name in clientfiles:
                
                localpath = os.path.join(clientdir, name)
                remotepath = os.path.join(serverdir, name)
                localroot = os.path.split(localpath)[0]
                remoteroot = os.path.split(remotepath)[0]

                # Case 2: File/dir doesn't exist in remote but exists in local
                # Copy over files/dirs in local to remote
                if not name in serverfiles and os.path.exists(localpath):

                    if os.path.isdir(localpath):
                        joblist.append('CPDIR,{},{}'.format(localpath, remotepath))
                    else:
                        joblist.append('CP,{},{}'.format(localpath, remotepath))
                        
                # Case 3: File/dir exists both in local and remote
                # Compare both files/dirs and keep newest in both local and remote
                elif name in serverfiles and os.path.exists(localpath):
                    if clientindex[name][1] > clientindex[name][1]:

                        if os.path.isdir(localpath):
                            joblist.append('CPDIR,{},{}'.format(localpath, remotepath))
                        else:
                            joblist.append('CP,{},{}'.format(localpath, remotepath))
                        
            joblist.append('DONE')

            # Sort and iterate over jobs in joblist, send file if necessary
            cpdirjobs = []
            for entry in joblist:
                if entry.split(',')[0] == 'CPDIR':
                    cpdirjobs.append(joblist.pop(joblist.index(entry)))
            for entry in reversed(cpdirjobs):
                joblist.insert(1, entry)

            for item in joblist:
                job = item.split(',')
                self.send(item)
                self.wait('OK')
                # Send file for each copy jobs
                if job[0] == 'CP':
                    with open(job[1], 'rb') as f:
                        self.send(f.read(), isbyte=False)
                    self.wait('OK')
            # End of a sync protocol
            print('Done syncing to server!')
            S_SEM.release()
        except:
            S_SEM.release()
    
    def getNametype(self, path):
        if os.path.isdir(path):
            return 'dir'
        elif os.path.isfile(path):
            return 'file'
        else: return None

    def wait(self, signal):
        while True:
            s = self.receive()
            if s == signal:
                break

    def getIndex(self):
        self.updateIndex()
        self.send('GETINDEX')
        self.serverindex = json.loads(self.receive())
        return (self.clientindex, self.serverindex)

    def sendIndex(self):
        outpkg = json.dumps(self.clientindex)
        self.send(outpkg)

    def displayThreads(self):
        print('{!s:15}  {!s:20} {}'.format('THREAD NAME','INFO','IS ALIVE'))
        for key in sorted(list(self.threadlist.keys())):
            print('{!s:15}: {!s:20} {}'.format(key, 
                self.threadlist[key], self.threadlist[key].isAlive()))

    def __repr__(self):
        """Represents the thread in readable string format."""
        return "{}:{}".format(self.ip, self.port)

class WorkerThread(Thread):
    """Performs high-level file operations from the job queue
    from a sync job."""

    global LOCAL_DIR

    def __init__(self, jobqueue):
        Thread.__init__(self)
        self.jobqueue = jobqueue

    def run(self):
        """Iterates over the jobqueue and writes changes to
        local directory."""
        
        os.chdir(mainthread.clientdir)
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
        return "{} jobs in queue".format(len(self.jobqueue))

class cmdApp(cmd.Cmd):
    """Command line interpreter app that runs interactively."""
    
    def __init__(self):

        global LOCAL_DIR, TCP_IP, TCP_PORT
        
        cmd.Cmd.__init__(self)
        print('\n~ SyncOrSwim 1.0 client\n~ Connect to a remote server.\n')

        self.prompt = 'SyncOrSwim >> '
        
        while True:
            dirpath = str(input('Enter path to shared folder: '))
            if not os.path.exists(dirpath):
                print("The path you entered does not exist.")
                continue
            LOCAL_DIR = dirpath
            break
        
        while True:
            ipaddr = str(input('IP address: '))
            try:
                ip_address(ipaddr)
            except ValueError:
                print("The IP address you entered is invalid.")
                continue
            if not ip_address(ipaddr):
                print("The IP address you entered is invalid.")
                continue
            TCP_IP = ipaddr
            break
        
        while True:
            portnum = input('Port number: ')
            try:
                portnum = int(portnum)
            except ValueError:
                print("The port number you entered is invalid.")
                continue
            if not portnum:
                print("Please enter a port number.")
                continue
            TCP_PORT = portnum
            break

        connect(LOCAL_DIR, TCP_IP, TCP_PORT)
        if mainthread:
            print("\nType 'syncto' to push local files to server")
            print("Type 'syncfrom' to pull changes from server to client")
            print("Type 'serverfiles' to view server files")
            print("Type 'printthreads' to view spawned threads")
            print("Type 'exit' close connection and exit\n")

    def do_syncto(self, line):
        syncto()

    def do_syncfrom(self, line):
        syncfrom()

    def do_serverfiles(self, line):
        serverfiles()

    def do_printthreads(self, line):
        printthreads()

    def do_exit(self, line):
        close()
        
    
##def print(*args, **kwargs):
##    """Overrides the print function so that it uses a lock
##    to print output in order."""
##    with P_LOCK:
##        __builtins__.print(*args, **kwargs)
        
def printthreads():
    print('\nCurrent threads list:')
    THREADS['Main'].displayThreads()
    print('')
                         
def connect(localdir=LOCAL_DIR, ip=TCP_IP, port=TCP_PORT):
    
    global tcpsock, mainthread, LOCAL_DIR

    tcpsock = socket(AF_INET, SOCK_STREAM)
    tcpsock.settimeout(15)

    print("Connecting to server at {}:{}...".format(ip, port))
    while True:
        try:
            tcpsock.connect((TCP_IP, TCP_PORT))
            ip, port = tcpsock.getsockname()
            print('Connected to server on socket {}:{}'.format(ip, port))
            break
        except timeout:
            print('Connection timed out.', file=sys.stderr)
            print('Retrying...')
            continue
        except KeyboardInterrupt:
            sys.exit()
        except ConnectionRefusedError:      
            print('Connection refused by server. Server may be offline.', file=sys.stderr)
            return

    mainthread = MainThread(ip, port, tcpsock, THREADS, LOCAL_DIR, CLIENT_INDEX, JOBQUEUE)
    THREADS['Main'] = mainthread
    mainthread.start()

def syncto():
    mainthread.syncToServer()

def syncfrom():
    mainthread.syncFromServer()

def serverfiles():
    index = mainthread.getIndex()[1]
    print('\nNAME'+46*' '+'| TYPE | LAST MODIFIED')
    for k in index.keys():
        name, ntype, mtime = k, index[k][0], time.ctime(index[k][1])
        if len(name) > 50:
            name = '...' + name[len(name)-46:]
        print('{:50}| {:4} | {}'.format(name, ntype, mtime))

def close():
    sys.exit()

if __name__ == '__main__':

    # Running in IDLE
    if 'idlelib.run' in sys.modules:
        print('~ SyncOrSwim 1.0 client\n~ Connect to a remote server.\n')
        while True:
            dirpath = str(input('Enter path to shared folder: '))
            if not os.path.exists(dirpath):
                print("The path you entered does not exist.")
                continue
            LOCAL_DIR = dirpath
            break
        
        while True:
            ipaddr = str(input('IP address: '))
            try:
                ip_address(ipaddr)
            except ValueError:
                print("The IP address you entered is invalid.")
                continue
            if not ip_address(ipaddr):
                print("The IP address you entered is invalid.")
                continue
            TCP_IP = ipaddr
            break
        
        while True:
            portnum = input('Port number: ')
            try:
                portnum = int(portnum)
            except ValueError:
                print("The port number you entered is invalid.")
                continue
            if not portnum:
                print("Please enter a port number.")
                continue
            TCP_PORT = portnum
            break
        
        connect(LOCAL_DIR, TCP_IP, TCP_PORT)
        if mainthread:
            print("\nType 'syncto()' to push local files to server")
            print("Type 'syncfrom()' to pull changes from server to client")
            print("Type 'serverfiles()' to view server files")
            print("Type 'printThreads()' to view spawned threads")
            print("Type 'close()' to exit")

    # Running in CLI
    elif sys.stdin.isatty():  
        cmdApp().cmdloop()
