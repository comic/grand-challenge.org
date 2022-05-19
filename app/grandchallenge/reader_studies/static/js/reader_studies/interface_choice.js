$(document).ready(function() {
    const answerTypeToInterfaceMap = JSON.parse(answerTypeToInterfaceMapJson.innerText);
    const $interfaceSelect = $('#id_interface');
    const $answerTypeSelect = $('#id_answer_type');
    const allOptions = $interfaceSelect.children().toArray();

    function updateInterfaceChoices() {
        $interfaceSelect.empty().append(allOptions[0])
        const allowedInterfaces = answerTypeToInterfaceMap[$answerTypeSelect.val()];
        if (allowedInterfaces) {
            const filteredOptions = allOptions.filter(o => allowedInterfaces.map(ai => ai.toString()).includes(o.value));
            $interfaceSelect.append(filteredOptions);
        }
    }
    $answerTypeSelect.change(updateInterfaceChoices);
    updateInterfaceChoices();
});
