import {Inspector, Runtime} from "https://cdn.jsdelivr.net/npm/@observablehq/runtime@4/dist/runtime.js";

if (window.self !== window.top) {
    const observableNotebookJS = JSON.parse(document.getElementById("observableNotebookJS").textContent);
    const selectedCells = JSON.parse(document.getElementById("observableCells").textContent);
    const evaluations = JSON.parse(document.getElementById("evaluations").textContent);

    function setErrorMessage(msg) {
        const alert = document.getElementById("observableAlert");
        alert.textContent = msg
        alert.classList.remove("d-none");

        const cells = document.getElementsByClassName("observableCell");
        while (cells.length > 0) cells[0].remove();
    }

    import(observableNotebookJS).then(
        module => {
            const runtime = new Runtime()
            let main

            if (selectedCells.length === 1 && selectedCells.every((c) => c === "*")) {
                const cell = document.querySelector("#observableCell");
                cell.textContent = "";
                cell.classList.remove("text-center");
                main = runtime.module(module.default, Inspector.into(cell));
            } else {
                main = runtime.module(module.default, (name) => {
                    let selected = selectedCells.indexOf(name);
                    if (selected > -1) {
                        const id = selectedCells[selected].replace(/[\s*]/g, "");  // remove spaces and * from cell names
                        let cell = document.querySelector("#observableCell" + id);
                        cell.classList.remove("text-center");
                        return new Inspector(cell);
                    }
                });
            }

            try {
                main.redefine("evaluations", evaluations);
            } catch (error) {
                setErrorMessage("The variable 'evaluations' has not been defined in the provided notebook.");
            }
        }
    ).catch(() => {
            setErrorMessage("Could not load notebook.");
        }
    );
}
