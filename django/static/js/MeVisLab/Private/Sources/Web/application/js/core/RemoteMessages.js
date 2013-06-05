;(function() {
  // The message type for MLAB.Core.GenericRequest.  
  this.MSG_GENERIC_REQUEST = '10'
  // The message type for MLAB.Core.GenericReply.  
  this.MSG_GENERIC_REPLY = '11'
  // This message type is currently not handled. 
  this.MSG_OBJECT_DELETED = '12'
  // The message type for MLAB.Core.ModuleVersionMessage. 
  this.MSG_MODULE_VERSION = '100'
  // The message type for MLAB.Core.ModuleCreateMessage. 
  this.MSG_MODULE_CREATE = '101'
  // The message type for MLAB.Core.ModuleInfoMessage. 
  this.MSG_MODULE_INFO = '102'
  // The message type for MLAB.Core.ModuleSetFieldValuesMessage. 
  this.MSG_MODULE_SET_FIELD_VALUES = '103'
  // The message type for MLAB.Core.ModuleLogMessage. 
  this.MSG_MODULE_LOG_MESSAGE = '104'
  // The message type is currently not used. 
  this.MSG_MODULE_SET_IMAGE_PROPERTIES = '105'
  // The message type is currently not used. 
  this.MSG_MODULE_TILE_REQUEST = '106'
  // The message type is currently not used. 
  this.MSG_MODULE_TILE_DATA = '107'
  // The message type for MLAB.Core.ModuleBaseFieldTypeMessage. 
  this.MSG_MODULE_BASE_FIELD_TYPE = '108'
  // The message type for MLAB.Core.ModuleShowIDEMessage. 
  this.MSG_MODULE_SHOW_IDE = '109'
  // The message type for MLAB.Core.ModuleProcessInformationMessage. 
  this.MSG_MODULE_PROCESS_INFORMATION = '110'
  // The message type for MLAB.Core.ModuleFieldsMinMaxChangedMessage. 
  this.MSG_MODULE_FIELDS_MIN_MAX_CHANGED = '112'
  
  // The message type for MLAB.Core.GenericBaseRequestMessage. 
  this.MSG_GENERIC_BASE_REQUEST = '1000' 
    // The message type for MLAB.Core.GenericBaseReplyMessage. 
  this.MSG_GENERIC_BASE_REPLY = '1001'
  
  // The message type for MLAB.Core.RenderingSlaveAddedMessage. 
  this.MSG_RENDERING_SLAVE_ADDED = '1020'
  // The message type for MLAB.Core.RenderingSlaveRemovedMessage. 
  this.MSG_RENDERING_SLAVE_REMOVED = '1021'
  // The message type for MLAB.Core.RenderingQEventMessage. 
  this.MSG_RENDERING_QEVENT = '1022'
  // The message type for MLAB.Core.RenderingSetRenderSizeMessage. 
  this.MSG_RENDERING_SET_RENDER_SIZE = '1023'
  // The message type for MLAB.Core.RenderingRenderRequestMessage. 
  this.MSG_RENDERING_RENDER_REQUEST = '1024'
  // The message type for MLAB.Core.RenderingRenderSceneChangedMessage. 
  this.MSG_RENDERING_RENDER_SCENE_CHANGED = '1025'
  // The message type for MLAB.Core.RenderingRenderedImageMessage. 
  this.MSG_RENDERING_RENDERED_IMAGE = '1026'
  // The message type for MLAB.Core.RenderingSetCursorShapeMessage. 
  this.MSG_RENDERING_SET_CURSOR_SHAPE = '1027'
  // The message type for MLAB.Core.RenderingSetSizeHintsMessage. 
  this.MSG_RENDERING_SET_SIZE_HINTS = '1028'
  // The message type for MLAB.Core.RenderingRenderedImageAcknowledgeMessage. 
  this.MSG_RENDERING_RENDERED_IMAGE_ACKNOWLEDGE = '1029'
  // The message type for MLAB.Core.RenderingRenderStartStreamingMessage. 
  this.MSG_RENDERING_RENDER_START_STREAMING = '1030'
  // The message type for MLAB.Core.RenderingRenderStopStreamingMessage. 
  this.MSG_RENDERING_RENDER_STOP_STREAMING = '1031'
  // The message type for MLAB.Core.RenderingSetStreamingQualityMessage. 
  this.MSG_RENDERING_SET_STREAMING_QUALITY = '1032'
  
  // The message type for MLAB.Core.ItemModelAttributesMessage. 
  this.MSG_ITEM_MODEL_ATTRIBUTES = '1050'
  // The message type for MLAB.Core.ItemModelItemChanged. 
  this.MSG_ITEM_MODEL_ITEM_CHANGED = '1051'
  // The message type for MLAB.Core.ItemModelItemsInserted. 
  this.MSG_ITEM_MODEL_ITEMS_INSERTED = '1052'
  // The message type for MLAB.Core.ItemModelItemsRemoved. 
  this.MSG_ITEM_MODEL_ITEMS_REMOVED = '1053'
  // The message type for MLAB.Core.ItemModelDataChanged. 
  this.MSG_ITEM_MODEL_DATA_CHANGED = '1054'
  // The message type for MLAB.Core.ItemModelGetChildrenMessage. 
  this.MSG_ITEM_MODEL_GET_CHILDREN = '1055'
  // The message type for MLAB.Core.ItemModelChildrenDoneMessage. 
  this.MSG_ITEM_MODEL_CHILDREN_DONE = '1056'
}).apply(MLAB.Core)

  
/** \fn MLAB.Core.getMessageTypeName
 * 
 * Map message type numbers to readable names.
 * 
 * \param msgType A string representing a number.
 * \return A type name string.
 */
