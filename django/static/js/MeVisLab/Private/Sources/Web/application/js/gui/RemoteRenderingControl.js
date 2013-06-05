/** \class MLAB.GUI.RemoteRenderingControl(MLAB.GUI.WidgetControl)
 * 
 */
MLAB.GUI.deriveClass("RemoteRenderingControl", MLAB.GUI.WidgetControl, {

  RemoteRenderingControl: function(mdlTree, module) {
    MLAB.GUI.RemoteRenderingControl.super.constructor.call(this, mdlTree, module)
    this._slave = null
    this.registerSignal("metaInformationChanged")
  },
  
  createWidget: function(id) {
    var w = MLAB.GUI.WidgetFactory.create("RemoteRenderingWidget", id)
    w.setControl(this)
    w.connect("viewportSizeChanged", this, "viewportSizeChanged")
    return w
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.slaveWasActivated
   * 
   * Called from the \ref MLAB.Core.RemoteRenderingSlave "slave" when it is added. If
   * this control is visible, then the slave is enabled. Otherwise the slave will
   * be enabled when the control is shown (setVisible()).
   */
  slaveWasAdded: function() {
    this.getWidget().slaveWasAdded()
  },
  
  setup: function(parentControl) {
    MLAB.GUI.RemoteRenderingControl.super.setup.call(this, "MLAB-GUI-RemoteRenderingControl", parentControl)
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl
   * 
   * Returns the remote rendering slave.
   * 
   * \return The MLAB.Core.RemoteRenderingSlave, or null if it was not yet created or the base field type is not "RemoteRendering".
   */
  getSlave: function() {
    return this._slave
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.getViewportSize
   * 
   * Returns the viewport size.
   * 
   * \returns The viewport size as array with two elements: [width, height].
   */
  getViewportSize: function() {
    return this.getWidget().getViewportSize()
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.resizeViewport
   * 
   * Resizes the viewport.
   * 
   * \param w The new viewport width.
   * \param h The new viewport height.
   */
  resizeViewport: function(w, h) {
    this.getWidget().resizeViewport(w, h)
  },
  
  viewportSizeChanged: function(w, h) {
    this._slave.viewportSizeChanged(w, h)
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.setSizeHint
   * 
   * Sets the size hint for the viewport.
   * 
   * \param sizeHint An array with two elements is expected: [width, height]
   */
  setSizeHint: function(sizeHint) {
    this.getWidget().setSizeHint(sizeHint)
  },

  /** \fn MLAB.GUI.RemoteRenderingControl.resizeViewportToSizeHint
   * 
   * This method resizes the viewport to the size hint, or the viewport size if
   * the size hint is invalid. MLAB.Core.RemoteRenderingSlave.setSizeHints() calls this function.
   */
  resizeViewportToSizeHint: function() {
    this.getWidget().resizeViewportToSizeHint()
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.setMaximumSize
   * 
   * Sets the maximum size of the viewport.
   * 
   * \param size An array with two elements is expected: [width, height]
   */
  setMaximumSize: function(size) {
    this.getWidget().setMaximumSize(size)
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.getMaximumSize
   * 
   * Returns the maximum size of the viewport.
   *  
   * \returns  An array with two elements: [width, height]
   */
  getMaximumSize: function() {
    return this.getWidget().getMaximumSize()
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.setMinimumSize
   * 
   * Sets the maximum size of the viewport.
   * 
   * \param size An array with two elements is expected: [width, height]
   */
  setMinimumSize: function(size) {
    this.getWidget().setMinimumSize(size)
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.getMinimumSize
   * 
   * Returns the minimum size of the viewport.
   * 
   * \returns An array with two elements: [width, height]
   */
  getMinimumSize: function() {
    return this.getWidget().getMinimumSize()
  },

  /** \fn MLAB.GUI.RemoteRenderingControl.useSizeHintWidth
   * 
   * Returns true if the width of the size hint should be used.
   *
   * \returns A boolean value.
   */
  useSizeHintWidth: function() {
    return this.getWidget().useSizeHintWidth()
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.useSizeHintHeight
   * 
   * Returns true if the height of the size hint should be used.
   *
   * \returns A boolean value.
   */
  useSizeHintHeight: function() { 
    return this.getWidget().useSizeHintHeight()
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.setupTypicalTags
   * 
   * Reimplements MLABWidgetControl.setupTypicalTags() to check if a fixed size
   * is given. If it is not, then the default size is 400x400 and the size hint
   * will be used, if it is valid. The remote rendering slave is also created here.
   */
  setupTypicalTags: function() {
    var w = parseInt(this.getMDLAttribute("w", "-1"))
    var h = parseInt(this.getMDLAttribute("h", "-1"))
    this.getWidget().setSizeHint([w, h])
    if (w === -1) { w = 400; this.getWidget().setUseSizeHintWidth(true) }
    if (h === -1) { h = 400; this.getWidget().setUseSizeHintHeight(true) }
    this.getWidget().initViewportSize(w, h)
    this._createSlave()
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.destroy
   * 
   * Destructor. Destroys the slave and calls the inherited destructor of MLAB.GUI.WidgetControl.
   */ 
  destroy: function() { 
    this._destroySlave()
    MLAB.GUI.RemoteRenderingControl.super.destroy.call(this)
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl._destroySlave
   * 
   * Deactivates the slave (MLAB.Core.RemoteRenderingSlave.remove()) and removes it from the
   * remote rendering base field handler (MLABRemoteRenderingBaseHandler.removeSlave()).
   */
  _destroySlave: function() {
    if (this._slave !== null) {
      this.getWidget().setRemoteRenderingSlave(null)
      var handler = this._field.getHandler()
      this._slave.remove()
      handler.removeSlave(this._slave)
      this._slave = null
    }
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl._createSlave
   * 
   * Creates the remote rendering slave. An existing slave is first destroyed and a new
   * one is created if MLAB.Core.BaseField.getBaseType() returns "RemoteRendering". The slave
   * is then added to the MLABRemoteRenderingBaseHandler.
   */
  _createSlave: function() {
    this._destroySlave()
    if (this.getField().getBaseType() === "RemoteRendering") {
      this._slave = new MLAB.Core.RemoteRenderingSlave(this)
      this.getWidget().setRemoteRenderingSlave(this._slave)
      this._field.getHandler().addSlave(this._slave)
      if (this.getModule().getModuleContext().getState().getClassName() === "MLAB.Core.MCStateRenderingSlavesActivated") {
        this._slave.add()
      }
    }
  },
  
  /** \fn MLAB.GUI.RemoteRenderingControl.fieldChanged
   * 
   * Reimplemented from MLABWidgetControl to react on changes of the base field type.
   * Calls _createSlave()
   */
  fieldChanged: function() {
    this._createSlave()
  },
  
  
  setImageData: function(mimeType, imageData, metaInformation) {
    this.getWidget().setImageData(mimeType, imageData, metaInformation)
    if (metaInformation) {
      this.emit("metaInformationChanged", metaInformation)
    }
  },
  
  setCursorStyle: function(cursorStyle) {
    this.getWidget().setCursorStyle(cursorStyle)
  },
})


MLAB.GUI.WidgetControlFactory.registerWidgetControl("RemoteRendering", MLAB.GUI.RemoteRenderingControl)
