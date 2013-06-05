/** \class MLAB.Core.Object
 * 
 * Base class for objects with signals and slots.
 * 
 * The signals and slots mechanism is a replacement for 
 * callback functions. So instead of having setter functions and member variables for callbacks,
 * you can use signals and slots. You can connect signals to slots (which simply are class methods), to
 * functions in general, and to other signals.<br>
 * 
 * Here is a comparison between callback functions and signals/slots:
 *
 * <table style="border: 0px none;">
 * <tr><th>Callback functions</th><th>Signals and slots</th></tr>
 * <tr style="vertical-align: top;"><td>
 * \code
 * function ClassA() {
 *   var self = this
 *   this._callbackFunction = null
 *   
 *   this.setCallback = function(callback) {
 *     self._callbackFunction = callback
 *   }
 *   
 *   this.doSomething = function() {
 *     console.log("doing something")
 *     var result = 4711
 *     self._callbackFunction(result)
 *   }
 * }
 * 
 * function ClassB() {
 *   var self = this
 *   this.handleResult = function(result) {
 *     console.log("got result: " + result)
 *   } 
 * }
 * 
 * var a = new ClassA()
 * var b = new ClassB()
 * a.setCallback(b.handleResult)
 * a.doSomething()
 * \endcode
 * </td><td>
 * \code
 * MLAB.createNamespace("Demo")
 * MLAB.Demo.deriveClass("ClassA", MLAB.Core.Object, {
 *   ClassA: function() {
 *     MLAB.Demo.ClassA.super.constructor.call(this)
 *     this.registerSignal("didSomething")
 *   },
 *   
 *   doSomething: function() {
 *     console.log("doing something")
 *     var result = 4711
 *     this.emit("didSomething", result)
 *   },
 * })
 * 
 * MLAB.Demo.deriveClass("ClassB", MLAB.Core.Object, {
 *   ClassB: function() {
 *     MLAB.Demo.ClassB.super.constructor.call(this)
 *   },
 *   
 *   handleResult: function(result) {
 *     console.log("got result: " + result)
 *   },
 * })
 * 
 * var a = new ClassA()
 * var b = new ClassB()
 * a.connect("didSomething", b, "handleResult")
 * a.doSomething() 
 * \endcode
 * </td></tr>
 * </table>
 */
