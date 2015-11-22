Sync or Swim
===================

The only program that synchronizes your directories swimmingly!

----------


client.py
-------------
StackEdit stores your documents in your browser, which means all your documents are automatically saved locally and are accessible **offline!**

> **MainThread**
> describes the client mechanism in creating requests.

#### <i class="icon-check-empty"></i> run
Assigns an ID to a thread within a critical section.

#### <i class="icon-check-empty"></i> displayThreads
Prints out a list of threads.

#### <i class="icon-check-empty"></i> getIndex
You can rename the current document by clicking the document title in the navigation bar.

#### <i class="icon-check-empty"></i> syncFromServer
You can delete the current document by clicking <i class="icon-trash"></i> **Delete document** in the document panel.

#### <i class="icon-check-empty"></i> syncToServer
Traverses a predetermined path based on input and returns whether it is a directory or a file.

#### <i class="icon-check"></i> _update_index
Updates file indices within a directory based on input in the form of an index dictionary, excluding hidden directories and files.

#### <i class="icon-check"></i> get_nametype
Returns whether a predetermined path based on input is a directory or a file.

#### <i class="icon-check"></i> send
Sends all packages in the queue to be processed by the server, where the string '?magic?' is a makeshift codeword indicating that the transmission is terminated.

#### <i class="icon-check-empty"></i> receive
Creates a directory tree that starts from the root directory in the form of a (nested) dictionary. If a child directory is encountered during the traversal of the path, then the function recursively traverses down said child directory. Else, if a file is encountered during the traversal of the path, it is stored in the dictionary as it is under the appropriate directory.

#### <i class="icon-check"></i> wait
Receives connection from server on a non-conditional loop without processing any possible transmissions until the server sends an ‘OK’ signal.

#### <i class="icon-check-empty"></i> sendIndex
Creates an index of the server directory in the form of a dictionary.

#### <i class="icon-check"></i> recvIndex
Sends a request to get index and then returns the response of that request.

#### <i class="icon-check"></i> getDirTree
Returns a directory tree that starts from the root directory in the form of a (nested) dictionary. If a child directory is encountered during the traversal of the path, then the function recursively traverses down said child directory. Else, if a file is encountered during the traversal of the path, it is stored in the dictionary as it is under the appropriate directory.

#### <i class="icon-check"></i> recvDirTree
Sends a request to get directory tree and then returns the response of that request.

> **WorkerThread**
> describes sh*t.

#### <i class="icon-check-empty"></i> run
You can rename the current document by clicking the document title in the navigation bar.

----------


client_GUI.py
-------------
This Python program runs Sync or Swim's GUI for users' ease of access and readability.

> **LoginWindow**
> is the main window that users interact with in order to use the program. It first asks for the path of the directory that users would like to sync from, the IP address of the destination machine, and the port number.

#### <i class="icon-check"></i> storeEntry
Checks if all of the entries are valid before continuing on with the rest of the program. If not, then an exception will be raised, specifying to the user which error had occurred, and the program will not run.

> **AppWindow**
> The WorkerThread class describes sh*t.

#### <i class="icon-check-empty"></i> _index_to_array
You can rename the current document by clicking the document title in the navigation bar.

#### <i class="icon-check-empty"></i> _setup_widgets
Assigns an ID to a thread within a critical section.

#### <i class="icon-check-empty"></i> _build_tree
Assigns an ID to a thread within a critical section.

#### <i class="icon-check-empty"></i> sortby
Assigns an ID to a thread within a critical section.

#### <i class="icon-check-empty"></i> syncfrom
Assigns an ID to a thread within a critical section.

#### <i class="icon-check-empty"></i> syncto
Assigns an ID to a thread within a critical section.

#### <i class="icon-check-empty"></i> updatelocaltree
Assigns an ID to a thread within a critical section.

#### <i class="icon-check-empty"></i> updateservertree
Assigns an ID to a thread within a critical section.

----------


server.py
-------------
StackEdit stores your documents in your browser, which means all your documents are automatically saved locally and are accessible **offline!**

> **ClientThread**
> The ClientThread class describes the server mechanism in handling requests from the client.

#### <i class="icon-check"></i> run
Processes every thread that is received one at a time by determining which action to take based on the request code of the thread. The parsing of the threads continue until the TCP socket connection is closed or when a keyboard interrupt occurs.

#### <i class="icon-check-empty"></i> send
Sends. Once all the packages have been sent, the server would send 

#### <i class="icon-check-empty"></i> receive
You can delete the current document by clicking <i class="icon-trash"></i> **Delete document** in the document panel.

#### <i class="icon-check"></i> getNametype
Returns whether a predetermined path based on input is a directory or a file.

#### <i class="icon-check"></i> sendTime
Retrieves the date and time from the system and sends it as a package to the client.

#### <i class="icon-check"></i> sendIndex
Updates the server index and sends the updated index as a package to the client.

#### <i class="icon-check"></i> wait
Receives connection from client on a non-conditional loop without processing any possible transmissions until the client sends an ‘OK’ signal.

#### <i class="icon-check"></i> updateIndex
Updates file indices within the server directory in the form of a dictionary, excluding hidden directories and files.

#### <i class="icon-check-empty"></i> syncFromClient
You can delete the current document by clicking <i class="icon-trash"></i> **Delete document** in the document panel.

#### <i class="icon-check-empty"></i> syncToClient
You can delete the current document by clicking <i class="icon-trash"></i> **Delete document** in the document panel.

#### <i class="icon-check"></i> getID
Assigns an ID to a thread within a critical section.

> **WorkerThread**
> The WorkerThread class describes sh*t.

#### <i class="icon-check-empty"></i> run
You can rename the current document by clicking the document title in the navigation bar.

> **ListenThread**
> The ListenThread class describes the server mechanism in listening to any incoming connections from the client.

#### <i class="icon-check-empty"></i> run
You can rename the current document by clicking the document title in the navigation bar.

#### <i class="icon-check-empty"></i> displayThreads
You can rename the current document by clicking the document title in the navigation bar.
