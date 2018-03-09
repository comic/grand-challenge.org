from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from jqfileupload.forms import UploadForm


def uploader_widget_test(request: HttpRequest, **kwargs) -> HttpResponse:
    if request.method == "POST":
        test_form = UploadForm(request.POST)
        if test_form.is_valid():
            result = "Success!!!\n"
            result += "\n".join(
                f"  {k}: {v}" for k, v in test_form.cleaned_data.items())

            result += "\n\n"

            f1 = test_form.cleaned_data["upload_form"][0]
            with f1.open() as f:
                the_bytes = f.read(16)
            result += f"""
You uploaded {len(test_form.cleaned_data["upload_form"])} files in the first form.

The first 16 bytes of the first file were: {the_bytes}
            """
        else:
            result = "Validation error:\n"
            result += "\n".join(f"  {e}" for e in test_form.errors)
        return HttpResponse(result, content_type="text/plain")
    else:
        test_form = UploadForm()
        return render(request, "uploader_widget_test.html", {
            "testform": test_form,
        })