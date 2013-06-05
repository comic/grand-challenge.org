/** \class MLAB.Core.ConnectionSettings
 * 
 * The settings for the web socket connection.
 * <p><tt>webSocketHostName</tt> and <tt>webSocketPort</tt> are used to establish the connection.</p>
 * <p><tt>application</tt> is required if the MeVisLab Worker Service
 * runs in proxy mode, so that it can decide from which installed application the worker process needs to 
 * be started.</p>
 * <p><tt>authToken</tt> is used in conjunction with <tt>application</tt> to do client authentication. The MeVisLab
 * Worker Service replaces the variables $(applicationName) and $(authenticationToken) in its authenticationRequestUrl.
 * The web server does the authentication and notifies the Worker Service about the result. If the authentication fails,
 * then the web socket connection is closed.</p><br><br>
 * 
 * The connection settings are:
 * \htmlonly
 * <table>
 *   <thead style="text-align: left;">
 *     <tr><th>name</th><th>type</th><th>default</th></tr>
 *   </thead>
 *   <tbody>
 *     <tr><td>webSocketHostName</td><td>HOSTNAME</td><td>window.location.hostname</td></tr>
 *     <tr><td>webSocketPort</td><td>INTEGER</td><td>read from http://<webSocketHostName>/Settings/webSocketPort</td></tr>
 *     <tr><td>application</td><td>STRING</td><td></td></tr>
 *     <tr><td>authToken</td><td>STRING</td><td></td></tr>
 *   </tbody>
 * </table>
 * \endhtmlonly
 */
MLAB.Core.defineClass("ConnectionSettings", {
  ConnectionSettings: function() {  
    this._webSocketHostName = null
    this._webSocketPort = null
    this._webSocketProtocol = null
    this._applicationName = null
    this._authenticationToken = null
  },
  
  setupFromArguments: function(args) {
    // detect web socket hostname
    this._webSocketHostName = "webSocketHostName" in args ? args["webSocketHostName"] : null    
    if (!this._webSocketHostName) { this._webSocketHostName = window.location.hostname }
    if (!this._webSocketHostName) { this._webSocketHostName = "127.0.0.1" }

    // detect web socket port
    this._webSocketPort = "webSocketPort" in args ? args["webSocketPort"] : null
    if (!this._webSocketPort) {
      var httpUrl = window.location.protocol + "//" + this._webSocketHostName
      var httpPort = window.location.port
      if (httpPort) { httpUrl = httpUrl + ":" + httpPort }
      this._webSocketPort = this._getWebSocketPortFromWorkerService(httpUrl)
    }
    
    // detect web socket protocol
    this._webSocketProtocol = "ws://"
    if (window.location.protocol === "https:") { this._webSocketProtocol = "wss://" }
    
    // detect application
    if ("application" in args) {
      this._applicationName = args["application"]
    } else {
      // auto-detect application name, this works with the WorkerService web server
      var parts = window.location.pathname.split('/')
      if (parts.length > 3) {
        if (parts[1] === "Applications") {
          this._applicationName = parts[2]
        }
      }
    }
    
    if ("authToken" in args) {
      this._authenticationToken = args["authToken"]
    }
  },
  
  /** \fn MLAB.Core.ConnectionSettings.getWebSocketHostName
   * Returns the web socket hostname. See also MLAB.Core.RemoteManager.openConnection().
   * @return Returns the web socket hostname, or null if it was not set with setWebSocketHostName().
   */
  getWebSocketHostName: function() { return this._webSocketHostName },
  
  /** \fn MLAB.Core.ConnectionSettings.getWebSocketPort
   * 
   * Returns the web socket port. See also MLAB.Core.RemoteManager.openConnection().
   * @return Returns the web socket port, or null if it was not set with setWebSocketPort().
   */
  getWebSocketPort: function() { return this._webSocketPort },
  
  /** \fn MLAB.Core.ConnectionSettings.getWebSocketProtocol
   * 
   * Returns the web socket protocol. The protocol is "wss://" if window.location.protocol is "https:",
   * "ws://" otherwise.
   */
  getWebSocketProtocol: function() { return this._webSocketProtocol },
  
  /** \fn MLAB.Core.ConnectionSettings._getWebSocketPortFromWorkerService
   * 
   * Retrieves the web socket port from the MeVisLabWorkerService http server. It uses the following url for this:
   * \code window.location.protocol + "//" + hostname + ":" + window.location.port + "/Settings/webSocketPort" \endcode
   * @return Returns the retrieved web socket port, or 4114 if the request had failed.
   */
  _getWebSocketPortFromWorkerService: function(httpUrl) {
    var port = "4114"
    var request = new XMLHttpRequest()
    // do a synchronous request, because we need to know the web socket port now
    request.open("GET", httpUrl + "/Settings/webSocketPort", false)
    request.onreadystatechange = function() {
      if (request.readyState==4) {
        port = request.responseText
      }
    }
    request.send(null)
    return port
  },
  
  /** \fn MLAB.Core.ConnectionSettings.getApplicationName
   * 
   * Returns the application name.
   * 
   * \return Returns the application name, or null if it is not set.
   */
  getApplicationName: function() { return this._applicationName },
  
  /** \fn MLAB.Core.ConnectionSettings.getAuthenticationToken
   * 
   * Returns the authentication token.
   * 
   * \return Returns the authentication token, or null if it is not set.
   */
  getAuthenticationToken: function() { return this._authenticationToken },
})