MLAB.Core.getMessageTypeName = function (msgType) {
  switch (msgType) {
  case '10':
    return 'GENERIC_REQUEST'
  case '11':
    return 'GENERIC_REPLY  '
  case '12':
    return 'OBJECT_DELETED '

  case '100':
    return 'MODULE_VERSION               '
  case '101':
    return 'MODULE_CREATE                '
  case '102':
    return 'MODULE_INFO                  '
  case '103':
    return 'MODULE_SET_FIELD_VALUES      '
  case '104':
    return 'MODULE_LOG_MESSAGE           '
  case '105':
    return 'MODULE_SET_IMAGE_PROPERTIES  '
  case '106':
    return 'MODULE_TILE_REQUEST          '
  case '107':
    return 'MODULE_TILE_DATA             '
  case '108':
    return 'MODULE_BASE_FIELD_TYPE       '
  case '109':
    return 'MODULE_SHOW_IDE              '
  case '110':
    return 'MODULE_PROCESS_INFORMATION   '
  case '112':
    return 'MODULE_FIELDS_MIN_MAX_CHANGED'

  case '1000':
    return 'GENERIC_BASE_REQUEST '
  case '1001':
    return 'GENERIC_BASE_REPLY '

  case '1020':
    return 'RENDERING_SLAVE_ADDED             '
  case '1021':
    return 'RENDERING_SLAVE_REMOVED           '
  case '1022':
    return 'RENDERING_QEVENT                  '
  case '1023':
    return 'RENDERING_SET_RENDER_SIZE         '
  case '1024':
    return 'RENDERING_RENDER_REQUEST          '
  case '1025':
    return 'RENDERING_RENDER_SCENE_CHANGED    '
  case '1026':
    return 'RENDERING_RENDERED_IMAGE          '
  case '1027':
    return 'RENDERING_SET_CURSOR_SHAPE        '
  case '1028':
    return 'RENDERING_SET_SIZE_HINTS          '
  case '1029':
    return 'RENDERING_RENDERED_IMAGE_ACKNOWLEDGE'
  case '1030':
    return 'RENDERING_RENDER_START_STREAMING'
  case '1031':
    return 'RENDERING_RENDER_STOP_STREAMING'
  case '1032':
    return 'RENDERING_SET_STREAMING_QUALITY'

  case '1050':
    return 'MLAB_MSG_ITEM_MODEL_ATTRIBUTES    '
  case '1051':
    return 'MLAB_MSG_ITEM_MODEL_ITEM_CHANGED  '
  case '1052':
    return 'MLAB_MSG_ITEM_MODEL_ITEMS_INSERTED'
  case '1053':
    return 'MLAB_MSG_ITEM_MODEL_ITEMS_REMOVED '
  case '1054':
    return 'MLAB_MSG_ITEM_MODEL_DATA_CHANGED  '
  case '1055':
    return 'MLAB_MSG_ITEM_MODEL_GET_CHILDREN  '
  case '1056':
    return 'MLAB_MSG_ITEM_MODEL_CHILDREN_DONE '
  }
  return "UNKNOWN_MESSAGE_TYPE(" + msgType + ")"
}

/** \defgroup RemoteMessages Remote Messages
 * 
 * These are the messages that are used to communicate with a MeVisLab process through a web socket connection.
 */

/** \class MLAB.Core.RemoteMessage
 * 
 * This is the base class for messages that are sent and received via a web socket to and from
 * a MeVisLab process.
 * 
 * \ingroup RemoteMessages
 */
