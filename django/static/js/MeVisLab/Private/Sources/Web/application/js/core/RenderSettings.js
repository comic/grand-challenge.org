/** \defgroup RemoteRendering Remote Rendering
 * 
 */

/** \class MLAB.Core.RenderSettings
 * 
 * This class stores settings for the remote rendering.
 * The render settings are only used if streaming is enabled.
 * The settings can be set using the setProperty() method
 * or via the application arguments.
 * 
 * The render settings are:
 * \htmlonly
 * <table>
 *   <thead style="text-align: left;">
 *     <tr><th>name</th><th>type</th><th>default</th></tr>
 *   </thead>
 *   <tbody>
 *     <tr><td>maxPendingImages</td><td>INTEGER</td><td>3</td></tr>
 *     <tr><td>interactiveJpgQuality</td><td>0..100</td><td>75</td></tr>
 *     <tr><td>interactiveImageType</td><td>JPG or PNG</td><td>JPG</td></tr>
 *     <tr><td>interactiveScaling</td><td>0.0..1.0</td><td>1.0</td></tr>
 *     <tr><td>highQualityJpgQuality</td><td>0..100</td><td>100</td></tr>
 *     <tr><td>highQualityImageType</td><td>JPG or PNG</td><td>PNG</td></tr>
 *     <tr><td>highQualityDelayInMs</td><td>INTEGER</td><td>500</td></tr>
 *     <tr><td>minUpdateDelayInMs</td><td>INTEGER</td><td>20</td></tr>
 *     <tr><td>maxUpdateDelayInMs</td><td>INTEGER</td><td>200</td></tr>
 *   </tbody>
 * </table>
 * \endhtmlonly
 * \ingroup RemoteRendering
 */
MLAB.Core.defineClass("RenderSettings", {
  RenderSettings: function() {
     this._isStreamingEnabled = true
     this._settings = {
       maxPendingImages : 3,
       interactiveJpgQuality : 75,
       // Don't send these settings by default, they
       // typically have senseful values on the server side:
       //interactiveImageType : "JPG",
       //highQualityImageType : "PNG",
       //highQualityJpgQuality : 100,
       //highQualityDelayInMs : 500,
       //interactiveScaling : 1.0,
       //maxUpdateDelayInMs : 200,
       //minUpdateDelayInMs : 20
      }
     // can we handle binary WebSocket messages (more space-efficient for images)?
     this._settings["preferBinaryImages"] =
       (typeof(DataView) !== "undefined") && (typeof(Blob) !== "undefined")
  },

  /** \fn MLAB.Core.RenderSettings.clone
   * Clones the RenderSettings
   */
  clone: function() {
    var settings = new MLAB.Core.RenderSettings()
    settings._isStreamingEnabled       = this._isStreamingEnabled
    settings._settings = JSON.parse(JSON.stringify(this._settings));
    return settings
  },
  
  /** \fn MLAB.Core.RenderSettings.setMaxPendingImages
   * 
   * Sets the maximum number of pending images. See getMaxPendingImages().
   * 
   * \param value An integer value.
   */
  setupFromArguments: function(args) {
    if ("streaming" in args)             { this._settings.isStreamingEnabled    = args["streaming"] !== "0" }
    if ("maxPendingImages" in args)      { this._settings.maxPendingImages      = parseInt(args["maxPendingImages"]) }    
    if ("interactiveJpgQuality" in args) { this._settings.interactiveJpgQuality = parseInt(args["interactiveJpgQuality"]) }
    if ("interactiveImageType" in args)  { this._settings.interactiveImageType  = args["interactiveImageType"] }
    if ("interactiveScaling" in args)    { this._settings.interactiveScaling    = parseFloat(args["interactiveScaling"]) }
    if ("highQualityJpgQuality" in args) { this._settings.highQualityJpgQuality = parseInt(args["highQualityJpgQuality"]) }
    if ("highQualityImageType" in args)  { this._settings.highQualityImageType  = args["highQualityImageType"] }
    if ("highQualityDelayInMs" in args)  { this._settings.highQualityDelayInMs  = parseInt(args["highQualityDelayInMs"]) }    
    if ("minUpdateDelayInMs" in args)    { this._settings.minUpdateDelayInMs    = parseInt(args["minUpdateDelayInMs"]) }    
    if ("maxUpdateDelayInMs" in args)    { this._settings.maxUpdateDelayInMs    = parseInt(args["maxUpdateDelayInMs"]) }
    if ("preferBinaryImages" in arguments)    { this._settings.preferBinaryImages    = arguments["preferBinaryImages"] != "0" }

    // for backward compatiblity:
    if ("jpgQuality" in args) { this._settings.interactiveJpgQuality = parseInt(args["jpgQuality"]) }
  },

    /** \fn MLAB.Core.RenderSettings.setProperty
   * 
   * Sets the given property, see constructor for available properties.
   *
   */
  setProperty: function(name, value) { return this._settings[name] = value },

  /** \fn MLAB.Core.RenderSettings.getSettingsDictionary
   * 
   * Get the settings dictionary for sending the message to MeVisLab.
   *
   */
  getSettingsDictionary: function() { return this._settings },
  
  /** \fn MLAB.Core.RenderSettings.setStreamingEnabled
   * 
   * Enables or disables streaming. See isStreamingEnabled().
   * 
   * \param A boolean value.
   */
  setStreamingEnabled: function(enabled) { this._isStreamingEnabled = enabled },
  
  /** \fn MLAB.Core.RenderSettings.isStreamingEnabled
   * 
   * Returns if streaming is enabled or disabled. Streaming is enabled
   * by default.
   * 
   * \return A boolean value.
   */
  isStreamingEnabled: function(enabled) { return this._isStreamingEnabled },
})
