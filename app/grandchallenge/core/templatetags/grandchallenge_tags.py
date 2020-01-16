import logging

from django import template

from grandchallenge.core.templatetags import library_plus
from grandchallenge.subdomains.utils import reverse

register = library_plus.LibraryPlus()
logger = logging.getLogger(__name__)


@register.simple_tag()
def url(view_name, *args, **kwargs):
    return reverse(view_name, args=args, kwargs=kwargs)


@register.tag(name="url_parameter")
def url_parameter(parser, token):
    """Try to read given variable from given url."""
    split = token.split_contents()
    all_args = split[1:]
    if len(all_args) != 1:
        error_message = "Expected 1 argument, found " + str(len(all_args))
        return TemplateErrorNode(error_message)

    else:
        args = {"url_parameter": all_args[0]}
    args["token"] = token
    return UrlParameterNode(args)


class UrlParameterNode(template.Node):
    def __init__(self, args):
        self.args = args

    def make_error_msg(self, msg):
        logger.error(
            "Error in url_parameter tag: '" + ",".join(self.args) + "': " + msg
        )
        errormsg = "Error in url_parameter tag"
        return make_error_message_html(errormsg)

    def render(self, context):
        if self.args["url_parameter"] in context["request"].GET:
            return context["request"].GET[self.args["url_parameter"]]

        else:
            logger.error(
                "Error rendering %s: Parameter '%s' not found in request URL"
                % (
                    "{%  " + self.args["token"].contents + "%}",
                    self.args["url_parameter"],
                )
            )
            error_message = "Error rendering"
            return make_error_message_html(error_message)


class TemplateErrorNode(template.Node):
    """
    Render error message in place of this template tag. This makes it directly
    obvious where the error occured
    """

    def __init__(self, errormsg):
        self.msg = html_encode_django_chars(errormsg)

    def render(self, context):
        return make_error_message_html(self.msg)


def html_encode_django_chars(txt):
    """
    Replace curly braces and percent signs that used in the django template
    tags with their html encoded equivalents.
    """
    txt = txt.replace("{", "&#123;")
    txt = txt.replace("}", "&#125;")
    txt = txt.replace("%", "&#37;")
    return txt


def make_error_message_html(text):
    return (
        '<p><span class="pageError"> '
        + html_encode_django_chars(text)
        + " </span></p>"
    )
