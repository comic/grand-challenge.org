/** \class MLAB.Core.SystemInfo
 * 
 * Provides information about the client system (browser).
 */
MLAB.Core.SystemInfoSingleton = function() {
  /** \fn MLAB.Core.SystemInfo.getInternetExplorerVersion
   * 
   * Returns the internet explorer version number.
   * 
   * \return The internet explorer version number, or -1 if the system is not an internet explorer.
   */
  this.getInternetExplorerVersion = function() {
    var rv = -1 // Return value assumes failure.
    if (navigator.appName === 'Microsoft Internet Explorer') {
      var ua = navigator.userAgent
      var re  = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})")
      if (re.exec(ua) !== null) {
        rv = parseFloat( RegExp.$1 )
      }
    }
    return rv
  }
  
  this.isIE = function() {
    return this.getInternetExplorerVersion() >= 0
  }

  /** \fn MLAB.Core.SystemInfo.isIE9
   * 
   *  Returns true if the system is the Internet Explorer 9.
   *  More precisely this function returns if getInternetExplorerVersion() is greater than
   *  or equal to 7, because the Internet Explorer 9 may run in compatibility mode.
   *  
   *  \return A boolean.
   */
  this.isIE9 = function() {
    return this.getInternetExplorerVersion()>=7
  }
 
  /** \fn MLAB.Core.SystemInfo.isIOS
   * Returns true if the system is an IOS device by checking if one of these strings
   * is found in the user agent string: iphone, ipad, ipod.
   * 
   * \return A boolean.
   */
  this.isIOS = function() {
    return (/iphone|ipad|ipod/i.test(navigator.userAgent.toLowerCase()))
  }
  
  this.isWebKit = function() {
    return (/AppleWebKit/i.test(navigator.userAgent.toLowerCase()))
  }
  
  this.isGecko = function() {
    return (/gecko/i.test(navigator.userAgent.toLowerCase())) && 
            !this.isWebKit() // the chrome user agent string may include "like Gecko"
  }

  /** \fn MLAB.Core.SystemInfo.isAndroid
   * 
   * Returns true if the system is an android device by checking if the string
   * "android" is found in the user agent string.
   * 
   *  \return A boolean.
   */
  this.isAndroid = function() {
    return navigator.userAgent.toLowerCase().indexOf("android") >= 0
  }
  
  /** \fn MLAB.Core.SystemInfo.isMacOS
   * 
   * Returns true if the platform is MacOS by checking if the string
   * "Mac" is found in the navigator platform string.
   * 
   *  \return A boolean.
   */
  this.isMacOS = function() {
    return navigator.platform.indexOf("Mac") >= 0
  }
  
  /** \fn MLAB.Core.SystemInfo.isLinux
   * 
   * Returns true if the platform is Linux by checking if the string
   * "Linux" is found in the navigator platform string.
   * 
   *  \return A boolean.
   */
  this.isLinux = function() {
    return navigator.platform.indexOf("Linux") >= 0
  }
  
  /** \fn MLAB.Core.SystemInfo.isWindows
   * 
   * Returns true if the platform is Windows by checking if the string
   * "Win" is found in the navigator platform string.
   * 
   *  \return A boolean.
   */
  this.isWindows = function() {
    return navigator.platform.indexOf("Win") >= 0
  }
}

MLAB.Core.SystemInfo = new MLAB.Core.SystemInfoSingleton()
