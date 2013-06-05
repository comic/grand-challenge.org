

MLAB.Core.defineClass("Timer", {
  Timer: function() {
    this._interval = 100
    this._timeout = null
    this._callback = null
    this._isSingleShot = false
    this._isStopped = false
    this._intervalCount = 0
  },
  
  setSingleShot: function(flag) {
    this._isSingleShot = flag
  },
  
  setCallback: function(callback) {
    this._callback = callback
  },
  
  setInterval: function(interval) {
    this._interval = interval
  },
  
  stop: function() {
    this._isStopped = true
    if (this._timeout !== null) {
      window.clearTimeout(this._timeout)
      this._timeout = null
    }
  },
  
  start: function() {
    this.stop()
    this._intervalCount = 0
    this._isStopped = false
    this._timeout = window.setTimeout(this.callback("_onTimeout"), this._interval)
  },
  
  getIntervalCount: function() {
    return this._intervalCount
  },
  
  _onTimeout: function() {
    this._intervalCount++
    if (!this._isStopped) { 
      this._callback()
    }
    if (!this._isSingleShot && !this._isStopped) {
      this._timeout = window.setTimeout(this.callback("_onTimeout"), this._interval)
    }
  },
})
