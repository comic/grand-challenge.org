//=============================================================================
// Message types
//=============================================================================
MLAB_MSG_GENERIC_REQUEST = '10';
MLAB_MSG_GENERIC_REPLY   = '11';
MLAB_MSG_OBJECT_DELETED  = '12';

MLAB_MSG_MODULE_VERSION              = '100';
MLAB_MSG_MODULE_CREATE               = '101';
MLAB_MSG_MODULE_INFO                 = '102';
MLAB_MSG_MODULE_SET_FIELD_VALUES     = '103';
MLAB_MSG_MODULE_LOG_MESSAGE          = '104';
MLAB_MSG_MODULE_SET_IMAGE_PROPERTIES = '105';
MLAB_MSG_MODULE_TILE_REQUEST         = '106';
MLAB_MSG_MODULE_TILE_DATA            = '107';
MLAB_MSG_MODULE_BASE_FIELD_TYPE      = '108';
MLAB_MSG_MODULE_SHOW_IDE             = '109';
MLAB_MSG_MODULE_PROCESS_INFORMATION  = '110';

MLAB_MSG_RENDERING_SLAVE_ADDED          = '1020';
MLAB_MSG_RENDERING_SLAVE_REMOVED        = '1021';
MLAB_MSG_RENDERING_QEVENT               = '1022';
MLAB_MSG_RENDERING_SET_RENDER_SIZE      = '1023';
MLAB_MSG_RENDERING_RENDER_REQUEST       = '1024';
MLAB_MSG_RENDERING_RENDER_SCENE_CHANGED = '1025';
MLAB_MSG_RENDERING_RENDERED_IMAGE       = '1026';
MLAB_MSG_RENDERING_SET_CURSOR_SHAPE     = '1027';
MLAB_MSG_RENDERING_SET_SIZE_HINTS       = '1028';
MLAB_MSG_RENDERING_RENDERED_IMAGE_ACKNOWLEDGE = '1029';
MLAB_MSG_RENDERING_RENDER_START_STREAMING = '1030';
MLAB_MSG_RENDERING_RENDER_STOP_STREAMING  = '1031';
MLAB_MSG_RENDERING_SET_STREAMING_QUALITY  = '1032';

MLAB_MSG_ITEM_MODEL_ATTRIBUTES     = '1050';
MLAB_MSG_ITEM_MODEL_ITEM_CHANGED   = '1051';
MLAB_MSG_ITEM_MODEL_ITEMS_INSERTED = '1052';
MLAB_MSG_ITEM_MODEL_ITEMS_REMOVED  = '1053';
MLAB_MSG_ITEM_MODEL_DATA_CHANGED   = '1054';
MLAB_MSG_ITEM_MODEL_GET_CHILDREN   = '1055';


function mlabGetMessageTypeName(msgType) {
  switch (msgType) {
    case '10': return 'GENERIC_REQUEST';
    case '11': return 'GENERIC_REPLY  ';
    case '12': return 'OBJECT_DELETED ';
    
    case '100': return 'MODULE_VERSION             ';
    case '101': return 'MODULE_CREATE              ';
    case '102': return 'MODULE_INFO                ';
    case '103': return 'MODULE_SET_FIELD_VALUES    ';
    case '104': return 'MODULE_LOG_MESSAGE         ';
    case '105': return 'MODULE_SET_IMAGE_PROPERTIES';
    case '106': return 'MODULE_TILE_REQUEST        ';
    case '107': return 'MODULE_TILE_DATA           ';
    case '108': return 'MODULE_BASE_FIELD_TYPE     ';
    case '109': return 'MODULE_SHOW_IDE            ';
    case '110': return 'MODULE_PROCESS_INFORMATION ';
    
    case '1020': return 'RENDERING_SLAVE_ADDED             ';
    case '1021': return 'RENDERING_SLAVE_REMOVED           ';
    case '1022': return 'RENDERING_QEVENT                  ';
    case '1023': return 'RENDERING_SET_RENDER_SIZE         ';
    case '1024': return 'RENDERING_RENDER_REQUEST          ';
    case '1025': return 'RENDERING_RENDER_SCENE_CHANGED    ';
    case '1026': return 'RENDERING_RENDERED_IMAGE          ';
    case '1027': return 'RENDERING_SET_CURSOR_SHAPE        ';
    case '1028': return 'RENDERING_SET_SIZE_HINTS          ';
    case '1029': return 'RENDERING_RENDERED_IMAGE_ACKNOWLEDGE';
    case '1030': return 'RENDERING_RENDER_START_STREAMING';
    case '1031': return 'RENDERING_RENDER_STOP_STREAMING';
      
    case '1050': return 'MLAB_MSG_ITEM_MODEL_ATTRIBUTES    ';
    case '1051': return 'MLAB_MSG_ITEM_MODEL_ITEM_CHANGED  ';
    case '1052': return 'MLAB_MSG_ITEM_MODEL_ITEMS_INSERTED';
    case '1053': return 'MLAB_MSG_ITEM_MODEL_ITEMS_REMOVED ';
    case '1054': return 'MLAB_MSG_ITEM_MODEL_DATA_CHANGED  ';
    case '1055': return 'MLAB_MSG_ITEM_MODEL_GET_CHILDREN  ';
  }
  return "UNKNOWN_MESSAGE_TYPE(" + msgType + ")";
}


