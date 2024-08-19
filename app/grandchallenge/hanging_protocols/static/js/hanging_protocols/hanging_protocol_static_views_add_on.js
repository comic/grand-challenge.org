$(document).ready(function () {
    let jsonDivs = document.querySelectorAll("[id^='id_json']");
    let hpVizDivs = document.querySelectorAll("[id^='hpVisualization']");
    for (let i = 0; i < jsonDivs.length; i++) {
        let jsonString = jsonDivs[i].innerHTML;
        updateHangingProtocolVisualization(hpVizDivs[i].id, jsonString);
    }
});
