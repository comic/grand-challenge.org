/** \class MLAB.Core.RemoteRenderingEventHandler
 * 
 * This class handles the JavaScript events for a RemoteRendering control.
 */
MLAB.Core.defineClass("RemoteRenderingEventHandler", {
  RemoteRenderingEventHandler: function(control) {
    this._control = control
  
    // flag to ignore next key press
    this._ignoreNextKeyPress = false
    // previous text of last keypress
    this._prevText = ""
    // previous text of last keydown
    this._prevKeyCode = 0  
  },
    
  /** \fn MLAB.Core.RemoteRenderingEventHandler.handleKeyEvent
   * 
   * Handles the given MLAB.Core.KeyEvent.
   */
  handleKeyEvent: function(keyEvent) {
    var data = {remoteRenderingSlaveId: this._id, keyEvent: keyEvent}
    this._control.sendBaseFieldMessage(MLAB.Core.RenderingQKeyEventMessage, data)
  },
  
  /** \fn MLAB.Core.RemoteRenderingEventHandler.handleWheelEvent
   * 
   * Handles the given MLAB.Core.WheelEvent.
   */
  handleWheelEvent: function(wheelEvent) {
    var data = {remoteRenderingSlaveId: this._id, wheelEvent: wheelEvent}
    this._control.sendBaseFieldMessage(MLAB.Core.RenderingQWheelEventMessage, data)
  },
  
  /** \fn MLAB.Core.RemoteRenderingEventHandler.handleMouseEvent
   * 
   * Handles the given MLAB.Core.MouseEvent.
   */
  handleMouseEvent: function(mouseEvent) {
    var data = {remoteRenderingSlaveId: this._id, mouseEvent: mouseEvent}
    this._control.sendBaseFieldMessage(MLAB.Core.RenderingQMouseEventMessage, data)
  },
})


/** \class MLAB.Core.RemoteRenderingSlave(MLAB.Core.RemoteRenderingEventHandler)
 */
