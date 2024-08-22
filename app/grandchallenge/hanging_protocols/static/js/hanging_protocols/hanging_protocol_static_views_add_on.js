$(document).ready(() => {
    const jsonDivs = document.querySelectorAll("[id^='id_json']");
    const hpVizDivs = document.querySelectorAll("[id^='hpVisualization']");
    for (let i = 0; i < jsonDivs.length; i++) {
        const jsonString = jsonDivs[i].innerHTML;
        updateHangingProtocolVisualization(hpVizDivs[i].id, jsonString);
    }
});