//=============================================================================
// MLABRemoteMessage
//=============================================================================
function MLABRemoteMessage(type) {
  var self = this;
  
  this.type = type;
  
  this.unescape = function(s) {
    return s.replace(/\\\\/g, '\\').replace(/\\n/g, '\n');
    var unescaped = '';
    var p = s.indexOf('\\n');
    if (p == -1) {
      unescaped = s;
    } else {
      var p2 = 0;
      while (p != -1) {
        unescaped += s.substr(p2, p-p2);
        if (p+1 < s.length) {
          var c = s.charAt(p+1);
          unescaped += (c == 'n' ? '\n' : c);
        }
        p2 = p+2;
        p = s.indexOf('\\', p2);
      }
      unescaped += s.substr(p2);
    }
    return unescaped;
  };
  
  this.escape = function(s) {
    return s.replace(/\\/g, '\\\\').replace(/\n/g, '\\n');
  };
  
  this.read = function(data) {
    self.data = data;    
  };
  
  this.setData = function(data) {
    self.data = data;    
  };
  
  this.toString = function() {
    var message = mlabGetMessageTypeName(self.type) + "\n";
    for (var i=0; i<self.data.length; i++) {
      message += self.data[i] + "\n";
    }
    return message;
  };
  
  this.serialize = function() {
    var message = self.type + "\n";
    for (var i=0; i<self.data.length; i++) {
      message += self.data[i] + "\n";
    }
    return message;
  };
}


//=============================================================================
// MLABGenericReply
//=============================================================================
function MLABGenericReply() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_GENERIC_REPLY);
  
  this.read = function(data) {
    self.requestID = parseInt(data.shift());
    self.arguments = [];
    // skip last argument, which is always an empty string
    // TODO: do correct unescaping here! it is currently not clear if unescaping
    // must be done before or after json parsing
    for (var i=0; i<data.length-1; i++) {
      self.arguments.push(JSON.parse(data[i]));
    }
  }
}


//=============================================================================
// MLABGenericRequest
//=============================================================================
function MLABGenericRequest() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_GENERIC_REQUEST);
  
  this.setData = function(requestID, objectID, functionName, arguments) {
    self.data = [requestID, objectID, functionName];
    
    if (arguments && (arguments.length > 0)) {
      self.data.push(arguments.length);
      for (var i=0; i<arguments.length; i++) {
        self.data.push(self.escape(JSON.stringify(arguments[i])));
      }
    }
  };
}


