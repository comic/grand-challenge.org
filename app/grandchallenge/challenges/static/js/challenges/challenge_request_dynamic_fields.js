function updateBudgetFields(){
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

function updateLongTermCommitmentField(){
    let checkbox = document.getElementById("id_long_term_commitment");
    if (checkbox.checked) {
        document.getElementById("div_id_long_term_commitment_extra").style.display = 'none';
    } else {
        document.getElementById("div_id_long_term_commitment_extra").style.display = 'block';
        document.getElementById("div_id_long_term_commitment_extra").classList.add('ml-3');
        document.getElementById("id_long_term_commitment_extra").required = true;
        document.getElementById("div_id_long_term_commitment_extra").querySelector('label').innerHTML = "Why are you not willing/able to support this challenge long-term? *"
    }
}

function updateExtraField(fieldName, helpText){
    let checkboxFieldId = 'id_' + fieldName
    let extraFieldDiv = 'div_id_' + fieldName + '_extra'
    let extraFieldId = 'id_' + fieldName + '_extra'
    let checkbox = document.getElementById(checkboxFieldId);
    if (checkbox.checked) {
        document.getElementById(extraFieldDiv).style.display = 'none';
    } else {
        document.getElementById(extraFieldDiv).style.display = 'block';
        document.getElementById(extraFieldDiv).classList.add('ml-3');
        document.getElementById(extraFieldId).required = true;
        document.getElementById(extraFieldDiv).querySelector('label').innerHTML = "Why are you not willing/able to" + helpText + "? *"
    }
}

$(document).ready(function() {
    updateBudgetFields();
    updateLongTermCommitmentField();
    updateExtraField();
});
