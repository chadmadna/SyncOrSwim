# client4.py
import os, sys, traceback, json, shutil, time
from threading import *
from socket import *
from tkinter import *
from tkinter.ttk import *
from ipaddress import ip_address

LOCAL_DIR = r'C:\Users\chadm\Desktop\t2'
TCP_IP = '127.0.0.1'
TCP_PORT = 9001
BUFFER_SIZE = 4096

TCP_LOCK = Lock()
PRINT_LOCK = RLock()

LOCK_1 = Semaphore(1)
LOCK_2 = Semaphore(0)

CLIENT_INDEX = dict()
JOBQUEUE = []
THREADS = dict()

STATUS = 'Ready.'

del globals()['enumerate']

class MainThread(Thread):
    
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
        self.serverindex = self.recvIndex()
        
    def run(self):
        self._update_index(self.clientdir, self.clientindex)
        print("Main thread started for " + self.ip + ":" + str(self.port))

    def displayThreads(self):
        print('{!s:15}  {!s:20} {}'.format('THREAD NAME','INFO','IS ALIVE'))
        for key in sorted(list(self.threadlist.keys())):
            print('{!s:15}: {!s:20} {}'.format(key, 
                self.threadlist[key], self.threadlist[key].isAlive()))

    def getIndex(self):
        self._update_index(LOCAL_DIR, self.clientindex)
        self.send('GETINDEX')
        self.serverindex = json.loads(self.receive())
        return (self.clientindex, self.serverindex)

    def sync(self, requestcode):
        LOCK_1.acquire()
        print('LOCK_1 acquired')
        # Sync server to client
        if requestcode == 'SYNCFROM':
            try:
                print('Started sync from server...')
                # Send sync signal
                self.send('SYNCFROM')
                # Send client directory
                self.wait('OK')
                self.send(LOCAL_DIR)
                # Update index before proceeding
                self._update_index(self.clientdir, self.clientindex)

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
                LOCK_2.release()
                print('LOCK_2 released')
            except:
                LOCK_1.release()

        # Sync client to server
        if requestcode == 'SYNCTO':
            try:
                print('Started sync to server...')
                # Send sync signal
                self.send('SYNCTO,{}'.format(LOCAL_DIR))
                # Update index before proceeding
                self._update_index(self.clientdir, self.clientindex)
                self.send('OK')
                serverdir = self.receive()
                print(serverdir)
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
                print('clientfiles: ', clientfiles)

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
                print(joblist)
                LOCK_1.release()
                print('LOCK_1 released')
            except:
                LOCK_1.release()
        
    def _update_index(self, directory, index):
        for root, dirs, files in os.walk(directory):
            for d in dirs:
                if not d.startswith('.'):
                    relpath = os.path.relpath(os.path.join(root, d), directory)
                    index[relpath] = (self.get_nametype(os.path.join(root,d)), os.path.getmtime(os.path.join(root, d)))
            for f in files:
                if not f.startswith('.'):
                    relpath = os.path.relpath(os.path.join(root, f), directory)
                    index[relpath] = (self.get_nametype(os.path.join(root,f)), os.path.getmtime(os.path.join(root, f)))        
    
    def get_nametype(self, path):
        if os.path.isdir(path):
            return 'dir'
        elif os.path.isfile(path):
            return 'file'
        else: return None

    def send(self, pkg, isbyte=True):
        time.sleep(0.1)
        with TCP_LOCK:
            if isbyte:
                self.sock.sendall(pkg.encode())
            if not isbyte:
                self.sock.sendall(pkg)
            self.sock.sendall('?magic?'.encode())

    def receive(self, isFile=False):
        with TCP_LOCK:
            s = self.sock
            ret = b''
            while True:
                buf = s.recv(BUFFER_SIZE)
                if buf:
                    ret += buf
                    if b'?magic?' in buf:
                        ret = ret.replace(b'?magic?',b'')
                        break
                elif not buf: break
            return ret if isFile else ret.decode()

    def wait(self, signal):
        while True:
            s = self.receive()
            if s == signal:
                break

    def sendIndex(self):
        outpkg = json.dumps(self.clientindex)
        self.send(outpkg)

    def recvIndex(self):
        self.send('GETINDEX')
        return json.loads(self.receive())

    def getDirTree(self, path):
        d = {'name': os.path.basename(path)}
        if os.path.isdir(path):
            d['type'] = "dir"
            d['children'] = [self.getDirTree(os.path.join(path,x)) \
                             for x in os.listdir(path)]
        else:
            d['type'] = "file"
        return d

    def recvDirTree(self):
        self.send('GETDIRTREE')
        return json.loads(self.receive())

    def __repr__(self):
        return "{}:{}".format(self.ip, self.port)

