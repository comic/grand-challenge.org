//message types, see mlabRemoteModuleMessages.h,  Message::MsgFirstUserMessage = 100


//=============================================================================
// Message Types
//=============================================================================
MLAB_MSG_GENERIC_REQUEST = '10';
MLAB_MSG_GENERIC_REPLY   = '11';
MLAB_MSG_OBJECT_DELETED  = '12';

MLAB_MSG_MODULE_CREATE               = '101';
MLAB_MSG_MODULE_INFO                 = '102';
MLAB_MSG_MODULE_SET_FIELD_VALUES     = '103';
MLAB_MSG_MODULE_LOG_MESSAGE          = '104';
MLAB_MSG_MODULE_SET_IMAGE_PROPERTIES = '105';
MLAB_MSG_MODULE_TILE_REQUEST         = '106';
MLAB_MSG_MODULE_TILE_DATA            = '107';
MLAB_MSG_MODULE_BASE_FIELD_TYPE      = '108';

MLAB_MSG_RENDERING_SLAVE_ADDED          = '1020';
MLAB_MSG_RENDERING_SLAVE_REMOVED        = '1021';
MLAB_MSG_RENDERING_SEND_QEVENT          = '1022';
MLAB_MSG_RENDERING_SET_RENDER_SIZE      = '1023';
MLAB_MSG_RENDERING_RENDER_REQUEST       = '1024';
MLAB_MSG_RENDERING_RENDER_SCENE_CHANGED = '1025';
MLAB_MSG_RENDERING_SEND_RENDER_IMAGE    = '1026';
MLAB_MSG_RENDERING_SET_CURSOR_SHAPE     = '1027';


//=============================================================================
// MLABRemoteManager
//=============================================================================
function MLABRemoteManager() {
  var self = this;
  
  this._lastRequestID = 1;
  this._activeResponseHandlers = new Object();
  
  this._webSocket = null;
  
  // callback functions
  //this._contextReadyCallback = null;
  this._connectionErrorCallback = null;
  this._connectedCallback = null;
  this._disconnectedCallback = null;
  this._messageReceivedCallback = null;

  this.setConnectedCallback = function(callback) { self._connectedCallback = callback; };
  this.setDiconnectedCallback = function(callback) { self._disconnectedCallback = callback; };
  this.setConnectionErrorCallback = function(callback) { self._connectionErrorCallback = callback; };
  this.setMessageReceivedCallback = function(callback) { self._messageReceivedCallback = callback; };
  
  this.unescapeMessage = function(message) {
    var unescaped = '';
    var p = message.indexOf('\\n');
    if (p == -1) {
      unescaped = message;
    } else {
      var p2 = 0;
      while (p != -1) {
        unescaped += message.substr(p2, p-p2);
        if (p+1 < message.length()) {
          var c = s.charAt(p+1);
          unescaped += (c == 'n' ? '\n' : c);
        }
        p2 = p+2;
        p = message.indexOf('\\', p2);
      }
      unescaped += message.substr(p2);
    }
    return unescaped;
  };

  
  this.escapeMessage = function(message) {
    return message.replace(/\\/g, '\\\\').replace(/\n/g, '\\n');
  };
  
  
  this.sendMessage = function(msgType, message) {
    self._webSocket.send(msgType + "\n" + message + "\n");
  }

  // calls the specified script function on the application module. arguments
  // is optional and must be a list if specified. responseHandler is also 
  // optional and is the callback that is called when the reply to this request
  // is received.
  this.sendGenericRequest = function(functionName, arguments, responseHandler) {
    var message = '';
    if (arguments && (arguments.length > 0)) {
      for (var i=0; i<arguments.length; i++) {
        message += "\n" + self.escapeMessage(JSON.stringify(arguments[i]));
      }
      message = arguments.length + message;
    }
    
    var requestID = 0;
    var objectID = 0;
    if (responseHandler) {
      var requestID = self._lastRequestID;
      self._lastRequestID += 1;
      self._activeResponseHandlers[requestID] = responseHandler;
    }
    
    if (message.length > 0) {
      message = functionName + "\n" + message;
    } else {
      message = functionName;
    }
    
    self.sendMessage(MLAB_MSG_GENERIC_REQUEST, requestID + "\n" + objectID + "\n" + message);
  };


  this.setup = function(socketUri) {
    if ("WebSocket" in window) {
      self._webSocket = new WebSocket(socketUri);
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
      var type = data[0];

      if (type == MLAB_MSG_GENERIC_REPLY) {
        var requestID = parseInt(data[1]);
        if (requestID in self._activeResponseHandlers) {
          var arguments = [];
          // skip last argument, which is always an empty string
          for (var i=2; i<data.length-1; i++) {
            arguments.push(JSON.parse(data[i]));
          }
          self._activeResponseHandlers[requestID](arguments);
          delete self._activeResponseHandlers[requestID];
        }
      } else {
        if (self._messageReceivedCallback) {
          var message = self.unescapeMessage(data[1]);
          self._messageReceivedCallback(type, message); 
        }
      }
    } catch(e) {
      self.logException(e);
    }
  };    

  
  this.handleConnectionError = function(message) { 
    if (self._connectionErrorCallback) { self._connectionErrorCallback(message); }
  };
  
  this.log = function(message) { self.sendGenericRequest("handleRemoteInfo", [message]); };
  this.logError = function(message) { console.log(message);/* self.sendGenericRequest("handleRemoteError", [message]);  */};
  
  this.logException = function(exception) {
    var message = '';
    if ('stack' in exception) {
      message = exception['stack']; 
    } else {
      for (var property in exception) {
        message += 'property: ' + property + ', value: "' + exception[property] + '"\n';
      }
      message += 'toString(): ' + ', value: ' + exception.toString();
    }
    self.logError(message);
  };
}
