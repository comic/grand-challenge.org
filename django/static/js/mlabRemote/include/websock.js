if ("WebSocket" in window) {
    Websock_native = true;
} else {
    /* no builtin WebSocket so load web_socket.js */
    Websock_native = false;
    (function () {
        function get_INCLUDE_URI() {
            return (typeof INCLUDE_URI !== "undefined") ?
                INCLUDE_URI : "include/";
        }

        var start = "<script src='" + get_INCLUDE_URI(),
            end = "'><\/script>", extra = "";

        WEB_SOCKET_SWF_LOCATION = get_INCLUDE_URI() +
                    "web-socket-js/WebSocketMain.swf?" + Math.random();
        if (Util.Engine.trident) {
            Util.Debug("Forcing uncached load of WebSocketMain.swf");
            WEB_SOCKET_SWF_LOCATION += "?" + Math.random();
        }
        extra += start + "web-socket-js/swfobject.js" + end;
        extra += start + "web-socket-js/web_socket.js" + end;
        document.write(extra);
    }());
}