MLAB.Core.defineClass("RemoteMessage", {
  RemoteMessage: function(type) {
    this.type = type
    this.data = []
  },

  /** \fn MLAB.Core.RemoteMessage.isBaseFieldMessage
   * 
   * Returns true if this is a base field message, i.e. if MLAB.Core.BaseFieldMessage is inherited.
   */
  isBaseFieldMessage: function() { return false },

  /** \fn MLAB.Core.RemoteMessage.unescape
   * 
   * Unescapes the given string. See escape().
   * 
   * \param s An escaped string.
   */
  unescape: function(s) { return s.replace(/\\\\/g, '\\').replace(/\\n/g, '\n') },

  /** \fn MLAB.Core.RemoteMessage.escape
   * 
   * Escapes the given string, so that it can be safely passed as base64 encoded string
   * through a web socket.
   * 
   * \param s An unescaped string.
   */
  escape: function(s) { return s.replace(/\\/g, '\\\\').replace(/\n/g, '\\n') },

  /** \fn MLAB.Core.RemoteMessage.read
   * 
   * Reads the message from the given web socket message data.
   * 
   * \param data The data from the web socket message.
   */
  read: function(data) { this.data = data },

  /** \fn MLAB.Core.RemoteMessage.setData
   * 
   * Sets the data that will be send through a web socket message. 
   * 
   * \param data The data for a web socket message. It must be an array and all values need to be
   *             escaped strings. See also escape().
   */
  setData: function(data) { this.data = data },

  /** \fn MLAB.Core.RemoteMessage.toString
   * 
   * Creates and returns a string representation of this message.
   */
  toString: function() {
    var message = MLAB.Core.getMessageTypeName(this.type) + "\n"
    for ( var i = 0; i < this.data.length; i++) {
      message += this.data[i] + "\n"
    }
    return message
  },

  /** \fn MLAB.Core.RemoteMessage.serialize
   * 
   * Serializes this message into a string and returns it.
   */
  serialize: function() {
    var message = this.type + "\n"
    for ( var i = 0; i < this.data.length; i++) {
      if (typeof(this.data[i]) === "undefined") {
        MLAB.Core.throwException("Message data contains an undefined value: " + this.toString())
      }
      message += this.data[i] + "\n"
    }
    return message
  },
})

