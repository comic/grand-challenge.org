$(document).ready(() => {
    const jsonString = document.getElementById("id_json").value;
    updateHangingProtocolVisualization("hpVisualization", jsonString);
    document
        .getElementById("jsoneditor_id_json")
        .addEventListener("input", () => {
            updateHangingProtocolVisualization();
        });
    document
        .getElementById("jsoneditor_id_json")
        .addEventListener("paste", () => {
            updateHangingProtocolVisualization();
        });
});