/** \class MLAB.Core.ResponseHandler
 * 
 * This response handles responses of generic requests that are
 * send to the MeVisLab process with MLAB.Core.RemoteManager.sendGenericRequest(). 
 * It is created with two callback functions. The
 * response handler is used in handleResponse(). If handleResponse() is 
 * not called during the next 5000 milliseconds, then the timeout callback
 * is called.
 * 
 * \param responseHandler
 * \param timeoutCallback
 */
MLAB.Core.defineClass("ResponseHandler", {
  ResponseHandler: function(responseHandler, timeoutCallback, remoteManager) {  
    this._responseHandler = responseHandler
    this._timeoutId = window.setTimeout(timeoutCallback, 5000)
    this._remoteManager = remoteManager
  },
  
  /** \fn MLAB.Core.ResponseHandler.handleResponse
   * 
   * Clears the timeout timer and calls the responser handler callback with the given arguments.
   * MLAB.Core.RemoteManager.handleMessageReceived() calls this method.
   * 
   * \param arguments The arguments list from the response.
   */
  handleResponse: function(args) {
    try {
      window.clearTimeout(this._timeoutId)
    } catch (e) {
      remoteManager.logException(e)
    }
    try {
      this._responseHandler(args)
    } catch (e) {
      this._remoteManager.logException(e)
    }
  },
})


/** \class MLAB.Core.RemoteManager
 * 
 * \defgroup RemoteManagerCallbacks
 */