MLAB.Core.defineClass("Object", {
  Object: function() {
    this._slotsBySignalByReceiver = {}
    this._registeredSignals = []
    this._signalsBlocked = false
    this._callbacksBySignal = {}
    this._targetSignalsBySignal = {}
  },
  
  /** \fn MLAB.Core.Object.blockSignals
   * 
   * Sets if signals are blocked, which means that signals are suppressed in situations
   * where they would have been emitted.
   * 
   * \param blocked If true, signals are blocked, otherwise signals will be emitted.
   * \return Returns true if signals were blocked before calling this function, false otherwise.
   */
  blockSignals: function(blocked) {
    var signalsBlocked = this._signalsBlocked
    this._signalsBlocked = blocked
    return signalsBlocked
  },
  
  /** \fn MLAB.Core.Object.signalsBlocked
   * 
   * Returns true if signals are blocked.
   * 
   * \return Returns true if signals are blocked, false otherwise.
   */
  signalsBlocked: function() {
    return this._signalsBlocked
  },
  
  /** \fn MLAB.Core.Object.registerSignal
   * 
   * Registers a signal. Only registered signals can be emitted.
   * 
   * \param signal The signal name that will be registered.
   * \throw String Throws an exception if the signal is already registered.
   */
  registerSignal: function(signal) {
    if (this._registeredSignals.indexOf(signal) < 0) {
      this._registeredSignals.push(signal)
    } else {
      MLAB.Core.throwException("Signal is already registered: " + signal)
    }
  },
  
  /** \fn MLAB.Core.Object.isSignalRegistered
   * 
   * Returns true if the given signal is registered.
   * 
   * \return Returns true if the given signal is registered, false otherwise.
   */
  isSignalRegistered: function(signal) {
    return (this._registeredSignals.indexOf(signal) >= 0)
  },
  
  /** \fn MLAB.Core.Object.emit
   * 
   * Emits a signal. The call order of connected functions is:
   * <ol>
   *   <li>connected slots</li>
   *   <li>connected callbacks</li>
   *   <li>connected signals</li>
   * </ol>
   * 
   * \param signal The signal that will be emitted.
   * \throw String Throws an exception if the signal is not registered.
   */
  emit: function(signal) {
    if (this._registeredSignals.indexOf(signal) < 0) {
      MLAB.Core.throwException("Signal is not registered: " + signal)
    }
    if (this._signalsBlocked) { return }
    var args = []
    for (var i=1; i<arguments.length; i++) {
      args.push(arguments[i])
    }

    var slotsByReceiver = this._slotsBySignalByReceiver[signal]
    if (typeof(slotsByReceiver) !== "undefined") {
      for (var receiver in slotsByReceiver) {
        var slots = slotsByReceiver[receiver]
        if (typeof(slots) === "undefined") {
          MLAB.Core.throwException("Object.emit(): no slots for the receiver found while emitting this signal: '" + signal + "'")
        } else {
          for (var slot in slots) {
            slots[slot].apply(receiver, args)
          }
        }
      }
    }
    
    var callbacks = this._callbacksBySignal[signal]
    if (typeof(callbacks) !== "undefined") {
      for (var i=0; i<callbacks.length; i++) {
        callbacks[i].apply(null, args)
      }
    }
    
    var targetSignals = this._targetSignalsBySignal[signal]
    if (typeof(targetSignals) !== "undefined") {
      for (var i=0; i<targetSignals.length; i++) {
        var ts = targetSignals[i] 
        var args = [ts.signal]
        for (var i=1; i<arguments.length; i++) {
          args.push(arguments[i])
        }
        ts.receiver.emit.apply(ts.receiver, args)
      }
    }
  },
  
  /** \fn MLAB.Core.Object.connectSignal
   * 
   * Connects a signal of this object to the signal of the receiver, so
   * that if this signal is emitted, the target signal on the receiver
   * is also emitted. 
   * 
   * \param signal The signal that will be connected.
   * \param receiver The object on which the target signal will be emitted.
   * \param targetSignal The target signal name of the receiver.
   * \throw String Throws an exception if the signal or targetSignal is not registered.
   */
  connectSignal: function(signal, receiver, targetSignal) {
    if (this._registeredSignals.indexOf(signal) < 0) {
      MLAB.Core.throwException("Signal is not registered: " + signal)
    }
    if (!receiver.isSignalRegistered(targetSignal)) {
      MLAB.Core.throwException("Receiver signal '" + targetSignal + "' is not registered: " + receiver.getClassName())
    }
    var targetSignals = this._targetSignalsBySignal[signal]
    if (typeof(targetSignals) === "undefined") {
      targetSignals = []
      this._targetSignalsBySignal[signal] = targetSignals
    }
    targetSignals.push({receiver: receiver, signal: targetSignal})
  },
  
  /** \fn MLAB.Core.Object.connectCallback
   * 
   * Connects a signal of this object to the given callback function. Note that the callback
   * may require to be bound to an object. (TODO: add REFERENCE TO BUILTIN callback() FUNCTION)
   * 
   * \param signal The signal that will be connected.
   * \param callback The function that will be called.
   * \throw String Throws an exception if the signal is not registered.
   */
  connectCallback: function(signal, callback) {
    if (this._registeredSignals.indexOf(signal) < 0) {
      MLAB.Core.throwException("Signal is not registered: " + signal)
    }
    var callbacks = this._callbacksBySignal[signal]
    if (typeof(callbacks) === "undefined") {
      callbacks = []
      this._callbacksBySignal[signal] = callbacks
    }
    callbacks.push(callback)
  },
  
  /** \fn MLAB.Core.Object.disconnectCallback
   * 
   * Disconnects a signal of this object from the given callback function.
   * 
   * \param signal The signal that will be disconnected.
   * \param callback The function that is connected to the given signal.
   * \throw String Throws an exception if the signal is not registered or if the callback is not connected to the signal.
   */
  disconnectCallback: function(signal, callback) {
    if (this._registeredSignals.indexOf(signal) < 0) {
      MLAB.Core.throwException("Signal is not registered: " + signal)
    }
    var callbacks = this._callbacksBySignal[signal]
    if (typeof(callbacks) === "undefined" || callbacks.indexOf(callback) < 0) {
      MLAB.Core.throwException("Callback is not connected to signal " + signal)
    }
    callbacks.remove(callback)
  },
  
  /** \fn MLAB.Core.Object.connect
   * 
   * Connects a signal of this object to the slot of the receiver.
   * 
   * \param signal The signal that will be disconnected.
   * \param receiver The object on which the slot will be called.
   * \param slot The name of the method that will be connected.
   * \throw String Throws an exception if the signal is not registered or if the slot is already connected to the signal.
   */
  connect: function(signal, receiver, slot) {
    if (this._registeredSignals.indexOf(signal) < 0) {
      MLAB.Core.throwException("Signal is not registered: " + signal)
    }
    if (!(slot in receiver)) {
      MLAB.Core.throwException("Object.connect(): no such slot found on the receiver: " + slot)
    }
    var slotsByReceiver = this._slotsBySignalByReceiver[signal]
    if (typeof(slotsByReceiver) === "undefined") {
      slotsByReceiver = {}
      this._slotsBySignalByReceiver[signal] = slotsByReceiver
    }
    var slots = slotsByReceiver[receiver]
    if (typeof(slots) === "undefined") {
      slots = {}
      slotsByReceiver[receiver] = slots 
    }
    if (slot in slots) {
      MLAB.Core.throwException("Object.connect(): the slot '" + slot + "' of the receiver is already connected to this signal: '" + signal + "'")
    }
    slots[slot] = receiver[slot].bind(receiver)
  },
  
  /** \fn MLAB.Core.Object.disconnectReceiver
   * 
   * Disconnects a signal of this object from all slots of the receiver.
   * 
   * \param signal The signal that will be disconnected.
   * \param receiver The receiver that has slots that are connected to the signal.
   * \throw String Throws an exception if the signal is not registered or if the receiver has no slots that are connected to the signal.
   */
  disconnectReceiver: function(signal, receiver) {
    if (this._registeredSignals.indexOf(signal) < 0) {
      MLAB.Core.throwException("Signal is not registered: " + signal)
    }
    var slotsByReceiver = this._slotsBySignalByReceiver[signal]
    if (typeof(slotsByReceiver) === "undefined") {
      MLAB.Core.throwException("Object.disconnectReceiver(): no slot is connected to this signal: '" + signal + "'")
    }
    if (typeof(slotsByReceiver[receiver]) === "undefined") {
      MLAB.Core.throwException("Object.disconnectReceiver(): no slot of the receiver is connected to this signal: '" + signal + "'")
    }
    delete slotsByReceiver[receiver]
  },
  
  /** \fn MLAB.Core.Object.disconnect
   * 
   * Disconnects a signal of this object a the slots of the receiver.
   * 
   * \param signal The signal that will be disconnected.
   * \param receiver The receiver of the connected slot.
   * \param signal The name of the slot that is connected to the signal.
   * \throw String Throws an exception if the signal is not registered or if the slot is not connected to the signal.
   */
  disconnect: function(signal, receiver, slot) {
    if (this._registeredSignals.indexOf(signal) < 0) {
      MLAB.Core.throwException("Signal is not registered: " + signal)
    }
    var slotsByReceiver = this._slotsBySignalByReceiver[signal]
    if (typeof(slotsByReceiver) === "undefined") {
      MLAB.Core.throwException("Object.disconnect(): no slot is connected to this signal: '" + signal + "'")
    }
    var slots = slotsByReceiver[receiver]
    if (typeof(slots) === "undefined") {
      MLAB.Core.throwException("Object.disconnect(): no slot of the receiver is connected to this signal: '" + signal + "'")
    }
    if (slot in slots) {
      // no slot of the receiver is connected to this signal
      delete slots[slot]
      if (slots.length === 0) {
        // no receiver is connected to this signal
        delete slotsByReceiver[receiver]
        if (Object.keys(slotsByReceiver).length === 0) {
          // no slot is connected to this signal
          delete this._slotsBySignalByReceiver[signal]
        }
      }
    } else {
      MLAB.Core.throwException("Object.connect(): the slot '" + slot + "' of the receiver is not connected to this signal: '" + signal + "'")
    }
  }
})

/** \fn MLAB.Core.connect
   * 
   * Connects a signal of the sender to the slots of the receiver. This is a convenience function
   * that calls sender.connect(signal, receiver, slot).
   * 
   * \param sender The sender of the signal.
   * \param signal The signal that will be connected.
   * \param receiver The receiver of the slot.
   * \param slot The name of the slot that will be connected to the signal.
   * \throw String Throws an exception if the signal is not registered or if the slot is already connected to the signal.
   */
MLAB.Core.connect = function(sender, signal, receiver, slot) {
  sender.connect(signal, receiver, slot)
}

/** \fn MLAB.Core.Object.disconnect
 * 
 * Disconnects a signal of the sender from the slot of the receiver. This is a convenience function
   * that calls sender.disconnect(signal, receiver, slot).
 * 
 * \param sender The sender of the signal.
 * \param signal The signal that will be disconnected.
 * \param receiver The receiver of the slot.
 * \param slot The name of the slot that will be disconnected from the signal.
 * \throw String Throws an exception if the signal is not registered or if the slot is not connected to the signal.
 */
MLAB.Core.disconnect = function(sender, signal, receiver, slot) {
  sender.disconnect(signal, receiver, slot)
}