class WorkerThread(Thread):

    def __init__(self, jobqueue):
        Thread.__init__(self)
        self.jobqueue = jobqueue

    def run(self):
        LOCK_2.acquire()
        while True:
            if self.jobqueue:
                print(len(self.jobqueue))
                job_tuple = self.jobqueue.pop(0)
                job, file = job_tuple
                print(job[0])
                if job[0][:4] == 'SYNC':
                    print('SYNC')
                    continue
                if job[0] == 'CP':
                    with open(job[2], 'wb') as f:
                        f.write(file)
                        f.close()
                if job[0] == 'CPDIR':
                    try:
                        os.mkdir(job[2])
                    except FileExistsError:
                        print(job[2],' already exists.')
                if job[0] == 'RM':
                    os.remove(job[1])
                if job[0] == 'RMDIR':
                    shutil.rmtree(job[1])
                if job[0] == 'DONE':
                    print('LOCK_1 released')
                    LOCK_1.release()
                    print('Done syncing files!')
                    break
            else:
                LOCK_1.release()
                print('LOCK_1 released')
                            
    def __repr__(self):
        return "{} jobs in queue".format(len(self.jobqueue))

def print(*args, **kwargs):
    with PRINT_LOCK:
        __builtins__.print(*args, **kwargs)
        
def printthreads():
    with PRINT_LOCK:
        print('\nCurrent threads list:')
        THREADS['Main'].displayThreads()
        print('')

def connect(localdir=LOCAL_DIR, ip=TCP_IP, port=TCP_PORT):
    global tcpsock, mainthread
    tcpsock = socket(AF_INET, SOCK_STREAM)
    tcpsock.settimeout(15)

    print("Connecting to server...")
    while True:
        try:
            tcpsock.connect((TCP_IP, TCP_PORT))
            ip, port = tcpsock.getsockname()
            print('Connected to server {}:{}'.format(ip, port))
            break
        except timeout:
            print('Connection timed out.', file=sys.stderr)
            print('Retrying...')
            continue
        except KeyboardInterrupt:
            sys.exit()
        except ConnectionRefusedError:      
            print('Connection refused by server. Server may be offline.', file=sys.stderr)
            STATUS = 'Connection refused.'
            return

    mainthread = MainThread(ip, port, tcpsock, THREADS, LOCAL_DIR, CLIENT_INDEX, JOBQUEUE)
    THREADS['Main'] = mainthread
    mainthread.start()

def syncto():
    mainthread.sync('SYNCTO')

def syncfrom():
    mainthread.sync('SYNCFROM')

def getlocaldir():
    return mainthread.getDirTree(LOCAL_DIR)

def getserverdir():
    return mainthread.recvDirTree()
    