MLAB.Core.defineClass("RemoteManager", {
  RemoteManager: function() {
    this._debugMessages = false
    this._consoleLogger = null
    this._supportedRemoteProtocolVersion = 1
    
    this._lastRequestID = 1
    this._activeResponseHandlers = new Object()
    
    this._webSocket = null
    
    // callback functions
    this._connectionErrorCallback = null
    this._connectedCallback = null
    this._disconnectedCallback = null
    this._messageReceivedCallback = null
  },
  
  setDebugMessages: function(flag) { this._debugMessages = flag },
  
  setConsoleLogger: function(logger) { this._consoleLogger = logger },

  /** \fn MLAB.Core.RemoteManager.setConnectedCallback
   * 
   * Sets the callback that is called after the web socket connection is established.
   * \ingroup RemoteManagerCallbacks
   */
  setConnectedCallback: function(callback) { this._connectedCallback = callback },
  
  /** \fn MLAB.Core.RemoteManager.setDisconnectedCallback
   * 
   * Sets the callback that is called after the web socket connection is closed.
   * \ingroup RemoteManagerCallbacks
   */
  setDisconnectedCallback: function(callback) { this._disconnectedCallback = callback },
  
  /** \fn MLAB.Core.RemoteManager.setConnectionErrorCallback
   * 
   * Sets the callback that is called when an error occurs when creating the web socket connection.
   * \ingroup RemoteManagerCallbacks
   */
  setConnectionErrorCallback: function(callback) { this._connectionErrorCallback = callback },
  
  /** \fn MLAB.Core.RemoteManager.setMessageReceivedCallback
   * 
   * Sets the callback that is called when a message is received by the web socket.
   * 
   * \param callback The function that is to be used as the message received callback. The function
   *                 is called with the message object as only argument.
   * See \ref RemoteMessages
   * 
   * \ingroup RemoteManagerCallbacks
   */
  setMessageReceivedCallback: function(callback) { this._messageReceivedCallback = callback },
  
  /** \fn MLAB.Core.RemoteManager.sendMessage
   * 
   * Sends the given message to the connected MeVisLab process via the web socket.
   * 
   * \param message The message must be an object that has a serialize() method to serialize it and
   *                a toString() method if remote message debugging is enabled to print it in the console.
   */
  sendMessage: function(message) {
    if (this._debugMessages) {
      this._consoleLogger.logConsoleMessage("< Send      " + this.trimConsoleMessage(message.toString()))
    }
    this._webSocket.send(message.serialize())
  },

  /** \fn MLAB.Core.RemoteManager.sendGenericRequest
   * 
   * Calls the script function named by functionName on the application module. 
   * Creates a unique request ID and MLAB.Core.ResponseHandler internally if a response handler is given.  
   * 
   * \param functionName The name of the script function of the application module.
   * \param arguments An optional list of arguments that are passed to the called script function.
   * \param responseHandler An optional callback function that is called when the reply to this request is received.
   */
  sendGenericRequest: function(functionName, args, responseHandler) {
    var requestID = 0
    var objectID = 0
    if (responseHandler) {
      requestID = this._lastRequestID
      this._lastRequestID += 1
      this._activeResponseHandlers[requestID] = new MLAB.Core.ResponseHandler(responseHandler, 
                                                                               (function() { this._requestTimedOut(requestID, functionName, args) }).bind(this),
                                                                               this)
    }
    
    var request = new MLAB.Core.GenericRequest()
    request.setData({requestID: requestID, objectID: objectID, functionName: functionName, arguments: args})
    this.sendMessage(request)
  },

  /** \fn MLAB.Core.RemoteManager._requestTimedOut
   * 
   * This method is used as a callback when waiting for a response times out. It logs an error then.
   * See also MLAB.Core.ResponseHandler.
   * 
   * \param requestID The ID of the request that timed out.
   * \param functionName The name of the function that is called in the MeVisLab process. 
   * \param arguments This is the argument list of the generic request.
   */
  _requestTimedOut: function(requestID, functionName, args) {
    this.logError("Request timed out: " + requestID + ", " + functionName + ", " + args)
  },
  
  /** \fn MLAB.Core.RemoteManager.connect
   * Establishes the web socket connection to MeVisLab on the server.
   * The hostname and port for the web socket connection is determined in the following order:
   * <table>
   *   <tr><td valign="top">hostname</td><td valign="top">
   *     <ol>
   *       <li>MLAB.Core.ConnectionSettings.getWebSocketHostName()</li>
   *       <li>window.location.hostname</li>
   *       <li>127.0.0.1</li>
   *     </ol>
   *   </td></tr>
   *   <tr><td valign="top">port</td><td valign="top">
   *     <ol>
   *       <li>MLAB.Core.ConnectionSettings.getWebSocketPort()</li>
   *       <li>MLAB.Core.RemoteManager.getWebSocketPort()</li>
   *     </ol>
   *   </td></tr>
   * </table>
   *
   * The web socket protocol, \e ws or \e wss, is determined by MLAB.Core.ConnectionSettings.getWebSocketProtocol().
   * If that functions returns no value, then the web socket protocol is derived from
   * window.location.protocol: \e http results in \e ws and \e https in \e wss.<br>
   * 
   * \param connectionSettings An MLAB.Core.ConnectionSettings object.
   */
  openConnection: function(connectionSettings) {
    var hostname = connectionSettings.getWebSocketHostName()
    var port = connectionSettings.getWebSocketPort()
    var protocol = connectionSettings.getWebSocketProtocol()
    
    var applicationName = connectionSettings.getApplicationName()
    var authToken = connectionSettings.getAuthenticationToken()
    var socketUri = protocol + hostname + ":" + port + "/mlab4d4c4142/" + applicationName + "/" + authToken
    try {
      this.closeConnection()
      this._setup(socketUri)
    } catch (e) {
      this.logException(e)
    }
  },
  
  /** \fn MLAB.Core.RemoteManager.disconnect
   * 
   * Closes the web socket connection.
   */
  closeConnection: function() { 
    if (this._webSocket) { 
      this._webSocket.close()
      this._webSocket = null
    } 
  },

  /** \fn MLAB.Core.RemoteManager._setup
   * 
   * Creates the web socket and registers callbacks on it.
   */
  _setup: function(socketUri) {
    // ako: enhance check, since Android can have a WebSocket browser plugin.
    if ("WebSocket" in window || "MozWebSocket" in window) {
      if ("MozWebSocket" in window) {
          // Firefox 6.0 uses a prefixed name:
        this._webSocket = new MozWebSocket(socketUri)
      } else {
        this._webSocket = new WebSocket(socketUri)
      }
      if ("binaryType" in this._webSocket) {
        // being cautious: was this supported from the start?
        this._webSocket.binaryType = "arraybuffer"
      }
      this._webSocket.onopen  = this.callback("handleConnected")
      this._webSocket.onclose = this.callback("handleDisconnected")
      this._webSocket.onerror   = this.callback("handleConnectionError")
      this._webSocket.onmessage = this.callback("handleMessageReceived")
    } else {
      MLAB.Core.throwException("Neither WebSockets nor Flash emulation supported here!")
    }
  },
  
  /** \fn MLAB.Core.RemoteManager.handleDisconnect
   * 
   *  This method is called directly after the remote manager is disconnected. If the disconnected callback is set,
   *  then it is called by this function.
   *  \see setDiconnectedCallback()
   */
  handleDisconnected: function(ev) {
    if (this._disconnectedCallback) { this._disconnectedCallback(ev) } 
  },

  
  /** \fn MLAB.Core.RemoteManager.handleDisconnect
   * 
   *  This method is called directly after the remote manager is connected. If the connected callback is set,
   *  then it is called by this function.
   *  \see setConnectedCallback()
   */
  handleConnected: function(ev) {
    if (this._connectedCallback) { this._connectedCallback(ev) }
  },

  /** \fn MLAB.Core.RemoteManager.handleMessageReceived
   * 
   * This method is used as the web socket onmessage callback. It reads
   * the message type and creates a corresponding message object from the data.
   * 
   * See \ref RemoteMessages for the list of available messages.
   * 
   * \param messageEvent The message event from the web socket.
   */
  handleMessageReceived: function(messageEvent) {
    try {
      var type = 0
      var binaryMessage = false
      if (typeof(messageEvent.data) === "string") {
        var data = messageEvent.data.split('\n')
        // pop the last empty data entry, since all MeVisLab messages end with a trailing \n
        data.pop()
        
        type = data.shift()

        if (this._debugMessages) {
          if (console) {
            var m = data.slice(0)
            m.unshift(MLAB.Core.getMessageTypeName(type))
            this._consoleLogger.logConsoleMessage("> Received  " + this.trimConsoleMessage(m.join('\n')))
          }
        }
      } else {
        var stream = new MLAB.Core.BinaryDataStream(messageEvent.data)
        binaryMessage = true
        
        type = stream.readUInt32()

        if (this._debugMessages) {
          if (console) {
            this._consoleLogger.logConsoleMessage("> Received binary message " + MLAB.Core.getMessageTypeName(type))
          }
        }
      }
      
      var messageClass = MLAB.Core.remoteMessageClassMap[type]
      if (messageClass) {
        var message = new messageClass()
        if (binaryMessage) {
          message.readBinary(stream)
        } else {
          message.read(data)
        }
        
        switch (message.type) {
        
        case MLAB.Core.MSG_MODULE_VERSION:
          if (message.version !== this._supportedRemoteProtocolVersion) {
            this.logError("Server implements remote protocol version " + message.version +
                          ".\nThis client supports version " + this._supportedRemoteProtocolVersion + ".")
          }
          break
          
        case MLAB.Core.MSG_GENERIC_REPLY:
          if (message.requestID in this._activeResponseHandlers) {
            var responseHandler = this._activeResponseHandlers[message.requestID]
            responseHandler.handleResponse(message.arguments)
            delete this._activeResponseHandlers[message.requestID]
          } else if (this._debugMessages) {
            this.logError("No repsonse handler for generic reply set: " + message.requestID)
          }
          break
        
        default:
          if (this._messageReceivedCallback) {          
            this._messageReceivedCallback(message)
          }
        }
      } else {
        this.logError("Unknown message received: " + type)
      }
    } catch(e) {
      this.logException(e)
    }
  },
  
  /** \fn MLAB.Core.RemoteManager.handleConnectionError
   * 
   * The web socket's onerror handler. Calls the callback set with setConnectionErrorCallback().
   */
  handleConnectionError: function(ev) { 
    if (this._connectionErrorCallback) { this._connectionErrorCallback(ev) }
  },
  
  /** \fn MLAB.Core.RemoteManager.log
   * 
   * Sends the given log message to the MeVisLab process. It will appear in the MeVisLab logfile.
   * 
   * \param message The message string.
   * \param prefix Optional prefix that is prepended to the message.
   */
  log: function(message, prefix) {
    if (!prefix) { prefix = "" } else { prefix += " " }
    this.sendGenericRequest("handleRemoteInfo", [prefix + message])
  },
  
  /** \fn MLAB.Core.RemoteManager.logError
   * 
   * Same as log(), except that the message is treated as an error.
   * 
   * \param message The error string.
   * \param prefix Optional prefix that is prepended to the message.
   */
  logError: function(message, prefix) {
    this._consoleLogger.logConsoleError(message)
    if (!prefix) { prefix = "" } else { prefix += " " }
    this.sendGenericRequest("handleRemoteError", [prefix + message])
  },
  
  /** \fn MLAB.Core.RemoteManager.logException
   * 
   * Same as logError(), except that an exception instead of an message is expected.
   * 
   * \param exception The exception.
   * \param prefix Optional prefix that is prepended to the exception message.
   */
  logException: function(exception, prefix) {
    this._consoleLogger.logConsoleError(exception)
    var message = ''
    if (!exception) {
      MLAB.Core.throwException("Cannot log invalid exception: " + exception)
      return
    }
    if (typeof(exception) === "string") {
      message = exception
    } else if (('stack' in exception) && exception['stack']) {
      message = exception.message + "\n" + exception['stack']
    } else {
      message = 'Exception:\n'
      for (var property in exception) {
        message += property + ': ' + exception[property] + '\n'
      }
      message += 'toString(): ' + exception.toString()
    }
    this.logError(message, prefix)
  },
  
  trimConsoleMessage: function(message) {
    var s = message.replace(/\n/g, ",  ")
    if (s.length > 120) {
      s = s.substr(0, 120) + "   [...]"
    }
    return s
  },
})
