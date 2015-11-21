# server4.py
import sys, os, select, shutil, json, time, datetime, traceback
from socketserver import ThreadingMixIn
from threading import *
from socket import *

LOCAL_DIR = r'C:\Users\chadm\Desktop\t1'
TCP_IP = '127.0.0.1'
TCP_PORT = 9001
BUF_SIZE = 4096
COUNT = 0

C_LOCK = Lock() # Count mutex
Q_LOCK = Lock() # Queue mutex
S_LOCK = Lock() # Socket mutex
P_LOCK = RLock() # Print mutex

C_SEM = Semaphore(1) # Semaphore for client threads
W_SEM = Semaphore(0) # Semaphore for worker threads

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

    def getID(self):
        global COUNT, C_LOCK
        with C_LOCK:
            COUNT += 1
        return COUNT

    def run(self):
        print('ClientThread[{}] is running!'.format(self.threadID))
        while True:
            request = self.receive()
            try:
                requestcode = request.split(',')[0]
                print(requestcode)
                if requestcode == 'SYNCFROM':
                    self.syncToClient()
                    continue
                elif requestcode == 'SYNCTO':
                    self.syncFromClient()
                    continue
                elif requestcode == 'GETINDEX':
                    self.sendIndex()
                    continue
                elif requestcode == 'GETDIRTREE':
                    self.sendDirTree()
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

    def getNametype(self, path):
        if os.path.isdir(path):
            return 'dir'
        elif os.path.isfile(path):
            return 'file'
        else: return None
        
    def sendTime(self):
        timestamp = datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")
        self.send(timestamp)

    def sendIndex(self):
        outpkg = json.dumps(self.serverindex)
        self.send(outpkg)

    def sendDirTree(self):
        outpkg = json.dumps(self.makeDirTree(LOCAL_DIR))
        self.send(outpkg)

    def makeDirTree(self, path):
        d = {'name': os.path.basename(path)}
        if os.path.isdir(path):
            d['type'] = "dir"
            d['children'] = [self.makeDirTree(os.path.join(path,x)) \
                             for x in os.listdir(path)]
        else:
            d['type'] = "file"
        return d

    def wait(self, signal):
        while True:
            s = self.receive()
            if s == signal:
                break
            
    def updateIndex(self):
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
        """Sync local files to client machine by examining client's file index and then
        send sync and file operation protocols."""
        # Acquire the client thread semaphore
        C_SEM.acquire()

        # Unpack request parameter as request code and client directory
        # Sync client to server
        print('Started sync from client...')
        self.wait('OK')
        self.send(LOCAL_DIR)
        # Update index before proceeding
        self.updateIndex()
        # Encode, wait for signal and send index to client
        outpkg = json.dumps(self.serverindex)
        self.wait('OK')
        self.send(outpkg)

        # Receive requests and files from client
        Q_LOCK.acquire()
        while True:
            print('receiving request')
            request = self.receive()
            if request:
                job = tuple(request.split(','))
                print(job[0])
                self.send('OK')
                # Atomically add a single batch of sync jobs
                # Wait and receive file for all copy jobs
                if job[0] == 'CP':
                    print('receiveing file')
                    file = self.receive(isFile=True)
                    self.send('OK')
                    # Put job and file in jobqueue
                    self.jobqueue.append((job, file))
                elif job[0] == 'DONE':
                    self.jobqueue.append((job, None))
                    print('Done syncing from client!')
                    Q_LOCK.release()
                    break
                # Put job into jobqueue if not copy job
                else:
                    self.jobqueue.append((job, None))
        workerthread = WorkerThread(self.jobqueue, self)
        workerthread.start()
        threads['WorkerThread[{}]'.format(self.threadID)] = workerthread
        W_SEM.release()

    def syncToClient(self):
        C_SEM.acquire()
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

        joblist.append('DONE')

        # Sort and iterate over jobs in joblist, send file if necessary
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
        print(joblist)
        C_SEM.release()

    def __repr__(self):
        return "{}:{}".format(self.ip, self.port)
    
class WorkerThread(Thread):

    def __init__(self, jobqueue, clientthread):
        Thread.__init__(self)
        self.jobqueue = jobqueue
        self.threadID = clientthread.threadID

    def run(self):
        print('worker thread started')
        W_SEM.acquire()
        if not self.jobqueue:
            print('C_SEM released, jobqueue empty')
            C_SEM.release()
        else:
            while self.jobqueue:
                print(len(self.jobqueue))
                job_tuple = self.jobqueue.pop(0)
                job, file = job_tuple
                jobcode = job[0]
                if jobcode[:4] == 'SYNC':
                    print('SYNC')
                    continue
                if jobcode == 'CP':
                    src, dest = job[1], job[2]
                    with open(dest, 'wb') as f:
                        f.write(file)
                        f.close()
                if jobcode == 'CPDIR':
                    src, dest = job[1], job[2]
                    try:
                        print(dest)
                        os.mkdir(dest)
                    except FileExistsError:
                        print(dest,' already exists.')
                if jobcode == 'RM':
                    dest = job[1]
                    os.remove(dest)
                if jobcode == 'RMDIR':
                    dest = job[1]
                    shutil.rmtree(dest)
                if jobcode == 'DONE':
                    print('C_SEM released, DONE')
                    C_SEM.release()
                    break
        print('Worker thread done')

    def __repr__(self):
        return "WorkerThread"

class ListenThread(Thread):

    def __init__(self, tcpsock, threads, serverdir, serverindex, jobqueue):
        Thread.__init__(self)
        self.tcpsock = tcpsock
        self.threadlist = threads
        self.serverdir = serverdir
        self.serverindex = serverindex
        self.jobqueue = jobqueue

    def run(self):
        self.tcpsock.listen(5)
        while len(self.threadlist) < 10:

            print("Waiting for incoming connections...")

            inputready, outputready, exceptready = select.select([self.tcpsock],[],[])
            for i in inputready:
                if i == self.tcpsock:
                    (conn, (ip,port)) = self.tcpsock.accept()
                    print('Got connection from ', (ip,port))
                    clientthread = ClientThread(ip, port, conn, self.serverdir, self.serverindex, self.jobqueue)
                    clientthread.start()
                    self.threadlist['ClientThread[{}]'.format(clientthread.threadID)] = clientthread
                    time.sleep(1)

    def __repr__(self):
        return "ListenThread"

    def displayThreads(self):
        print('{:18}  {:20} {}'.format('THREAD NAME','INFO','IS ALIVE'))
        for key in sorted(list(self.threadlist.keys())):
            print('{!s:18}: {!s:20} {}'.format(key,
                    self.threadlist[key], self.threadlist[key].isAlive()))

def printThreads(threads):
    with P_LOCK:
        print('Current threads list:')
        threads['ListenThread'].displayThreads()
        print('')

def print(*args, **kwargs):
    with P_LOCK:
        __builtins__.print(*args, **kwargs)

if __name__ == '__main__':

    threads = dict()
    serverindex = dict()
    jobqueue = []

    tcpsock = socket(AF_INET, SOCK_STREAM)
    tcpsock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    tcpsock.bind((TCP_IP, TCP_PORT))
    tcpsock.setblocking(0.0)

    listenthread = ListenThread(tcpsock, threads, LOCAL_DIR, serverindex, jobqueue)
    listenthread.start()
    threads['ListenThread'] = listenthread