class LoginWindow(object):
    
    def __init__(self):
        self.window = Tk()
        self.window.geometry('350x220')
        self.window.iconbitmap('syncorswim.ico')
        self.window.title("SyncOrSwim")
        self.login = Frame(self.window)
        self.login.pack(expand=True)
        self.login
        self.dir = ''
        self.ip = ''
        self.port = 1
        self.app = None

        Label(self.login, text="Directory").grid(row=0, sticky='W')
        Label(self.login, text="IP Address").grid(row=1, sticky='W')
        Label(self.login, text="Port Number").grid(row=2, sticky='W')
        dirEntry = StringVar()
        ipEntry = StringVar()
        portEntry = IntVar()
        self.statusVar = StringVar()
        self.statusVar.set('')

        statusLabel = Label(self.login, textvariable=self.statusVar, foreground='red')
        statusLabel.grid(row=3, sticky='n', columnspan=2)

        dirEntry.set(LOCAL_DIR)
        ipEntry.set(TCP_IP)
        portEntry.set(TCP_PORT)
        
        self.e1 = Entry(self.login, textvariable=dirEntry)
        self.e1.grid(row=0, column=1)
        self.e2 = Entry(self.login, textvariable=ipEntry)
        self.e2.grid(row=1, column=1)
        self.e3 = Entry(self.login, textvariable=portEntry)
        self.e3.grid(row=2, column=1)

        Button(self.login, text='Submit', command=self.storeEntry).\
                      grid(row=4, column=1, sticky=W, pady=4)

        self.window.mainloop()

    def storeEntry(self):
        self.statusVar.set('')
        # checks the validity of directory
        if os.path.isdir(self.e1.get()):
            self.dir = self.e1.get()
        else:
            raise Exception("The directory is not valid.")

        # checks the validity of IP address
        try:
            self.ip = ip_address(self.e2.get())
        except ValueError:
            raise Exception("The IP address is not valid.")

        # checks validity of port number
        try:
            self.port = int(self.e3.get())
            if self.port < 1 or self.port > 65535:
                raise Exception("Invalid port number.")
        except ValueError:
            raise Exception("Port number must be an integer.")
        else:
            try:
                connect(self.e1.get(), self.e2.get(), self.e3.get())
            except:
                pass
            try:
                global mainthread
                if mainthread:
                    self.window.destroy()
                    self.app = AppWindow(mainthread)
            except NameError:
                pass
        if not self.app:
            self.statusVar.set('Connection refused by server.')

