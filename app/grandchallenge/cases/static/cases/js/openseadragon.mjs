const dziURL = JSON.parse(document.getElementById("dziURL").textContent);
const osdImages = JSON.parse(document.getElementById("osdImages").textContent);

let viewer = OpenSeadragon({
    id: "openseadragonview",
    prefixUrl: osdImages,
    tileSources: dziURL,
    debugMode: false,
    gestureSettingsMouse: {
        flickEnabled: true,
        clickToZoom: false,
        dblClickToZoom: true,
    },
    zoomPerSecond: 0.5,
    zoomPerScroll: 1.3,
    showNavigator: true,
});
