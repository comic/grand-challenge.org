jest.useFakeTimers();

const formHtml = `
<form gc-disable-after-submit>
  <fieldset>
    <button id="fieldset-button" type="submit">Save</button>
  </fieldset>
  <button id="form-button" type="submit">Save</button>
</form>`;

describe("disableAfterSubmit module", () => {
    require("../../../grandchallenge/core/static/js/disable_after_submit");

    let form;
    let fieldset;
    let fieldset_button;
    let form_button;

    beforeEach(() => {
        document.body.innerHTML = formHtml;
        document.dispatchEvent(new Event("DOMContentLoaded"));

        form = document.querySelector("form");
        fieldset = form.querySelector("fieldset");
        fieldset_button = form.querySelector("#fieldset-button");
        form_button = form.querySelector("#form-button");
    });

    function submit() {
        form.dispatchEvent(new Event("submit"));
        jest.advanceTimersByTime(0); // Only hits the 0
    }

    test("form disables on submit", () => {
        expect(fieldset.disabled).toBe(false); // Sanity

        submit();

        // fieldset is disabled
        expect(fieldset.disabled).toBe(true);

        // note: we dont't test fieldset other internals as
        // these are not disabled in jsdom; they are
        // in browser engines
        expect(form_button.disabled).toBe(true);

        // there are spinners
        const fieldset_button_spinner = fieldset_button.querySelector(
            "span.spinner-border",
        );
        expect(fieldset_button_spinner).not.toBeNull();
        const form_button_spinner = form_button.querySelector(
            "span.spinner-border",
        );
        expect(form_button_spinner).not.toBeNull();
    });

    test("form re-enables after timeout", () => {
        submit();

        expect(fieldset.disabled).toBe(true); // Sanity
        jest.runAllTimers();

        // fieldset enabled
        expect(fieldset.disabled).toBe(false);

        // buttons enabled
        expect(fieldset_button.disabled).toBe(false);
        expect(form_button.disabled).toBe(false);

        // Spinners removed
        const fieldset_button_spinner = fieldset_button.querySelector(
            "span.spinner-border",
        );
        expect(fieldset_button_spinner).toBeNull();

        const form_button_spinner = form_button.querySelector(
            "span.spinner-border",
        );
        expect(form_button_spinner).toBeNull();
    });

    test("pageshow persisted resets form state", () => {
        submit();

        expect(fieldset.disabled).toBe(true); // sanity

        window.dispatchEvent(
            new PageTransitionEvent("pageshow", { persisted: true }),
        );

        // fieldset enabled
        expect(fieldset.disabled).toBe(false);

        // buttons enabled
        expect(fieldset_button.disabled).toBe(false);
        expect(form_button.disabled).toBe(false);

        // Spinners removed
        const fieldset_button_spinner = fieldset_button.querySelector(
            "span.spinner-border",
        );
        expect(fieldset_button_spinner).toBeNull();
        const form_button_spinner = form_button.querySelector(
            "span.spinner-border",
        );
        expect(form_button_spinner).toBeNull();
    });

    test("subsequent form submits are prevented", () => {
        const mockEvent = new Event("submit");
        mockEvent.preventDefault = jest.fn();

        form.dispatchEvent(mockEvent);
        jest.advanceTimersByTime(0); // Only hits the 0

        // First time: not prevented
        expect(mockEvent.preventDefault).not.toHaveBeenCalled();

        // Second time: prevented
        form.dispatchEvent(mockEvent);
        expect(mockEvent.preventDefault).toHaveBeenCalled();
    });
});
