import mimetypes

from django.http import HttpResponse
from django.utils.encoding import smart_str


def serve_file(file, save_as=False, content_type=None):
    filename = file.name.rsplit('/')[-1]
    filename = filename.rsplit('\\')[-1]
    if save_as is True:
        save_as = filename
    if not content_type:
        content_type = mimetypes.guess_type(filename)[0]
    return xsendfile(file, save_as=save_as, content_type=content_type)


def xsendfile(file, save_as, content_type):
    """Lets the web server serve the file using the X-Sendfile extension"""
    response = HttpResponse(content_type=content_type)
    response['X-Accel-Redirect'] = file.name
    if save_as:
        response['Content-Disposition'] = smart_str(
            u'attachment; filename=%s' % save_as
        )
    if file.size is not None:
        response['Content-Length'] = file.size
    return response