/** \class MLAB.Core.GenericReply(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("GenericReply", MLAB.Core.RemoteMessage, {
  GenericReply: function() {
    MLAB.Core.GenericReply.super.constructor.call(this, MLAB.Core.MSG_GENERIC_REPLY)
  },

  read: function(data) {
    this.requestID = parseInt(data.shift())
    this.arguments = []
    // skip last argument, which is always an empty string
    for ( var i = 0; i < data.length; i++) {
      this.arguments.push(JSON.parse(data[i]))
    }
  },
})
 
/** \class MLAB.Core.GenericRequest(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("GenericRequest", MLAB.Core.RemoteMessage, {
  GenericRequest: function() {
    MLAB.Core.GenericRequest.super.constructor.call(this, MLAB.Core.MSG_GENERIC_REQUEST)
  },

  setData: function(data) {
    this.data = [ data.requestID, data.objectID, data.functionName ]

    if (data.arguments) {
      this.data.push(data.arguments.length)
      for ( var i = 0; i < data.arguments.length; i++) {
        this.data.push(JSON.stringify(data.arguments[i]))
      }
    } else {
      // empty argument list
      this.data.push(0)
    }
  },
})

/** \class MLAB.Core.ModuleFieldValuesBaseMessage(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleFieldValuesBaseMessage", MLAB.Core.RemoteMessage, {
  ModuleFieldValuesBaseMessage: function(messageType) {
    MLAB.Core.ModuleFieldValuesBaseMessage.super.constructor.call(this, messageType)
  },
  
  readFieldData: function(data) {
    var fieldCount = parseInt(data.shift())
    this.fieldData = []
    for ( var i = 0; i < fieldCount; i++) {
      this.fieldData.push([ data.shift(),                // name
                            this.unescape(data.shift()), // value/type
                            parseInt(data.shift()) ])    // flags
    }
  },

  writeFieldData: function(fieldData) {
    this.data.push(fieldData.length)
    for (var i=0; i<fieldData.length; i++) {
      this.data.push(fieldData[i].name)
      this.data.push(this.escape(fieldData[i].value))
      this.data.push(fieldData[i].flags)
    }
  },
})

/** \class MLAB.Core.ModuleSetFieldValuesMessage(MLAB.Core.ModuleFieldValuesBaseMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleSetFieldValuesMessage", MLAB.Core.ModuleFieldValuesBaseMessage, {
  ModuleSetFieldValuesMessage: function() {
    MLAB.Core.ModuleSetFieldValuesMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_SET_FIELD_VALUES)
  },
  
  read: function(data) {
    this.serialID = parseInt(data.shift())
    this.readFieldData(data)
  },

  setData: function(data) {
    this.serialID = ++MLAB.Core.ModuleSetFieldValuesMessage.LastSerialID 
    this.data = [this.serialID]
    this.writeFieldData(data)
  },
  
}, {
  // static members
  LastSerialID: 1,
})

/** \class MLAB.Core.ModuleFieldsMinMaxChangedMessage(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleFieldsMinMaxChangedMessage", MLAB.Core.RemoteMessage, {
  ModuleFieldsMinMaxChangedMessage: function() {
    MLAB.Core.ModuleFieldsMinMaxChangedMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_FIELDS_MIN_MAX_CHANGED)
  },

  read: function(data) {
    this.serialID = parseInt(data.shift())
    
    var fieldCount = parseInt(data.shift())
    this.fieldData = []
    for (var i = 0; i < fieldCount; i++) {
      var fieldName = data.shift()
      var minMaxValues = this.unescape(data.shift()).split(';')
      if (minMaxValues.length !== 2) {
        MLAB.Core.throwException("MLAB.Core.ModuleFieldsMinMaxChangedMessage: invalid min/max value format [" + fieldName + "]: " + minMaxValues.join(';'))
      }
      this.fieldData.push({name: fieldName,
                           minValue: minMaxValues[0],
                           maxValue: minMaxValues[1],
                           flags: parseInt(data.shift())})
    }
  },
})

/** \class MLAB.Core.ModuleCreateMessage(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleCreateMessage", MLAB.Core.RemoteMessage, {
  ModuleCreateMessage: function() {
    MLAB.Core.ModuleCreateMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_CREATE)
  },

  setData: function(data) {
    // the 0 stands for an empty list of starting values for the module
    this.data = [ data.module, 0 ]
  },
})

/** \class MLAB.Core.ModuleVersionMessage(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleVersionMessage", MLAB.Core.RemoteMessage, {
  ModuleVersionMessage: function() {
    MLAB.Core.ModuleVersionMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_VERSION)
  },

  read: function(data) {
    this.version = parseInt(data.shift())
  },
})

/** \class MLAB.Core.ModuleInfoMessage(MLAB.Core.ModuleFieldValuesBaseMessage)
 * 
 * This message includes the module creation status. It has one of the following
 * values:
 * <table>
 *   <tr><td>0</td><td>Module was successfully created</td></tr>
 *   <tr><td>1</td><td>Module exists already</td></tr>
 *   <tr><td>2</td><td>Module is unknown</td></tr>
 *   <tr><td>3</td><td>Module creation failed</td></tr>
 *   <tr><td>4</td><td>Module authentication failed</td></tr>
 * </ul>
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleInfoMessage", MLAB.Core.ModuleFieldValuesBaseMessage, {
  ModuleInfoMessage: function() {
    MLAB.Core.ModuleInfoMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_INFO)
  },

  read: function(data) {
    this.status = parseInt(data.shift())
    this.readFieldData(data)
    this.serialID = 0
  },
})

/** \class MLAB.Core.ModuleLogMessage(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleLogMessage", MLAB.Core.RemoteMessage, {
  ModuleLogMessage: function() {
    MLAB.Core.ModuleLogMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_LOG_MESSAGE)
  },

  read: function(data) {
    this.message = this.unescape(data.shift())
    if (data.length > 0) {
      this.severity = data.shift()
    } else {
      this.severity = "UNKNOWN"
    }
  },
})

/** \class MLAB.Core.ModuleShowIDEMessage(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleShowIDEMessage", MLAB.Core.RemoteMessage, {
  ModuleShowIDEMessage: function() {
    MLAB.Core.ModuleShowIDEMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_SHOW_IDE)
  },
})

/** \class MLAB.Core.BaseFieldMessage(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("BaseFieldMessage", MLAB.Core.RemoteMessage, {
  BaseFieldMessage: function(type, baseField) {
    MLAB.Core.BaseFieldMessage.super.constructor.call(this, type)
    // the baseField is undefined when a message is read from the web socket
    if (baseField) {
      this.data = [baseField.getName(), baseField.getGenerationId()]
    }
  },
  
  isBaseFieldMessage: function() { return true },
  
  read: function(data) {
    this.baseField = data.shift()
    this.baseGeneration = parseInt(data.shift())
  },

  readBinary: function(stream) {
    this.baseField = stream.readString()
    this.baseGeneration = stream.readInt32()
  },
})

/** \class MLAB.Core.ModuleBaseFieldTypeMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleBaseFieldTypeMessage", MLAB.Core.BaseFieldMessage, {
  ModuleBaseFieldTypeMessage: function(baseField) {
    MLAB.Core.ModuleBaseFieldTypeMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_BASE_FIELD_TYPE, baseField)
  },

  read: function(data) {
    this.baseField = data.shift()
    this.baseType = data.shift()
    this.baseGeneration = parseInt(data.shift())
  },
})

/** \class MLAB.Core.ModuleProcessInformationMessage(MLAB.Core.RemoteMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ModuleProcessInformationMessage", MLAB.Core.RemoteMessage, {
  ModuleProcessInformationMessage: function() {
    MLAB.Core.ModuleProcessInformationMessage.super.constructor.call(this, MLAB.Core.MSG_MODULE_PROCESS_INFORMATION)
  },
})

/** \class MLAB.Core.GenericBaseRequestMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("GenericBaseRequestMessage", MLAB.Core.BaseFieldMessage, {
  GenericBaseRequestMessage: function(baseField) {
    MLAB.Core.GenericBaseRequestMessage.super.constructor.call(this, MLAB.Core.MSG_GENERIC_BASE_REQUEST, baseField)
  },

  read: function(data) {
    MLAB.Core.GenericBaseRequestMessage.super.read.call(this, data)
    this.method = atob(data.shift())
    this.arguments = []
    var argCount = parseInt(data.shift())
    for (var i=0; i<argCount; i++) {
      this.arguments.push(JSON.parse(data.shift()))
    }
    this.requestId = parseInt(data.shift())
  },
})

/** \class MLAB.Core.GenericBaseReplyMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("GenericBaseReplyMessage", MLAB.Core.BaseFieldMessage, {
  GenericBaseReplyMessage: function(baseField) {
    MLAB.Core.GenericBaseReplyMessage.super.constructor.call(this, MLAB.Core.MSG_GENERIC_BASE_REPLY, baseField)
  },
  
  setData: function(data) {
    this.data.push(JSON.stringify(data.result))
    this.data.push(data.requestId)
  },
})

/** \class MLAB.Core.RenderingSlaveAddedMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingSlaveAddedMessage", MLAB.Core.BaseFieldMessage, {
  RenderingSlaveAddedMessage: function(baseField) {
    MLAB.Core.RenderingSlaveAddedMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_SLAVE_ADDED, baseField)
  },

  setData: function(data) {
    this.data.push(data.slaveID)
  },
})

/** \class MLAB.Core.RenderingSlaveRemovedMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingSlaveRemovedMessage", MLAB.Core.BaseFieldMessage, {
  RenderingSlaveRemovedMessage: function(baseField) {
    MLAB.Core.RenderingSlaveRemovedMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_SLAVE_REMOVED, baseField)
  },
  
  setData: function(data) {
    this.data.push(data.slaveID)
  },
})

/** \class MLAB.Core.RenderingQEventMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingQEventMessage", MLAB.Core.BaseFieldMessage, {
  RenderingQEventMessage: function(baseField) {
    MLAB.Core.RenderingQEventMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_QEVENT, baseField)
  },
})

/** \class MLAB.Core.RenderingQKeyEventMessage(MLAB.Core.RenderingQEventMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingQKeyEventMessage", MLAB.Core.RenderingQEventMessage, {
  RenderingQKeyEventMessage: function(baseField) {
    MLAB.Core.RenderingQKeyEventMessage.super.constructor.call(this, baseField)
  },

  setData: function(data) {
    this.data.push(data.remoteRenderingSlaveId)
    this.data.push(data.keyEvent.type === "keyup" ? 7 : 6) // QEvent::Type
    this.data.push(data.keyEvent.qtKeyCode)
    this.data.push(data.keyEvent.qtModifiersCode)
    this.data.push(data.keyEvent.text)  // text generated by pressed key
    this.data.push("false")  // auto-repeat?
    this.data.push(1)  // number of keys involved in this event
  },
})

/** \class MLAB.Core.RenderingQWheelEventMessage(MLAB.Core.RenderingQEventMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingQWheelEventMessage", MLAB.Core.RenderingQEventMessage, {
  RenderingQWheelEventMessage: function(baseField) {
    MLAB.Core.RenderingQWheelEventMessage.super.constructor.call(this, baseField)
  },
  
  setData: function(data) {
    this.data.push(data.remoteRenderingSlaveId)
    this.data.push(31) // QEvent::Type
    this.data.push(data.wheelEvent.relativePosition.x)
    this.data.push(data.wheelEvent.relativePosition.y)
    this.data.push(data.wheelEvent.wheelEventDelta)
    this.data.push(data.wheelEvent.qtButtons)
    this.data.push(data.wheelEvent.qtModifiersCode)
    this.data.push(data.wheelEvent.qtOrientation)
  },
})

/** \class MLAB.Core.RenderingQMouseEventMessage(MLAB.Core.RenderingQEventMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingQMouseEventMessage", MLAB.Core.RenderingQEventMessage, {
  RenderingQMouseEventMessage: function(baseField) {
    MLAB.Core.RenderingQMouseEventMessage.super.constructor.call(this, baseField)
  },
  
  setData: function(data) {
    this.data.push(data.remoteRenderingSlaveId)
    switch (data.mouseEvent.type) {
    case "mouseover":
      this.data.push(10) // QEvent::Enter
      break
    case "mouseout":
      this.data.push(11) // QEvent::Leave
      break
    default:
      switch (data.mouseEvent.type) {
      case "mousedown":
        this.data.push(2) // QEvent::MouseButtonPress
        break
      case "mouseup":
        this.data.push(3) // QEvent::MouseButtonRelease
        break
      case "mousemove":
        this.data.push(5) // QEvent::MouseMove
        break
      }
      this.data.push(data.mouseEvent.relativePosition.x)
      this.data.push(data.mouseEvent.relativePosition.y)
      this.data.push(data.mouseEvent.qtButtonCode)
      this.data.push(data.mouseEvent.qtButtons)
      this.data.push(data.mouseEvent.qtModifiersCode)
    }
  },
})

/** \class MLAB.Core.RenderingSetRenderSizeMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingSetRenderSizeMessage", MLAB.Core.BaseFieldMessage, {
  RenderingSetRenderSizeMessage: function(baseField) {
    MLAB.Core.RenderingSetRenderSizeMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_SET_RENDER_SIZE, baseField)
  },

  setData: function(data) {
    this.data.push(data.slaveID)
    this.data.push(Math.ceil(data.imageWidth))
    this.data.push(Math.ceil(data.imageHeight))
  },
})

/** \class MLAB.Core.RenderingRenderRequestMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingRenderRequestMessage", MLAB.Core.BaseFieldMessage, {
  RenderingRenderRequestMessage: function(baseField) {
    MLAB.Core.RenderingRenderRequestMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_RENDER_REQUEST, baseField)
  },

  setData: function(data) {
    this.data.push(data.slaveID)
    this.data.push(data.highQuality)
  },
})

/** \class MLAB.Core.RenderingRenderSceneChangedMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingRenderSceneChangedMessage", MLAB.Core.BaseFieldMessage, {
  RenderingRenderSceneChangedMessage: function(baseField) {
    MLAB.Core.RenderingRenderSceneChangedMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_RENDER_SCENE_CHANGED, baseField)
  },
})

/** \class MLAB.Core.RenderingRenderedImageMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingRenderedImageMessage", MLAB.Core.BaseFieldMessage, {
  RenderingRenderedImageMessage: function(baseField) {
    MLAB.Core.RenderingRenderedImageMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_RENDERED_IMAGE, baseField)
  },

  read: function(data) {
    MLAB.Core.RenderingRenderedImageMessage.super.read.call(this, data)
    this.slaveID = parseInt(data.shift())
    this.fullQuality = parseInt(data.shift())
    this.imageData = data.shift()
    if (data.length != 0) {
      // parse optional parameters
      this.metaInformation = JSON.parse(data.shift())
    } else {
      this.metaInformation = null
    }
  },

  readBinary: function(stream) {
    MLAB.Core.RenderingRenderedImageMessage.super.readBinary.call(this, stream)
    this.slaveID = stream.readUInt64()
    this.fullQuality = stream.readByte()
    this.imageData = stream.readByteArray()
    if (!stream.atEnd()) {
      // parse optional parameters
      this.metaInformation = stream.readVariant()
    } else {
      this.metaInformation = null
    }
  },
})

/** \class MLAB.Core.RenderingRenderedImageAcknowledgeMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingRenderedImageAcknowledgeMessage", MLAB.Core.BaseFieldMessage, {
  RenderingRenderedImageAcknowledgeMessage: function(baseField) {
    MLAB.Core.RenderingRenderedImageAcknowledgeMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_RENDERED_IMAGE_ACKNOWLEDGE, baseField)
  },

  setData: function(data) {
    this.data.push(data.slaveID)
    this.data.push("")
  },
})

/** \class MLAB.Core.RenderingRenderStartStreamingMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingRenderStartStreamingMessage", MLAB.Core.BaseFieldMessage, {
  RenderingRenderStartStreamingMessage: function(baseField) {
    MLAB.Core.RenderingRenderStartStreamingMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_RENDER_START_STREAMING, baseField)
  },

  setData: function(data) {
    this.data.push(data.slaveID)
  },
})

/** \class MLAB.Core.RenderingRenderStopStreamingMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingRenderStopStreamingMessage", MLAB.Core.BaseFieldMessage, {
  RenderingRenderStopStreamingMessage: function(baseField) {
    MLAB.Core.RenderingRenderStopStreamingMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_RENDER_STOP_STREAMING, baseField)
  },

  setData: function(data) {
    this.data.push(data.slaveID)
  },
})

/** \class MLAB.Core.RenderingSetStreamingQualityMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingSetStreamingQualityMessage", MLAB.Core.BaseFieldMessage, {
  RenderingSetStreamingQualityMessage: function(baseField) {
    MLAB.Core.RenderingSetStreamingQualityMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_SET_STREAMING_QUALITY, baseField)
  },
  
  setData: function(renderSettings) {
    this.data.push(JSON.stringify(renderSettings.getSettingsDictionary()))
  },
})

/** \class MLAB.Core.RenderingSetCursorShapeMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingSetCursorShapeMessage", MLAB.Core.BaseFieldMessage, {
  RenderingSetCursorShapeMessage: function(baseField) {
    MLAB.Core.RenderingSetCursorShapeMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_SET_CURSOR_SHAPE, baseField)
  },

  read: function(data) {
    MLAB.Core.RenderingSetCursorShapeMessage.super.read.call(this, data)
    this.slaveID = parseInt(data.shift())
    this.shapeID = data.shift()
    this.hasQCursor = MLAB.Core.convertMDLValueToBool(data.shift())
    this.shape = parseInt(data.shift())
    this.hotSpot = data.shift()
    // TODO: check what unknown is
    this.unknown = data.shift()
    this.imageData = data.shift()
  },
})

/** \class MLAB.Core.RenderingSetSizeHintsMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("RenderingSetSizeHintsMessage", MLAB.Core.BaseFieldMessage, {
  RenderingSetSizeHintsMessage: function(baseField) {
    MLAB.Core.RenderingSetSizeHintsMessage.super.constructor.call(this, MLAB.Core.MSG_RENDERING_SET_SIZE_HINTS, baseField)
  },

  read: function(data) {
    MLAB.Core.RenderingSetSizeHintsMessage.super.read.call(this, data)
    this.sizeHint = [ parseInt(data.shift()), parseInt(data.shift()) ]
    this.minimumSize = [ parseInt(data.shift()), parseInt(data.shift()) ]
    this.maximumSize = [ parseInt(data.shift()), parseInt(data.shift()) ]
  },
})

/** \class MLAB.Core.ItemModelAttributesMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ItemModelAttributesMessage", MLAB.Core.BaseFieldMessage, {
  ItemModelAttributesMessage: function(baseField) {
    MLAB.Core.ItemModelAttributesMessage.super.constructor.call(this, MLAB.Core.MSG_ITEM_MODEL_ATTRIBUTES, baseField)
  },
  
  read: function(data) {
    MLAB.Core.ItemModelAttributesMessage.super.read.call(this, data)
    this.hasChildren = data.shift()
    var attributeCount = data.shift() // number of attributes
    this.attributes = []
    for ( var i = 0; i < attributeCount; i++) {
      this.attributes.push([ data[i * 2], JSON.parse(data[i * 2 + 1]) ])
    }
  },
})

/** \class MLAB.Core.ItemModelGetChildrenMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ItemModelGetChildrenMessage", MLAB.Core.BaseFieldMessage, {
  ItemModelGetChildrenMessage: function(baseField) {
    MLAB.Core.ItemModelGetChildrenMessage.super.constructor.call(this, MLAB.Core.MSG_ITEM_MODEL_GET_CHILDREN, baseField)
  },

  read: function(data) {
    MLAB.Core.ItemModelGetChildrenMessage.super.read.call(this, data)
    this.itemID = parseInt(data.shift())
  },

  setData: function(data) {
    this.data.push(data.itemID)
  },
})

/** \class MLAB.Core.ItemModelChildrenDoneMessage(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ItemModelChildrenDoneMessage", MLAB.Core.BaseFieldMessage, {
  ItemModelChildrenDoneMessage: function(baseField) {
    MLAB.Core.ItemModelChildrenDoneMessage.super.constructor.call(this, MLAB.Core.MSG_ITEM_MODEL_CHILDREN_DONE, baseField)
  },

  read: function(data) {
    MLAB.Core.ItemModelChildrenDoneMessage.super.read.call(this, data)
    this.itemID = parseInt(data.shift())
  },

  setData: function(data) {
    this.data.push(data.itemID)
  },
})

/** \class MLAB.Core.ItemModelItemChanged(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ItemModelItemChanged", MLAB.Core.BaseFieldMessage, {
  ItemModelItemChanged: function(baseField) {
    MLAB.Core.ItemModelItemChanged.super.constructor.call(this, MLAB.Core.MSG_ITEM_MODEL_ITEM_CHANGED, baseField)
  },

  read: function(data) {
    MLAB.Core.ItemModelItemChanged.super.read.call(this, data)
    this.itemID = parseInt(data.shift())
    this.hasChildren = JSON.parse(data.shift())
  },
})

/** \class MLAB.Core.ItemModelItemsInserted(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ItemModelItemsInserted", MLAB.Core.BaseFieldMessage, {
  ItemModelItemsInserted: function(baseField) {
    MLAB.Core.ItemModelItemsInserted.super.constructor.call(this, MLAB.Core.MSG_ITEM_MODEL_ITEMS_INSERTED, baseField)
  },

  read: function(data) {
    MLAB.Core.ItemModelItemsInserted.super.read.call(this, data)
    this.parentItemID = parseInt(data.shift())
    this.position = parseInt(data.shift())
    var itemCount = parseInt(data.shift())
    this.items = []
    for (var i = 0; i < itemCount; i++) {
      this.items.push({
        "hasChildren" : JSON.parse(data[i * 2]),
        "data" : JSON.parse(data[i * 2 + 1])
      })
    }
  },
})

/** \class MLAB.Core.ItemModelItemsRemoved(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ItemModelItemsRemoved", MLAB.Core.BaseFieldMessage, {
  ItemModelItemsRemoved: function(baseField) {
    MLAB.Core.ItemModelItemsRemoved.super.constructor.call(this, MLAB.Core.MSG_ITEM_MODEL_ITEMS_REMOVED, baseField)
  },

  read: function(data) {
    MLAB.Core.ItemModelItemsRemoved.super.read.call(this, data)
    this.parentItemID = parseInt(data.shift())
    this.position = parseInt(data.shift())
    this.itemCount = parseInt(data.shift())
  },
})

/** \class MLAB.Core.ItemModelDataChanged(MLAB.Core.BaseFieldMessage)
 * \ingroup RemoteMessages
 */
