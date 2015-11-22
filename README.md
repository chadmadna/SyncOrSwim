Sync or Swim
===================

The only program that synchronizes your directories swimmingly!

----------

Written by:
Irsyad Nabil 1406546134
Meta Andrini Utari 1406546153

Team 4 Participation:
Meta - 50%
Irsyad - 50%
Isaac - 0%
Amel - 0%

client.py
-------------

> **MainThread**
> describes the client mechanism in creating requests and processing server responses.

#### <i class="icon-check"></i> run
Updates the client index, and notifies that the main thread is running and ready to receive requests/responses.

#### <i class="icon-check"></i> send
Sends all packages in the queue to be processed by the server, where the string '?magic?' is a makeshift codeword indicating the end of transmission.

#### <i class="icon-check-empty"></i> receive
Creates a directory tree that starts from the root directory in the form of a (nested) dictionary. If a child directory is encountered during the traversal of the path, then the function recursively traverses down said child directory. Else, if a file is encountered during the traversal of the path, it is stored in the dictionary as it is under the appropriate directory.

#### <i class="icon-check"></i> updateIndex
Updates file indices within the client directory in the form of a dictionary, excluding hidden directories and files.

#### <i class="icon-check-empty"></i> syncFromServer
You can delete the current document by clicking <i class="icon-trash"></i> **Delete document** in the document panel.

#### <i class="icon-check-empty"></i> syncToServer
Traverses a predetermined path based on input and returns whether it is a directory or a file.

#### <i class="icon-check"></i> getNametype
Returns whether a predetermined path based on input is a directory or a file.

#### <i class="icon-check"></i> wait
Receives connection from server on a non-conditional loop without processing any possible transmissions until the server sends an ‘OK’ signal.

#### <i class="icon-check"></i> getIndex
Updates client index, sends a request for server index, and then returns both client and server indices.

#### <i class="icon-check"></i> sendIndex
Sends client index as a dump package to the server.

#### <i class="icon-check"></i> displayThreads
Prints out the details of all spawned threads, including an information of whether a thread is alive. The list of threads is sorted by their keys.

> **WorkerThread**
> describes the mechanism of writing the changes made after synchronization unto the local disk.

#### <i class="icon-check"></i> run
Iterates over the job queue and applies the changes to the client directory.

----------


client_GUI.py
-------------

> **LoginWindow**
> is the main window that users interact with in order to use the program. It first asks for the path of the directory that users would like to sync from, the IP address of the destination machine, and the port number.

#### <i class="icon-check"></i> storeEntry
Checks if all of the entries are valid before continuing on with the rest of the program. If not, then an exception will be raised, specifying to the user which error had occurred, and the program will not run.

> **AppWindow**
> displays the details of the synchronization process to the user, in the form of 2 frames side-by-side: the client frame and the server frame. Both frames list the content of both directories as synchronization takes place.

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
Updates the server index and sends the updated index as a dump package to the client.

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
> Performs file operations and writes received data from the job queue to the local directory.

#### <i class="icon-check-empty"></i> run
You can rename the current document by clicking the document title in the navigation bar.

> **ListenThread**
> describes the server mechanism in listening to any incoming connections from the client.

#### <i class="icon-check"></i> run
Listens for connections; and when there exist incoming connections from the client, it can handle up to 10 connections. In handling these connections, the function has to wait for an available socket before creating a new thread for them.

#### <i class="icon-check"></i> displayThreads
Prints out the details of all spawned threads, including an information of whether a thread is alive. The list of threads is sorted by their keys.
