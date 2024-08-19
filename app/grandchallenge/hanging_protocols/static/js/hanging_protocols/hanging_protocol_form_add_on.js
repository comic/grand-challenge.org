$(document).ready(function () {
    let jsonString = document.getElementById("id_json").value;
    updateHangingProtocolVisualization("hpVisualization", jsonString);
    document.getElementById('jsoneditor_id_json').addEventListener('input', function(){updateHangingProtocolVisualization()});
    document.getElementById('jsoneditor_id_json').addEventListener('paste', function(){updateHangingProtocolVisualization()});
});