MLAB.Core.deriveClass("RemoteRenderingSlave", MLAB.Core.RemoteRenderingEventHandler, {
  RemoteRenderingSlave: function(control) {
    MLAB.Core.RemoteRenderingSlave.super.constructor.call(this, control)
   
    this._highQualityTimerId = null
    this._hasSceneChangedAgain = false
    this._id = null
    this._isUpdatePending = false
    this._useStreaming = false
    this._isEnabled = false
    this._isAdded = false
  },   
  
  setStreamingEnabled: function(flag) { this._useStreaming = flag },
  
  isAdded: function() { return this._isAdded },
  
  /** \fn MLAB.Core.RemoteRenderingSlave.setId
   * 
   * Sets the remote rendering slave id. MLAB.Core.RemoteRenderingBaseFieldHandler.addSlave() calls this
   * method.
   * 
   * \param id The remote rendering slave id.
   */
  setId: function(id) { this._id = id },
  
  /** \fn MLAB.Core.RemoteRenderingSlave.disable
   * 
   * Disables this slave. If streaming is enabled, then a MLAB.Core.RenderingRenderStopStreamingMessage
   * is send to the server. 
   */
  disable: function() {
    if (this._isEnabled) {
      if (this._useStreaming) { 
        this.sendSlaveMessage(MLAB.Core.RenderingRenderStopStreamingMessage)
      }
      this._isEnabled = false
    }
  },
  
  /** \fn MLAB.Core.RemoteRenderingSlave.sendSlaveMessage
   * 
   * \param data Optional dictionary with additional data properties.
   */
  sendSlaveMessage: function(messageClass, data) {
    if (!this._isAdded) {
      this.logError("Cannot send " + messageClass.getClassName() + ", because the slave with ID " + this._id + " has not been added")
    } else {
      var d = {slaveID: this._id}
      if (data) {
        for (var key in data) { d[key] = data[key] }
      }
      this._control.sendBaseFieldMessage(messageClass, d)
    }
  },
  
  /** \fn MLAB.Core.RemoteRenderingSlave.enable
   * 
   * Enables this slave. The viewport size is send with MLAB.Core.RenderingSetRenderSizeMessage to
   * the server. If streaming is disabled, then one image is requested,
   * otherwise a MLAB.Core.RenderingRenderStartStreamingMessage is send.
   */
  enable: function() {
    if (!this._isEnabled) {
      var size = this._control.getViewportSize()
      this.sendSlaveMessage(MLAB.Core.RenderingSetRenderSizeMessage, {imageWidth: size[0], imageHeight: size[1]})
      if (this._useStreaming) {
        this.sendSlaveMessage(MLAB.Core.RenderingRenderStartStreamingMessage)
      } else {
        // request the initial image
        this._requestImageUpdate(false)
      }
      this._isEnabled = true
    }
  },
  
  /** \fn MLAB.Core.RemoteRenderingSlave.remove
   * 
   * Removes this slave by first sending a MLAB.Core.RenderingRenderStopStreamingMessage if streaming
   * is enabled and by sending a MLAB.Core.RenderingSlaveRemovedMessage afterwards.
   */
  remove: function() {
    this.disable()
    this.sendSlaveMessage(MLAB.Core.RenderingSlaveRemovedMessage)
    this._isRemoved = true
  },

  /** \fn MLAB.Core.RemoteRenderingSlave.add
   * 
   * Adds this remote rendering slave by sending first a MLAB.Core.RenderingSlaveAddedMessage. The remote rendering
   * controls is notified via MLABRemoteRenderingControlBase.slaveWasAdded().
   */
  add: function() {
    this._control.sendBaseFieldMessage(MLAB.Core.RenderingSlaveAddedMessage, {slaveID: this._id})
    this._isAdded = true
    this._control.slaveWasAdded()
  },
  
  viewportSizeChanged: function(width, height) {
    if (this._isEnabled) {
      this.sendSlaveMessage(MLAB.Core.RenderingSetRenderSizeMessage, {imageWidth: width, imageHeight: height})
  
      if (!this._useStreaming) {
        // request the image with it's new size
        this._requestImageUpdate(false)
      }
    }
  },

  setSizeHints: function(message) { 
    this._control.setSizeHint(message.sizeHint)
    this._control.setMaximumSize(message.maximumSize)
    this._control.setMinimumSize(message.minimumSize)
    this._control.resizeViewportToSizeHint()
  },

  logError: function(error) {
    this._control.logError(error)
  },
  
  _requestImageUpdate: function(highQuality) {
    this._isUpdatePending = true
    this.sendSlaveMessage(MLAB.Core.RenderingRenderRequestMessage, {highQuality: highQuality?1:0})
  },
  
  _remoteSceneChanged: function(message) {
    if (!this._useStreaming) {
      // request a new image (currently in low quality only)
      if (this._isUpdatePending) {
        // request updated image delayed
        this._hasSceneChangedAgain = true
      } else {
        this._requestImageUpdate(false)
      }
    }
  },
  
  _remoteImageReceived: function(message) {
    // clear old timer if it exists
    if (this._highQualityTimerId !== null) {
      window.clearTimeout(this._highQualityTimerId)
      this._highQualityTimerId = null
    }

    if (!this._useStreaming) {
      if (this._hasSceneChangedAgain) {
        // scene has changed again in the meantime, request updated image
        this._hasSceneChangedAgain = false
        this.sendSlaveMessage(MLAB.Core.RenderingRenderRequestMessage, {highQuality: 0})
      
      } else {
        // we may request an updated image directly now
        this._isUpdatePending = false
                 
        if (!message.fullQuality) {
          // create new timer to request high quality image:
          this._highQualityTimerId = window.setTimeout(
              function () { this._requestImageUpdate(true) }.bind(this), 
              500)
        }
      }
    }    
    // It is faster to set the image after the new request has been sent above.
    var mimeType = (message.fullQuality ? "image/png" : "image/jpeg")

    this._control.setImageData(mimeType, message.imageData, message.metaInformation)
  },

  setCursorStyle: function(cursorStyle) {
    this._control.setCursorStyle(cursorStyle)
  },
  
  handleBaseFieldMessage: function(message) {    
    switch (message.type) {
    case MLAB.Core.MSG_MODULE_BASE_FIELD_TYPE:
      break
    
    case MLAB.Core.MSG_RENDERING_RENDER_SCENE_CHANGED:
      this._remoteSceneChanged(message)
      break
      
    case MLAB.Core.MSG_RENDERING_RENDERED_IMAGE:
      if (this._useStreaming) {
        // send acknowledge for the received image:
        this.sendSlaveMessage(MLAB.Core.RenderingRenderedImageAcknowledgeMessage)
      }
      this._remoteImageReceived(message)
      break
    
    case MLAB.Core.MSG_RENDERING_SET_SIZE_HINTS:
      this.setSizeHints(message)
      break
      
    default:
      this.logError("MLABRemoteRenderinControl.handleBaseFieldMessage: unhandled message " + message.type)
      break
    }
  },
})
