//=============================================================================
// MLABResponseHandler
//=============================================================================
function MLABResponseHandler(responseHandler, timeoutCallback) {
  var self = this;
  
  this._responseHandler = responseHandler;
  this._timeoutId = window.setTimeout(timeoutCallback, 5000);
  
  this.handleResponse = function(arguments) {
    try {
      window.clearTimeout(self._timeoutId);
    } catch (e) {
      gApp.logException(e);
    }
    try {
      self._responseHandler(arguments);
    } catch (e) {
      gApp.logException(e);
    }
  };
}


//=============================================================================
// MLABRemoteManager
//=============================================================================
function MLABRemoteManager() {
  var self = this;
  
  this.debugMessages = false; 
  
  this.supportedRemoteProtocolVersion = 1;
  
  this._lastRequestID = 1;
  this._activeResponseHandlers = new Object();
  
  this._webSocket = null;
  
  // callback functions
  this._connectionErrorCallback = null;
  this._connectedCallback = null;
  this._disconnectedCallback = null;
  this._messageReceivedCallback = null;

  this.setConnectedCallback = function(callback) { self._connectedCallback = callback; };
  this.setDiconnectedCallback = function(callback) { self._disconnectedCallback = callback; };
  this.setConnectionErrorCallback = function(callback) { self._connectionErrorCallback = callback; };
  this.setMessageReceivedCallback = function(callback) { self._messageReceivedCallback = callback; };
  
  this.sendMessage = function(message, responseHandler) {
    var requestID = 0;
    if (responseHandler) {
      requestID = self._lastRequestID;
      self._lastRequestID += 1;
      self._activeResponseHandlers[requestID] = new MLABResponseHandler(responseHandler, 
                                                                        function() { self._requestTimedOut(requestID, functionName, arguments); });
    }
    if (self.debugMessages) {
      console.log("< Send      " + mlabTrimConsoleMessage(message.toString()));
    }
    self._webSocket.send(message.serialize()); 
  }

  // calls the specified script function on the application module. arguments
  // is optional and must be a list if specified. responseHandler is also 
  // optional and is the callback that is called when the reply to this request
  // is received.
  this.sendGenericRequest = function(functionName, arguments, responseHandler) {
    var requestID = 0;
    var objectID = 0;
    if (responseHandler) {
      requestID = self._lastRequestID;
      self._lastRequestID += 1;
      self._activeResponseHandlers[requestID] = new MLABResponseHandler(responseHandler, 
                                                                        function() { self._requestTimedOut(requestID, functionName, arguments); });
    }
    
    var request = new MLABGenericRequest();
    request.setData(requestID, objectID, functionName, arguments);
    self.sendMessage(request);
  };
  
  this._requestTimedOut = function(requestID, functionName, arguments) {
    self.logError("Request timed out: " + requestID + ", " + functionName + ", " + arguments);
  };

  this.setup = function(socketUri) {
    // ako: enhance check, since Android can have a WebSocket browser plugin.
    if ("WebSocket" in window || "MozWebSocket" in window) {
      if ("MozWebSocket" in window) {
          // Firefox 6.0 uses a prefixed name:
        self._webSocket = new MozWebSocket(socketUri);
      } else {
        self._webSocket = new WebSocket(socketUri);
      }
      self._webSocket.onopen  = function() { self.handleConnected(); };
      self._webSocket.onclose = function() { self.handleDisconnected(); };
      self._webSocket.onerror   = function(message) { self.handleConnectionError(message); };
      self._webSocket.onmessage = function(message) { self.handleMessageReceived(message); };
    } else {
      app.showError("Neither WebSockets nor Flash emulation supported here!\n\nBrowser: " + navigator.appName + " " +
                    navigator.appVersion);
    }
  };

  
  this.close = function() {
    if (self._webSocket) { self._webSocket.close(); }
  };
  
  
  this.handleDisconnected = function() { 
    if (self._disconnectedCallback) { self._disconnectedCallback(); } 
  };

  
  this.handleConnected = function() {
    if (self._connectedCallback) { self._connectedCallback(); }
  };

  
  this.handleMessageReceived = function(messageEvent) {
    try {
      var data = messageEvent.data.split('\n');
      var type = data.shift();
      
      if (self.debugMessages) {
        if (console) {
          var m = data.slice(0);          
          m.unshift(mlabGetMessageTypeName(type));
          console.log("> Received  " + mlabTrimConsoleMessage(m.join('\n')));
        }
      }

      var messageClass = gMessageClassMap[type];
      if (messageClass) {
        var message = new messageClass();
        message.read(data);
        
        switch (message.type) {
        
        case MLAB_MSG_MODULE_VERSION:
          if (message.version != this.supportedRemoteProtocolVersion) {
            gApp.showError("Server implements remote protocol version " + message.version +
                            ".\nThis client supports version " + this.supportedRemoteProtocolVersion + ".");
          }
          break;
          
        case MLAB_MSG_GENERIC_REPLY:
          if (message.requestID in self._activeResponseHandlers) {
            try {
              var responseHandler = self._activeResponseHandlers[message.requestID];
              responseHandler.handleResponse(message.arguments);
            } catch(e) {
              self.logError("Failed to execute callback:\n" + callback);
              self.logException(e);
            }
            delete self._activeResponseHandlers[message.requestID];
          } else if (self.debugMessages) {
            self.logError("No repsonse handler for generic reply set: " + message.requestID);
          }
          break;
        
        default:
          if (self._messageReceivedCallback) {          
            self._messageReceivedCallback(message);
          }
        }
      } else {
        self.logError("Unknown message received: " + type);
      }
    } catch(e) {
      self.logException("MLABRemoteManager", e);
    }
  };    

  
  this.handleConnectionError = function(message) { 
    if (self._connectionErrorCallback) { self._connectionErrorCallback(message); }
  };
  
  this.log = function(prefix, message, formatAsHTML) { 
    var m = prefix + ": " + message;
    self.sendGenericRequest("handleRemoteInfo", [formatAsHTML ? m.replace(/\n/g, '<br>').replace(/\s/g, '&nbsp;') : m]); 
  };
  
  this.logError = function(prefix, message, formatAsHTML) {
    console.log(message);
    var m = prefix + ": " + message;
    self.sendGenericRequest("handleRemoteError", [formatAsHTML ? m.replace(/\n/g, '<br>').replace(/\s/g, '&nbsp;') : m]);
  };
  
  this.logException = function(prefix, exception, formatAsHTML) {
    console.log(exception);
    var message = '';
    if (!exception) {
      mlabThrowException("Cannot log invalid exception: " + exception);
      return;
    }
    if (typeof(exception) == "string") {
      message = exception;
    } else if (('stack' in exception) && exception['stack']) {
      message = exception['stack']; 
    } else {
      message = 'Exception:\n';
      for (var property in exception) {
        message += property + ': ' + exception[property] + '\n';
      }
      message += 'toString(): ' + exception.toString();
    }
    self.logError(prefix, message, formatAsHTML);
  };
}
