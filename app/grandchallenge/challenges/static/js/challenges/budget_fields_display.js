function updateForm(){
    let inputs = document.getElementById("budget-fields").querySelectorAll("#budget-fields input");
    if (document.getElementById("id_challenge_type").value == "1"){
        document.getElementById("budget-fields").style.display = 'none';
        for(var i = 0, len = inputs.length; i < len; i++) {
            inputs[i].required = false;
        }
    }
    else if (document.getElementById("id_challenge_type").value == "2"){
        document.getElementById("budget-fields").style.display = 'block';
        for(var i = 0, len = inputs.length; i < len; i++) {
            inputs[i].required = true;
        }
    }
}

$(document).ready(function() {
    updateForm();
});
