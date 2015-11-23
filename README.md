Sync or Swim
===================

The only program that synchronizes your directories swimmingly!

Written by:
Irsyad Nabil 1406546134
Meta Andrini Utari 1406546153

Team 4 Participation:
Meta - 30%
Irsyad - 70%
Isaac - 0%
Amel - 0%

----------

INSTRUCTIONS
----------

Make sure that your device and the device you are going to sync to are connected to the Internet.

This program runs on Command Prompt (Windows) and Terminal (Linux). Executable binaries are located in /dist. Otherwise, run it in Python via command line or Python IDLE.

**Client-side**

1. Run the client side of Sync or Swim program.
2. Choose the folder the contents you would like to synchronize to another folder, and paste the directory path to the Directory box (e.g.: /Users/lepton/Desktop/test).
3. Paste the IP address of the destination device to the IP Address box (e.g.: 127.0.0.1 for local host).
4. Enter a port number you would like to connect to in the Port Number box.
5. The program has 6 processes you could choose from:
	- syncto, to sync the contents of the client directory to the server directory.
	- syncfrom, to sync the contents of the server directory to the client directory.
	- serverfiles, to list the contents of the server directory and provide the type of each individual content (file or directory) as well as its modification time.
	- clientfiles, to list the contents of the client directory and provide the type of each individual content (file or directory) as well as its modification time.
	- printthreads, to list all spawned threads.
	- exit, to exit the program.
6. Submit.

**Server-side**

1. Run the server side of Sync or Swim program.
2. Specify the destination folder the client would synchronize to and from (e.g.: /Users/lepton/Desktop/test2).
3. Wait until the client initiates connection.

----------

client.py
-------------

> **MainThread**
> describes the client mechanism in creating requests and processing server responses.

#### <i class="icon-check"></i> run
Updates the client index.

#### <i class="icon-check"></i> send
Sends all packages in the queue to the server within a critical condition so that the packages would be sent in order. The packages are byte-encoded, and the string '?magic?' is a makeshift codeword indicating the end of transmission.

#### <i class="icon-check"></i> receive
Receives incoming connection through socket. Packages are received through a 4096-byte buffer and the connection stops when a '?magic?' string is received. This function returns received packages in byte format.

#### <i class="icon-check"></i> updateIndex
Updates file indices within the client directory in the form of a dictionary, excluding hidden directories and files.

#### <i class="icon-check"></i> syncFromServer
Synchronizes the contents from the server directory to the client directory. First, it would send the client index to the server for comparison. If the job is to copy a file/directory, then it would store the corresponding file/directory from the server and append it with the job type to the job queue. Other job types are added to the job queue as is.

#### <i class="icon-check"></i> syncToServer
Synchronizes the contents from the client directory to the server directory. Since the client is "in charge" of handling the synchronizing, so to speak, this function is equipped to handle 3 primary cases:

1. A file/directory exists in server but not in client. In this case, the file/directory in question will be removed from the server directory.
2. A file/directory exists in client but not in server. In this case, the file/directory in question will be copied to the server directory.
3. A file/directory exists in both client and server. In this case, the modification time of the file/directory in question will be compared. The older copy of the two will be updated with the most recently modified copy.

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
> describes the mechanism of writing the changes made after synchronization unto the local (client) disk.

#### <i class="icon-check"></i> run
Iterates over the job queue and applies the changes to the client directory one by one.

----------


server.py
-------------

> **ClientThread**
> The ClientThread class describes the server mechanism in handling requests from the client.

#### <i class="icon-check"></i> run
Processes every thread that is received one at a time by determining which action to take based on the request code of the thread. The parsing of the threads continue until the TCP socket connection is closed or when a keyboard interrupt occurs.

#### <i class="icon-check"></i> send
Sends all packages in the queue to the client through an available socket. The packages are byte-encoded, and the string '?magic?' is a makeshift codeword indicating the end of transmission.

#### <i class="icon-check"></i> receive
Receives incoming connection through socket. Packages are received through a 4096-byte buffer and the connection stops when a '?magic?' string is received. This function returns received packages in byte form.

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

#### <i class="icon-check"></i> syncFromClient
Synchronizes the contents from the client directory to the server directory. First, it would send the server index to the client for comparison. If the job is to copy a file/directory, then it would store the corresponding file/directory from the client and append it with the job type to the job queue. Other job types are added to the job queue as is.

#### <i class="icon-check"></i> syncToClient
Synchronizes the contents from the server directory to the client directory. Since the server is "in charge" of handling the synchronizing, so to speak, this function is equipped to handle 3 primary cases:

1. A file/directory exists in client but not in server. In this case, the file/directory in question will be removed from the client directory.
2. A file/directory exists in server but not in client. In this case, the file/directory in question will be copied to the client directory.
3. A file/directory exists in both server and client. In this case, the modification time of the file/directory in question will be compared. The older copy of the two will be updated with the most recently modified copy.

#### <i class="icon-check"></i> getID
Assigns an ID to a thread within a critical section.

> **WorkerThread**
> describes the mechanism of writing the changes made after synchronization unto the remote (server) disk.

#### <i class="icon-check"></i> run
Iterates over the job queue and applies the changes to the server directory one by one.

> **ListenThread**
> describes the server mechanism in listening to any incoming connections from the client.

#### <i class="icon-check"></i> run
Listens for connections; and when there exist incoming connections from the client, it can handle up to 10 connections. In handling these connections, the function has to wait for an available socket before creating a new thread for them.

#### <i class="icon-check"></i> displayThreads
Prints out the details of all spawned threads, including an information of whether a thread is alive. The list of threads is sorted by their keys.
