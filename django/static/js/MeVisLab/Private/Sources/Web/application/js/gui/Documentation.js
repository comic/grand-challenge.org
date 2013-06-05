/** \mainpage MeVisLab Web ToolKit 
 * 
 * \section Contents
 * <p>
 * <ol>
 *   <li>\ref MWT_Introduction</li>
 *   <li>\ref MWT_Integration</li>
 *   <li>\ref MWT_Structure</li>
 *   <li>\ref MWT_Initialization</li>
 *   <li>\ref MWT_Communication</li>
 *   <li>\ref MWT_Plugins</li>
 * </ol>
 * </p>
 * 
 * \section MWT_Introduction Introduction
 * 
 * <p>The MeVisLab Web ToolKit allows for the creation of web based remote clients for MeVisLab applications.</p>
 * <p>It is a JavaScript framework that runs in HTML5 compatible browsers. Its main features are:
 * <ul>
 *   <li>access to synchronized field values</li>
 *   <li>display of remotely rendered images</li>
 *   <li>HTML generation from MDL GUI descriptions</li>
 *   <li>extensible via JavaScript plugins</li>
 * </ul>
 * </p>
 * 
 * \section MWT_Structure Application Structure
 * 
 * The MeVisLab Web Toolkit provides web applications with a given structure. First, there is an object that
 * loads the JavaScript files of the toolkit and handles its initialization: MLAB.GUI.Application. Next, the module
 * creation, initialization, and communication is managed by MLAB.Core.ModuleContext. It contains an MLAB.Core.Module  
 * object, which represents the instantiated module in MeVisLab and provides access to the fields (MLAB.Core.Field).
 * The communication with MeVisLab is implemented with a web socket in MLAB.Core.RemoteManager.
 * 
 * \image html Structure.png Application structure 
 * 
 * \section MWT_Integration Integration into HTML pages
 * 
 * The integration of the MeVisLab Web Toolkit into an HTML page is done by first including the file
 * MeVisLab/Private/Sources/Web/application/js/gui/Application.js. The exact URL to it
 * depends on the web server configuration and relative location of the target HTML file.
 * The Web Toolkit is initialized by calling MLABApp.runApplication(). It expects the name of the application,
 * the name of the application macro module, and an optional settings dictionary as arguments.
 * See MLAB.GUI.ApplicationSettings, MLAB.Core.RenderSettings, and MLAB.Core.ConnectionSettings for possible arguments. Plugins may
 * also evaluate the arguments.
 * 
 * Example:
 * \code
 * <html>
 *   <head>
 *     <script type="text/javascript" src="MeVisLab/Private/Sources/Web/application/js/gui/Application.js"></script>
 *     <script type="text/javascript">
 *       var applicationName = "ExampleApplication"
 *       var macroName = "ExampleMacro"
 *       var arguments = {}
 *       arguments["diagnosis"] = "" // enables diagnosis messages
 *       arguments["urlToMLABRoot"] = "http://example.server.org/ExampleApplication" 
 *       MLABApp.runApplication(applicationName, macroName, arguments)
 *     </script>
 *   </head>
 *   <body>
 *   </body>
 * </html>
 * \endcode
 * 
 * \section MWT_Initialization Application Initialization
 * 
 * The application is initialized by calling MLABApp.runApplication() in an HTML document. It loads
 * and initializes the toolkit, and creates an MLAB.Core.ModuleContext object. The module context
 * contains an MLAB.Core.RemoteManager object, which establishes a web socket connection with MeVisLab.
 * Then it requests the creation of the application macro from MeVisLab, which in turn responds by sending
 * the description of the module (name and type of its fields). After an additional request, the MDL 
 * description is also send. Any JavaScript plugin specified in the MDL will be loaded and initialized now.
 * Finally, HTML elements are generated for the MDL controls.  
 * 
 * \image html InitializationProcess.png Application initialization
 * 
 * \section MWT_Communication Communication
 * 
 * The toolkit communicates with MeVisLab on a server using \ref RemoteMessages "remote messages" via a
 * web socket connection. The communication is bidirectional, i.e. the toolkit and MeVisLab can both send and
 * receive messages. For example, field values are automatically synchronized by using the 
 * MLAB.Core.ModuleSetFieldValuesMessage. Certain messages are however only used in one direction: rendered images
 * and RPCs (remote procedure calls) are only sent from MeVisLab to the toolkit, while \ref MLAB.Core.GenericRequest
 * "generic requests" and \ref MLAB.Core.RenderingQEventMessage "mouse/key events" are only sent from the toolkit to MeVisLab.
 *
 * \image html MeVisLabWebToolkit.png MeVisLab Web Toolkit communication
 * 
 * 
 * \section MWT_Plugins Writing Plugins
 * 
 * Plugins extend the MeVisLab Web Toolkit. They can customize the look and behavior of a web application.
 * For example, they can provide custom CSS rules and replace existing widget implementations. 
 * 
 * A plugin is at least of one JavaScript file. Optionally, it may provide additional CSS and JavaScript files.
 * In this case, it should provide a class derived from MLAB.GUI.PluginBase. It specifies the required files
 * and is loaded by the application. Before the files are loaded, MLAB.GUI.PluginBase.initialize() is called.
 * The plugin can now evaluate the application arguments. Later, after the specified JS and CSS files are loaded,
 * MLAB.GUI.PluginBase.setup() is called. The plugin can now use and initialze the code from the loaded JavaScript files.
 * It is also possible to include third party frameworks like jQuery and YUI using this mechanism.
 * 
 * ExamplePlugin.js:
 * \code
 * MLAB.createNamespace("Example")
 * 
 * MLAB.Example.deriveClass("ExamplePlugin", MLAB.GUI.PluginBase, {
 *   ExamplePlugin: function() {
 *     MLAB.Example.ExamplePlugin.super.constructor.call(this)
 *     
 *     var jsUrls = ["..."]
 *     this.setJSUrls(jsUrls)
 *     
 *     var cssUrls = ["..."]
 *     this.setCSSUrls(cssUrls)
 *   },
 *   
 *   initialize: function(applicationArguments) {
 *     // initialize() is called before the JS and CSS files are loaded
 *     // applicationArguments is a dictionariy containing all application arguments
 *     ...
 *   },
 *   
 *   setup: function() {
 *     // setup() is called after the JS and CSS files have finished loading
 *     ...
 *   },
 * })
 * 
 * MLAB.GUI.Application.loadPlugin(new MLAB.Example.ExamplePlugin())
 * \endcode
 */

/** \defgroup Debugging Debugging Features
 * 
 * This MeVisLab Web Toolkit provides some debugging features. They can be enabled
 * using the applications arguments (see MLAB.GUI.Application.getArguments()):
 * 
 * <ul>
 *   <li><b>Debugging of remote messages</b><p>This which means that whenever a message
 *   is send or received over the web socket connection, it is printed to the console.
 *   The argument to enable this is <i>debugRemoteMessages</i>.</p></li>
 *   <li><b>Logging of diagnosis message</b><p>If enabled messages from the MeVisLab console
 *   are logged to the console. The argument to enable this is <i>diagnosis</i>.</p></li>
 *   <li><b>Showing the MeVisLab IDE</b><p>It can help to inspect the MeVisLab process that is connected
 *   to an MLABModule by showing the IDE on the server. This can be done programmatically
 *   by calling MLABModule.showIDE() for a single module. For example, you could call it 
 *   through the onclick handler of a button.<br>
 *   It is also possible to initially show the IDE of all modules when the page has finished
 *   loading. Pass the application argument <i>showIDE</i> to enable this.</p></li>
 *   
 *   The prefix "[WEB]" is prepended to the messages, so that they are not printed again
 *   to the console when received from MeVisLab.
 * </ul>
 */