MLAB.Core.deriveClass("ItemModelDataChanged", MLAB.Core.BaseFieldMessage, {
  ItemModelDataChanged: function(baseField) {
    MLAB.Core.ItemModelDataChanged.super.constructor.call(this, MLAB.Core.MSG_ITEM_MODEL_DATA_CHANGED, baseField)
  },

  read: function(data) {
    MLAB.Core.ItemModelDataChanged.super.read.call(this, data)
    var attributeCount = parseInt(data.shift())
    this.attributeNames = []
    for ( var i = 0; i < attributeCount; i++) {
      this.attributeNames.push(data.shift())
    }
    var itemCount = parseInt(data.shift())
    this.itemIDs = []
    for ( var i = 0; i < itemCount; i++) {
      this.itemIDs.push(parseInt(data.shift()))
    }
    var valueCount = parseInt(data.shift())
    this.values = []
    for ( var i = 0; i < valueCount; i++) {
      this.values.push(JSON.parse(data.shift()))
    }
  },

  setData: function(data) {
    this.data.push(data.attributeNames.length)
    this.data = this.data.concat(data.attributeNames)
    this.data.push(data.itemIDs.length)
    this.data = this.data.concat(data.itemIDs)
    this.data.push(data.values.length)
    for ( var i = 0; i < data.values.length; i++) {
      this.data.push(this.escape(JSON.stringify(data.values[i])))
    }
  },
})