class AppWindow:
    
    def __init__(self, mainthread):
        self.window = Tk()
        self.window.iconbitmap('syncorswim.ico')
        self.window.title("SyncOrSwim")
        self.window.resizable(0,0)

        self.localDir = mainthread.clientindex
        self.serverDir = mainthread.serverindex
        
        self.tree_columns = ("directory", "type", "modification time")
        self.localtree_data = self._index_to_array(self.localDir)
        self.servertree_data = self._index_to_array(self.serverDir)
            
        self._setup_widgets()
        self._build_tree(self.localtree_data, self.localtree)
        self._build_tree(self.servertree_data, self.servertree)        
        self.window.mainloop()
        
    def _index_to_array(self, d):
        l = []
        for k in d.keys():
            l.append((k, d[k][0], time.ctime(d[k][1])))
        return l

    def _setup_widgets(self):
        
        self.localtreeframe = LabelFrame(self.window, text="Local Directory")
        self.localtreeframe.grid(row=0, column=0, padx=20, pady=20)

        self.servertreeframe = LabelFrame(self.window, text="Server Directory")
        self.servertreeframe.grid(row=0, column=1, padx=20, pady=20)

        localbtframe = Frame()
        localbtframe.grid(row=1, column=0, padx=5, pady=5)
        serverbtframe = Frame()
        serverbtframe.grid(row=1, column=1, padx=5, pady=5)

        self.localtree = Treeview(columns=self.tree_columns, show="headings", height=20)
        self.lvsb = Scrollbar(orient="vertical", command=self.localtree.yview)
        self.lhsb = Scrollbar(orient="horizontal", command=self.localtree.xview)
        self.localtree.configure(yscrollcommand=self.lvsb.set, xscrollcommand=self.lhsb.set)
        self.localtree.grid(column=0, row=0, sticky='nsew', in_=self.localtreeframe)
        self.lvsb.grid(column=1, row=0, sticky='ns', in_=self.localtreeframe)
        self.lhsb.grid(column=0, row=1, sticky='ew', in_=self.localtreeframe)
        self.localtreeframe.grid_columnconfigure(0, weight=1)
        self.localtreeframe.grid_rowconfigure(0, weight=1)

        self.servertree = Treeview(columns=self.tree_columns, show="headings", height=20)
        self.svsb = Scrollbar(orient="vertical", command=self.servertree.yview)
        self.shsb = Scrollbar(orient="horizontal", command=self.servertree.xview)
        self.servertree.configure(yscrollcommand=self.svsb.set, xscrollcommand=self.shsb.set)
        self.servertree.grid(column=0, row=0, sticky='nsew', in_=self.servertreeframe)
        self.svsb.grid(column=1, row=0, sticky='ns', in_=self.servertreeframe)
        self.shsb.grid(column=0, row=1, sticky='ew', in_=self.servertreeframe)
        self.servertreeframe.grid_columnconfigure(0, weight=1)
        self.servertreeframe.grid_rowconfigure(0, weight=1)

        updatelocalBt = Button(localbtframe, text='Update', command=self.updatelocaltree)
        updatelocalBt.grid(row=0, column=0, sticky='', pady=8)
        
        updateserverBt = Button(serverbtframe, text='Update', command=self.updateservertree)
        updateserverBt.grid(row=0, column=0, sticky='', pady=8)

        syncfromBt = Button(localbtframe, text='Sync from server', command=self.syncfrom)
        syncfromBt.grid(row=0, column=1, sticky='', pady=8)
        
        synctoBt = Button(serverbtframe, text='Sync to server', command=self.syncto)
        synctoBt.grid(row=0, column=1, sticky='', pady=8)

    def _build_tree(self, tree_data, tree):
        for col in self.tree_columns:
            tree.heading(col, text=col.title(),
                command=lambda c=col: self.sortby(tree, c, 0))
            tree.column(col, width=font.Font().measure(col.title()))

        for item in tree_data:
            tree.insert('', 'end', values=item)

            # adjust columns lenghts if necessary
            for indx, val in enumerate(item):
                ilen = font.Font().measure(val)
                if tree.column(self.tree_columns[indx], width=None) < ilen:
                    tree.column(self.tree_columns[indx], width=ilen)

    def sortby(self, tree, col, descending):
        # grab values to sort
        data = [(tree.set(child, col), child) for child in tree.get_children('')]

        # reorder data
        data.sort(reverse=descending)
        for indx, item in enumerate(data):
            tree.move(item[1], '', indx)

        # switch the heading so that it will sort in the opposite direction
        tree.heading(col,
            command=lambda col=col: self.sortby(tree, col, int(not descending)))
        
     def syncfrom(self):
        syncfrom()
        self.updatelocaltree()
        
    def syncto(self):
        syncto()
        self.updateservertree()
        
    def updatelocaltree(self):
        self.localtree.destroy()
        self.localtree = Treeview(columns=self.tree_columns, show="headings", height=20)
        self.localtree.configure(yscrollcommand=self.lvsb.set, xscrollcommand=self.lhsb.set)
        self.localtree.grid(column=0, row=0, sticky='nsew', in_=self.localtreeframe)
        self.localtree_data = self._index_to_array(self.localDir)
        self._build_tree(self.localtree_data, self.localtree)

    def updateservertree(self):
        self.servertree.destroy()
        self.servertree = Treeview(columns=self.tree_columns, show="headings", height=20)
        self.servertree.configure(yscrollcommand=self.svsb.set, xscrollcommand=self.shsb.set)
        self.servertree.grid(column=0, row=0, sticky='nsew', in_=self.servertreeframe)
        self.servertree_data = self._index_to_array(self.serverDir)
        self._build_tree(self.servertree_data, self.servertree)
        
if __name__ == '__main__':
    LoginWindow()

