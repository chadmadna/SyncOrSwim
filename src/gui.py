# client_GUI.py
import os, sys
from tkinter import *
from tkinter.ttk import *
from ipaddress import ip_address
import client

class LoginWindow(object):
    
    def __init__(self):
        self.window = Tk()
        self.window.geometry('350x220')
        self.window.iconbitmap('../assets/syncorswim.ico')
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

        dirEntry.set(client.LOCAL_DIR)
        ipEntry.set(client.TCP_IP)
        portEntry.set(client.TCP_PORT)
        
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
            client.connect(self.e1.get(), self.e2.get(), self.e3.get())
            try:
                if client.mainthread:
                    self.window.destroy()
                    self.app = AppWindow(client.mainthread)
                    client.LOCAL_DIR, client.TCP_IP, client.TCP_PORT = self.e1.get(), self.e2.get(), self.e3.get()
            except NameError:
                pass
        if not self.app:
            self.statusVar.set('Connection refused by server.')

class AppWindow:
    
    def __init__(self, mainthread):
        self.window = Tk()
        self.window.iconbitmap('../assets/syncorswim.ico')
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
        client.syncfrom()
        self.updatelocaltree()
        
    def syncto(self):
        client.syncto()
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