// =============================================================================
// Global message class map
// =============================================================================
;(function() {
  
  var o = new Object()
  
  o[MLAB.Core.MSG_GENERIC_REPLY]      = MLAB.Core.GenericReply
  // o[MLAB.Core.MSG_GENERIC_REQUEST] = unused
  // o[MLAB.Core.MSG_OBJECT_DELETED]  = unused

  o[MLAB.Core.MSG_MODULE_VERSION]                 = MLAB.Core.ModuleVersionMessage
  o[MLAB.Core.MSG_MODULE_CREATE]                  = MLAB.Core.RemoteMessage
  o[MLAB.Core.MSG_MODULE_INFO]                    = MLAB.Core.ModuleInfoMessage
  o[MLAB.Core.MSG_MODULE_SET_FIELD_VALUES]        = MLAB.Core.ModuleSetFieldValuesMessage
  o[MLAB.Core.MSG_MODULE_LOG_MESSAGE]             = MLAB.Core.ModuleLogMessage
  o[MLAB.Core.MSG_MODULE_BASE_FIELD_TYPE]         = MLAB.Core.ModuleBaseFieldTypeMessage
  o[MLAB.Core.MSG_MODULE_PROCESS_INFORMATION]     = MLAB.Core.ModuleProcessInformationMessage
  o[MLAB.Core.MSG_MODULE_FIELDS_MIN_MAX_CHANGED]  = MLAB.Core.ModuleFieldsMinMaxChangedMessage
  // o[MLAB.Core.MSG_MODULE_SET_IMAGE_PROPERTIES] = unused
  // o[MLAB.Core.MSG_MODULE_TILE_REQUEST          = unused
  // o[MLAB.Core.MSG_MODULE_TILE_DATA             = unused
  
  o[MLAB.Core.MSG_GENERIC_BASE_REQUEST] = MLAB.Core.GenericBaseRequestMessage
  o[MLAB.Core.MSG_GENERIC_BASE_REPLY]   = MLAB.Core.GenericBaseReplyMessage

  o[MLAB.Core.MSG_RENDERING_SLAVE_ADDED]                = MLAB.Core.RenderingSlaveAddedMessage
  o[MLAB.Core.MSG_RENDERING_QEVENT]                     = MLAB.Core.RenderingQEventMessage
  o[MLAB.Core.MSG_RENDERING_SET_RENDER_SIZE]            = MLAB.Core.RenderingSetRenderSizeMessage
  o[MLAB.Core.MSG_RENDERING_RENDER_REQUEST]             = MLAB.Core.RenderingRenderRequestMessage
  o[MLAB.Core.MSG_RENDERING_RENDER_SCENE_CHANGED]       = MLAB.Core.RenderingRenderSceneChangedMessage
  o[MLAB.Core.MSG_RENDERING_RENDERED_IMAGE]             = MLAB.Core.RenderingRenderedImageMessage
  o[MLAB.Core.MSG_RENDERING_SET_CURSOR_SHAPE]           = MLAB.Core.RenderingSetCursorShapeMessage
  o[MLAB.Core.MSG_RENDERING_SET_SIZE_HINTS]             = MLAB.Core.RenderingSetSizeHintsMessage
  o[MLAB.Core.MSG_RENDERING_RENDERED_IMAGE_ACKNOWLEDGE] = MLAB.Core.RenderingRenderedImageAcknowledgeMessage
  // o[MLAB.Core.MSG_RENDERING_SLAVE_REMOVED]           = unused 

  o[MLAB.Core.MSG_ITEM_MODEL_ATTRIBUTES]     = MLAB.Core.ItemModelAttributesMessage
  o[MLAB.Core.MSG_ITEM_MODEL_ITEM_CHANGED]   = MLAB.Core.ItemModelItemChanged
  o[MLAB.Core.MSG_ITEM_MODEL_ITEMS_INSERTED] = MLAB.Core.ItemModelItemsInserted
  o[MLAB.Core.MSG_ITEM_MODEL_ITEMS_REMOVED]  = MLAB.Core.ItemModelItemsRemoved
  o[MLAB.Core.MSG_ITEM_MODEL_DATA_CHANGED]   = MLAB.Core.ItemModelDataChanged
  o[MLAB.Core.MSG_ITEM_MODEL_GET_CHILDREN]   = MLAB.Core.ItemModelGetChildrenMessage
  o[MLAB.Core.MSG_ITEM_MODEL_CHILDREN_DONE]  = MLAB.Core.ItemModelChildrenDoneMessage
  
  this.remoteMessageClassMap = o

}).apply(MLAB.Core)