//=============================================================================
// MLABModuleSetFieldValuesMessage
//=============================================================================
function MLABModuleSetFieldValuesMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_MODULE_SET_FIELD_VALUES);
  
  this.lastSerialID = 0;

  this.read = function(data) {
    // TODO: why is the set field values message the same as the module info message?
    // both seem to send the module code, but it should not be send here
    self.status = parseInt(data.shift());
    
    var fieldCount = parseInt(data.shift());
    self.fieldData = [];
    for (var i=0; i<fieldCount; i++) {
      self.fieldData.push([data.shift(), // name 
                           self.unescape(data.shift()), // value/type
                           data.shift()]); // options
    }
  };
  
  this.setFieldData = function(fieldData) {
    self.data = [self.lastSerialID, fieldData.length];
    for (var i=0; i<fieldData.length; i++) {
      self.data.push(fieldData[i][0]); // name
      self.data.push(self.escape(fieldData[i][1])); // value
      self.data.push(fieldData[i][2]); // options
    }
    self.lastSerialID += 1;
  };
}


//=============================================================================
// MLABModuleCreateMessage
//=============================================================================
function MLABModuleCreateMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_MODULE_CREATE);
  
  this.setData = function(module) {
    self.data = [module];
  };  
}


//=============================================================================
// MLABModuleVersionMessage
//=============================================================================
function MLABModuleVersionMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_MODULE_VERSION);
  
  this.read = function(data) {
    self.version = parseInt(data.shift());
  };
}


//=============================================================================
// MLABModuleInfoMessage
//=============================================================================
function MLABModuleInfoMessage() {
  var self = this;

  this.inheritFrom = MLABModuleSetFieldValuesMessage;
  this.inheritFrom();
  
  this.setFieldValuesMessageRead = this.read
  
  this.read = function(data) {
    self.setFieldValuesMessageRead(data);
  }
  
  this.type = MLAB_MSG_MODULE_INFO;
}


//=============================================================================
// MLABModuleLogMessage
//=============================================================================
function MLABModuleLogMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_MODULE_LOG_MESSAGE);
  
  this.read = function(data) {
    self.message = self.unescape(data.shift());
  };
}
/*
function MLABModuleSetImageProperties(data) {
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(data);
  // TODO
}

function MLABModuleTileRequest(data) {
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(data);
  // TODO
}

function MLABModuleTileData(data) {
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(data);
  // TODO
}

function MLABModuleSetImageProperties(data) {
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(data);
  // TODO
}*/

function MLABModuleBaseFieldTypeMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_MODULE_BASE_FIELD_TYPE);

  this.read = function(data) {
    self.baseField = data.shift();
    self.baseType = data.shift();
    self.baseGeneration = data.shift();
  };
}

function MLABModuleProcessInformationMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_MODULE_PROCESS_INFORMATION);
}

function MLABRenderingSlaveAddedMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_SLAVE_ADDED);

  this.setData = function(baseField, baseGeneration, slaveID) {
    self.data = [baseField, baseGeneration, slaveID];
  };
}

function MLABRenderingSlaveRemovedMessage() {
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_SLAVE_REMOVED);
  console.log("not implemented");
}

function MLABRenderingQEventMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_QEVENT);
}

function MLABRenderingSetRenderSizeMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_SET_RENDER_SIZE);
  
  this.setData = function(baseField, baseGeneration, slaveID, imageWidth, imageHeight) {
    self.data = [baseField, baseGeneration, slaveID, imageWidth, imageHeight];
  };
}

function MLABRenderingRenderRequestMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_RENDER_REQUEST);
  
  this.setData = function(baseField, baseGeneration, slaveID, highQuality) {
    self.data = [baseField, baseGeneration, slaveID, highQuality];
  };
}

function MLABRenderingRenderSceneChangedMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_RENDER_SCENE_CHANGED);
  
  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = data.shift();
  };
}

function MLABRenderingRenderedImageMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_RENDERED_IMAGE);
  
  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = data.shift();
    self.slaveID = data.shift();
    self.fullQuality = parseInt(data.shift());
    self.imageData = data.shift();
  };
}

function MLABRenderingRenderedImageAcknowledgeMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_RENDERED_IMAGE_ACKNOWLEDGE);
  
  this.setData = function(baseField, baseGeneration, slaveID) {
    self.data = [baseField, baseGeneration, slaveID, ""];
  };
}

function MLABRenderingRenderStartStreamingMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_RENDER_START_STREAMING);
  
  this.setData = function(baseField, baseGeneration, slaveID) {
    self.data = [baseField, baseGeneration, slaveID];
  };
}

function MLABRenderingRenderStopStreamingMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_RENDER_STOP_STREAMING);
  
  this.setData = function(baseField, baseGeneration, slaveID) {
    self.data = [baseField, baseGeneration, slaveID];
  };
}

function MLABRenderingSetStreamingQualityMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_SET_STREAMING_QUALITY);
  
  this.setData = function(baseField, baseGeneration, settingsDict) {
    self.data = [baseField, baseGeneration, JSON.stringify(settingsDict)];
  };
}

function MLABRenderingSetCursorShapeMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_SET_CURSOR_SHAPE);
  
  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = data.shift();
    self.slaveID = data.shift();
    self.shapeID = data.shift();
    self.hasQCursor = mlabIsTrue(data.shift());
    self.shape = parseInt(data.shift());
    self.hotSpot = data.shift();
    //TODO: check what unknown is
    self.unknown = data.shift();
    self.imageData = data.shift();
  };
}

function MLABRenderingSetSizeHintsMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_RENDERING_SET_SIZE_HINTS);
  
  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = data.shift();
    self.sizeHint = [parseInt(data.shift()), parseInt(data.shift())];
    self.minimumSize = [parseInt(data.shift()), parseInt(data.shift())];
    self.maximumSize = [parseInt(data.shift()), parseInt(data.shift())];
  };
}

function MLABItemModelAttributes() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_ITEM_MODEL_ATTRIBUTES);

  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = data.shift();
    self.hasChildren = data.shift();
    var attributeCount = data.shift(); // number of attributes
    self.attributes = [];
    for (var i=0; i<attributeCount; i++) {
      self.attributes.push([data[i*2], JSON.parse(data[i*2+1])]);
    }
  };
}

function MLABItemModelGetChildrenMessage() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_ITEM_MODEL_GET_CHILDREN);
  
  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = parseInt(data.shift());
    self.itemID = parseInt(data.shift());
  };

  this.setData = function(baseField, baseGeneration, itemID) {
    self.data = [baseField, baseGeneration, itemID];
  };
}

function MLABItemModelItemChanged() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_ITEM_MODEL_ITEM_CHANGED);

  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = parseInt(data.shift());
    self.itemID = parseInt(data.shift());
    self.hasChildren = JSON.parse(data.shift());
  };
}

function MLABItemModelItemsInserted() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_ITEM_MODEL_ITEMS_INSERTED);

  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = parseInt(data.shift());
    self.parentItemID = parseInt(data.shift());
    self.position = parseInt(data.shift());
    var itemCount = parseInt(data.shift());
    self.items = [];
    for (var i=0; i<itemCount; i++) {
      self.items.push({"hasChildren": JSON.parse(data[i*2]), 
                       "data": JSON.parse(data[i*2+1])});
    }
  };  
}

function MLABItemModelItemsRemoved() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_ITEM_MODEL_ITEMS_REMOVED);

  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = parseInt(data.shift());
    self.parentItemID = parseInt(data.shift());
    self.position = parseInt(data.shift());
    self.itemCount = parseInt(data.shift());
  };  
}

function MLABItemModelDataChanged() {
  var self = this;
  
  this.inheritFrom = MLABRemoteMessage;
  this.inheritFrom(MLAB_MSG_ITEM_MODEL_DATA_CHANGED);

  this.read = function(data) {
    self.baseField = data.shift();
    self.baseGeneration = parseInt(data.shift());
    var attributeCount = parseInt(data.shift());
    self.attributeNames = [];
    for (var i=0;i<attributeCount;i++) {
      self.attributeNames.push(data.shift());
    }
    var itemCount = parseInt(data.shift());
    self.itemIDs = [];
    for (var i=0;i<itemCount;i++) {
      self.itemIDs.push(parseInt(data.shift()));
    }
    var valueCount = parseInt(data.shift());
    self.values = [];
    for (var i=0;i<valueCount;i++) {
      self.values.push(JSON.parse(data.shift()));
    }
  };  

  this.setData = function(baseField, baseGeneration, attributeNames, itemIDs, values) {
    self.data = [baseField, baseGeneration];
    self.data.push(attributeNames.length);
    self.data = self.data.concat(attributeNames);
    self.data.push(itemIDs.length);
    self.data = self.data.concat(itemIDs);
    self.data.push(values.length);
    for (var i=0;i<values.length;i++) {
      self.data.push(self.escape(JSON.stringify(values[i])));
    }
  };

}


