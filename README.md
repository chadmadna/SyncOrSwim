Sync or Swim
===================


A program that synchronizes directory contents between clients.

----------


server.py
-------------
StackEdit stores your documents in your browser, which means all your documents are automatically saved locally and are accessible **offline!**

> **ClientThread**
> describes the server mechanism in handling requests from the client.

#### <i class="icon-check"></i> getID
Assigns an ID to a thread within a critical section.

#### <i class="icon-check"></i> run
Processes every thread that is received one at a time by determining which action to take based on the request code of the thread. The parsing of the threads continue until the TCP socket connection is closed or when a keyboard interrupt occurs.

#### <i class="icon-check-empty"></i> send
You can rename the current document by clicking the document title in the navigation bar.

#### <i class="icon-check-empty"></i> receive
You can delete the current document by clicking <i class="icon-trash"></i> **Delete document** in the document panel.

#### <i class="icon-check"></i> getNametype
Traverses a predetermined path based on input and returns whether it is a directory or a file.

#### <i class="icon-check"></i> sendTime
Retrieves the date and time from the system and sends it as a package to the client.

#### <i class="icon-check-empty"></i> sendIndex
Traverses a predetermined path based on input and returns whether it is a directory or a file.

#### <i class="icon-check"></i> sendDirTree
Makes a directory tree using the makeDirTree function and sends it as a package to the client.

#### <i class="icon-check"></i> makeDirTree
Creates a directory tree that starts from the root directory in the form of a (nested) dictionary. If a child directory is encountered during the traversal of the path, then the function recursively traverses down said child directory. Else, if a file is encountered during the traversal of the path, it is stored in the dictionary as it is under the appropriate directory.

#### <i class="icon-check"></i> wait
Receives connection from client on a non-conditional loop without processing any possible transmissions until the client sends an ‘OK’ signal.

#### <i class="icon-check-empty"></i> updateIndex
Creates an index of the server directory in the form of a dictionary.

#### <i class="icon-check-empty"></i> syncFromClient
You can delete the current document by clicking <i class="icon-trash"></i> **Delete document** in the document panel.

#### <i class="icon-check-empty"></i> syncToClient
You can delete the current document by clicking <i class="icon-trash"></i> **Delete document** in the document panel.

> **WorkerThread**
> describes sh*t.

#### <i class="icon-check-empty"></i> run
You can rename the current document by clicking the document title in the navigation bar.

> **ListenThread**
> describes the server mechanism in listening to any incoming connections from the client.

#### <i class="icon-check-empty"></i> run
You can rename the current document by clicking the document title in the navigation bar.

#### <i class="icon-check-empty"></i> displayThreads
You can rename the current document by clicking the document title in the navigation bar.
