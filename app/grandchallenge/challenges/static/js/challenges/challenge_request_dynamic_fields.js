function updateBudgetFields(){
    let inputs = document.querySelectorAll("#budget-fields input, #type-2-fields textarea");
    if (document.getElementById("id_challenge_type").value == "1"){
        document.getElementById("budget-fields").style.display = 'none';
        document.getElementById("type-2-fields").style.display = 'none';
        for(var i = 0, len = inputs.length; i < len; i++) {
            inputs[i].required = false;
        }
    }
    else if (document.getElementById("id_challenge_type").value == "2"){
        document.getElementById("budget-fields").style.display = 'block';
        document.getElementById("type-2-fields").style.display = 'block';
        for(var i = 0, len = inputs.length; i < len; i++) {
            inputs[i].required = true;
        }
    }
}

function updateExtraField(fieldName, helpText){
    let checkboxFieldId = 'id_' + fieldName
    let extraFieldDiv = 'div_id_' + fieldName + '_extra'
    let extraFieldId = 'id_' + fieldName + '_extra'
    let checkbox = document.getElementById(checkboxFieldId);
    if (checkbox.checked) {
        document.getElementById(extraFieldDiv).style.display = 'none';
        document.getElementById(extraFieldId).required = false;
    } else if (checkbox.value == "2" ) {
        document.getElementById(extraFieldDiv).style.display = 'none';
        document.getElementById(extraFieldId).required = false;
    } else {
        document.getElementById(extraFieldDiv).style.display = 'block';
        document.getElementById(extraFieldId).required = true;
        document.getElementById(extraFieldDiv).querySelector('label').innerHTML = "Why are you not willing/able to " + helpText + "? *"
    }
}

$(document).ready(function() {
    updateBudgetFields();
    updateExtraField('long_term_commitment', 'support this challenge long-term');
    updateExtraField('data_license', 'use a CC-BY license for your data');
    updateExtraField('challenge_type', 'host your challenge as a Type 2 challenge');
});