//=============================================================================
// Global message class map
//=============================================================================
gMessageClassMap = new Object();
    // MLAB_MSG_GENERIC_REQUEST is currently not used
gMessageClassMap[MLAB_MSG_GENERIC_REPLY] = MLABGenericReply;
    // MLAB_MSG_OBJECT_DELETED  is currently not used

gMessageClassMap[MLAB_MSG_MODULE_VERSION]          = MLABModuleVersionMessage;
gMessageClassMap[MLAB_MSG_MODULE_CREATE]           = MLABRemoteMessage;
gMessageClassMap[MLAB_MSG_MODULE_INFO]             = MLABModuleInfoMessage;
gMessageClassMap[MLAB_MSG_MODULE_SET_FIELD_VALUES] = MLABModuleSetFieldValuesMessage;
gMessageClassMap[MLAB_MSG_MODULE_LOG_MESSAGE]      = MLABModuleLogMessage;

    /* MLAB_MSG_MODULE_SET_IMAGE_PROPERTIES = '105';
    MLAB_MSG_MODULE_TILE_REQUEST         = '106';
    MLAB_MSG_MODULE_TILE_DATA            = '107';
    */
gMessageClassMap[MLAB_MSG_MODULE_BASE_FIELD_TYPE]  = MLABModuleBaseFieldTypeMessage;
gMessageClassMap[MLAB_MSG_MODULE_PROCESS_INFORMATION] = MLABModuleProcessInformationMessage;

gMessageClassMap[MLAB_MSG_RENDERING_SLAVE_ADDED] = MLABRenderingSlaveAddedMessage;
/*
    MLAB_MSG_RENDERING_SLAVE_REMOVED        = '1021';
    */
gMessageClassMap[MLAB_MSG_RENDERING_QEVENT]               = MLABRenderingQEventMessage;
gMessageClassMap[MLAB_MSG_RENDERING_SET_RENDER_SIZE]      = MLABRenderingSetRenderSizeMessage;
gMessageClassMap[MLAB_MSG_RENDERING_RENDER_REQUEST]       = MLABRenderingRenderRequestMessage;
gMessageClassMap[MLAB_MSG_RENDERING_RENDER_SCENE_CHANGED] = MLABRenderingRenderSceneChangedMessage;
gMessageClassMap[MLAB_MSG_RENDERING_RENDERED_IMAGE]       = MLABRenderingRenderedImageMessage;
gMessageClassMap[MLAB_MSG_RENDERING_SET_CURSOR_SHAPE]     = MLABRenderingSetCursorShapeMessage;
gMessageClassMap[MLAB_MSG_RENDERING_SET_SIZE_HINTS]       = MLABRenderingSetSizeHintsMessage;
gMessageClassMap[MLAB_MSG_RENDERING_RENDERED_IMAGE_ACKNOWLEDGE] = MLABRenderingRenderedImageAcknowledgeMessage;

gMessageClassMap[MLAB_MSG_ITEM_MODEL_ATTRIBUTES]     = MLABItemModelAttributes;
gMessageClassMap[MLAB_MSG_ITEM_MODEL_ITEM_CHANGED]   = MLABItemModelItemChanged;
gMessageClassMap[MLAB_MSG_ITEM_MODEL_ITEMS_INSERTED] = MLABItemModelItemsInserted;
gMessageClassMap[MLAB_MSG_ITEM_MODEL_ITEMS_REMOVED]  = MLABItemModelItemsRemoved;
gMessageClassMap[MLAB_MSG_ITEM_MODEL_DATA_CHANGED]   = MLABItemModelDataChanged;
gMessageClassMap[MLAB_MSG_ITEM_MODEL_GET_CHILDREN]   = MLABItemModelGetChildrenMessage;
