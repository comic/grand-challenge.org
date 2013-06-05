/** \class MLAB.Core.RemoteRenderingBaseFieldHandler(MLAB.Core.BaseFieldHandlerBase)
 *
 */
MLAB.Core.deriveClass("RemoteRenderingBaseFieldHandler", MLAB.Core.BaseFieldHandlerBase, {
  RemoteRenderingBaseFieldHandler: function (baseField) {
    MLAB.Core.RemoteRenderingBaseFieldHandler.super.constructor.call(this, baseField)
  
    this._lastSlaveId = -1
    this._slaves = []
    this._lastSizeHintMessage = null
    this._cursorStyles = {}
    this._renderSettings = this._baseField.getFieldOwner().getModuleContext().getRenderSettings().clone() 
  },
  
  /**
   * sends the current rendersettings to the MeVisLab remote rendering
   */
  sendRenderSettings: function() {
    // send desired quality settings for this base field:
    this.sendBaseFieldMessage(MLAB.Core.RenderingSetStreamingQualityMessage, this._renderSettings)
  },

  /**
   * returns the current render settings, which initially are a copy of the global render settings.
   * You can modify the returned render settings and update them to MeVisLab via sendRenderSettings().
   */
  getRenderSettings: function() { 
    return this._renderSettings
  },
  
  removeSlave: function(slave) {
    this._slaves.remove(slave)
  },
  
  addSlave: function(slave) {
    var id = ++this._lastSlaveId
    slave.setId(id)
    if (this._lastSizeHintMessage !== null) {
      slave.setSizeHints(this._lastSizeHintMessage)
    }
    slave.setStreamingEnabled(this.getRenderSettings().isStreamingEnabled())
    this._slaves.push(slave)
  },
  
  /**
   * adds rendering slaves to the rendering process
   */
  addRenderingSlaves: function() {
    for (var i=0; i<this._slaves.length; i++) {
      this._slaves[i].add()
    }
  },
    
  handleMessage: function(message) {
    if (message.type === MLAB.Core.MSG_MODULE_BASE_FIELD_TYPE) {
      this.sendRenderSettings()
    } else if (message.type === MLAB.Core.MSG_RENDERING_SET_SIZE_HINTS) {
      // size hints need to be stored and passed to the slaves when they are added
      this._lastSizeHintMessage = message
    }

    // cursors are cached per base field handler, so this message cannot be handled by the slaves
    var cursorStyle = null
    if (message.type === MLAB.Core.MSG_RENDERING_SET_CURSOR_SHAPE) {
      cursorStyle = this._getCursorStyleFromMessage(message)
    }
    
    for (var i=0; i<this._slaves.length; i++) {
      // either the message is for all slaves (message.slaveID is undefined) or it is
      // for one particular slave (message.slaveID is defined)
      if (typeof(message.slaveID) === "undefined" || this._slaves[i]._id === message.slaveID) {
        if (message.type === MLAB.Core.MSG_RENDERING_SET_CURSOR_SHAPE && cursorStyle) {
          this._slaves[i].setCursorStyle(cursorStyle)
        } else {
          this._slaves[i].handleBaseFieldMessage(message)
        }
      }
    }
  },
  
  _getCursorStyleFromMessage: function(message) {
    var cursorStyle = null
    if (message.hasQCursor) {
      // use cursor shape provided in message
      switch (message.shape) {
      case  0: cursorStyle = "default";     break
      case  1: cursorStyle = "n-resize";    break
      case  2: cursorStyle = "crosshair";   break
      case  3: cursorStyle = "wait";        break
      case  4: cursorStyle = "text";        break
      case  5: cursorStyle = "ns-resize";   break
      case  6: cursorStyle = "ew-resize";   break
      case  7: cursorStyle = "nesw-resize"; break
      case  8: cursorStyle = "nwse-resize"; break
      case  9: cursorStyle = "move";        break
      case 10: cursorStyle = "none";        break
      case 11: cursorStyle = "row-resize";  break
      case 12: cursorStyle = "col-resize";  break
      case 13: cursorStyle = "pointer";     break
      case 14: cursorStyle = "not-allowed"; break
      case 15: cursorStyle = "help";        break
      case 16: cursorStyle = "wait";        break
      case 17: cursorStyle = "cell";        break // no direct match  // better: -moz-grab
      case 18: cursorStyle = "all-scroll";  break // no direct match  // better: -moz-grabbing
      case 24:
        // bitmap cursor, construct cursor style with data url:
        cursorStyle = "url(data:image/png;base64," + message.imageData + ") " + message.hotSpot + " " + message.unknown + ", default"
        break
      default:
        this._baseField.getFieldOwner().logError("Unhandled Qt cursor shape: " + message.shape)
      }
      if (cursorStyle) {
        // remember cursor style
        this._cursorStyles[message.shapeID] = cursorStyle
      }
    } else {
      // use remembered cursor style
      cursorStyle = this._cursorStyles[message.shapeID]
    }
    return cursorStyle
  }
})

MLAB.Core.BaseFieldHandlerFactory.registerHandler("RemoteRendering", MLAB.Core.RemoteRenderingBaseFieldHandler)
