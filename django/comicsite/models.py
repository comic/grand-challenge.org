import pdb
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import Group,Permission,User
from django.contrib.sites.models import get_current_site
from django.core.mail import send_mail
from django.db.models import get_app, get_models
from django.template import loader, Context
from django.template.loader import get_template
from django.contrib.sites.models import get_current_site

from django.utils.html import strip_tags
from userena.signals import signup_complete
from comicmodels.signals import new_admin,file_uploaded
from comicmodels.models import ComicSite

logger = logging.getLogger("django")

# =============================== permissions ===================================
# put permissions code here because signal receiver code should go into models.py
# according to https://docs.djangoproject.com/en/dev/topics/signals/#connecting-receiver-functions
# TODO: where should this code go? This does not seem like a good place for permissions

def set_project_admin_permissions(sender, **kwargs):
    """ Set permissions so a user can enter the admin interface and edit a
    project

    """
    user = kwargs['user']

    # add this user to the projectadminsgroup, which means user can see and edit standard
    # objects types in admin.
    projectadmingroup = get_or_create_projectadmingroup()
    user.groups.add(projectadmingroup)

    # set staff status so user can access admin interface. User will still have to
    # activate through email link before being able to log in at all.
    user.is_staff = True
    user.save()

def get_or_create_projectadmingroup():
    """ create the group 'projectadmin' which should have class-level permissions for all
    models a project admin can edit. E.g. add/change/delete comicsite, page,
    dropboxfolder. If group does not exists, recreate with default permissions.
    """
    (projectadmins,created) = Group.objects.get_or_create(name='projectadmins')

    if created:
        # if projectadmins group did not exist, add default permissions.
        # adding permissions to all models in the comicmodels app.
        appname = 'comicmodels'
        app = get_app(appname)
        for model in get_models(app):
            classname = model.__name__.lower()
            add_standard_perms(projectadmins,classname,appname)

    return projectadmins


def add_standard_perms(group,classname,app_label):
    """ convenience function to add add_classname,change_classname,delete_classname
    permissions to permissionsgroup group

    """

    can_add = Permission.objects.get(codename="add_"+classname, content_type__app_label=app_label)
    can_change = Permission.objects.get(codename="change_"+classname,
                                        content_type__app_label=app_label)
    can_delete = Permission.objects.get(codename="delete_"+classname,
                                        content_type__app_label=app_label)

    group.permissions.add(can_add,can_change,can_delete)


# when a user activates account, set permissions. dispatch_uid makes sure the receiver is only
# registered once.  see https://docs.djangoproject.com/en/dev/topics/signals/
signup_complete.connect(set_project_admin_permissions,dispatch_uid="set_project_\
                            admin_permissions_reveiver")


# ======================================= sending notification emails ====================


def send_existing_project_link_submission_notification_email(request,obj):
    """ When someone has completed the form to submit a new existing challenge 
    site for the overview, let this know to all admins of the main project    
    params:
    obj:         a ProjectMetaData object, which is the database object which 
                 has just been created by submitting the form 
                     
    """        
    
    title = 'Existing project form submitted:"{0}"'.format(obj.title)
    mainproject = ComicSite.objects.get(short_name=settings.MAIN_PROJECT_NAME)
        
    kwargs={'obj':obj,
            'site':get_current_site(request),
            'mainproject':mainproject}
    for admin in mainproject.get_admins():
        if admin.email == '':
            continue
        kwargs["admin"] = admin
        logger.info("Sending existing project submission notification email to '{}'".format(admin.email))
        send_templated_email(title, "admin/emails/existing_project_link_submission_notification_email.txt",kwargs,[admin.email]
                        ,"noreply@"+get_current_site(request).domain, fail_silently=False)
        
    #send_mail(title, message, "noreply@"+site.domain ,[new_admin.email], fail_silently=False)

def send_participation_request_notification_email(request,obj):
    """ When a user requests to become a participant, let this know to all admins            
    
    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user requested
                 participation for which project
    
    """        
    
    
    title = 'New participation request for {0}'.format(obj.project.short_name)
    mainportal = get_current_site(request)
    kwargs={'user':obj.user,            
            'site':mainportal,
            'project':obj.project}
    for admin in obj.project.get_admins():
        kwargs["admin"] = admin 
        send_templated_email(title, "admin/emails/participation_request_notification_email.txt",kwargs,[admin.email]
                        ,"noreply@"+mainportal.domain, fail_silently=False)
    #send_mail(title, message, "noreply@"+site.domain ,[new_admin.email], fail_silently=False)
    
    


def send_participation_request_accepted_email(request,obj):
    """ When a users requests to become a participant is accepted, let the user know            
    
    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user requested
                 participation for which project
    
    """        
    
    title = obj.project.short_name + ' participation request accepted'    
    mainportal = get_current_site(request)
    kwargs={'user':obj.user,
            'adder':request.user,
            'site':mainportal,
            'project':obj.project}

    #send_mail(title, message, "noreply@"+site.domain ,[new_admin.email], fail_silently=False)
    send_templated_email(title, "admin/emails/participation_request_accepted_email.txt",kwargs,[obj.user.email]
                        ,"noreply@"+mainportal.domain, fail_silently=False)


def send_participation_request_rejected_email(request,obj):
    """ When a users requests to become a participant is rejected, let the user know            
    
    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user requested
                 participation for which project
    
    """        
    
    title = obj.project.short_name + 'participation request rejected'
    mainportal = get_current_site(request)
    kwargs={'user':obj.user,
            'adder':request.user,
            'site':mainportal,
            'project':obj.project}

    #send_mail(title, message, "noreply@"+site.domain ,[new_admin.email], fail_silently=False)
    send_templated_email(title, "admin/emails/participation_request_rejected_email.txt",kwargs,[obj.user.email]
                        ,"noreply@"+mainportal.domain, fail_silently=False)


# TODO: below: why these confusing signals. These functions are called from comicsite.admin,
# just import them there and use them. Much less confusing.

def send_new_admin_notification_email(sender,**kwargs):

    comicsite = kwargs['comicsite']
    new_admin = kwargs['new_admin']
    site = kwargs['site']
    title = 'You are now admin for '+comicsite.short_name


    #send_mail(title, message, "noreply@"+site.domain ,[new_admin.email], fail_silently=False)
    send_templated_email(title, "admin/emails/new_admin_notification_email.txt",kwargs,[new_admin.email]
                        ,"noreply@"+site.domain, fail_silently=False)

# connect to signal
new_admin.connect(send_new_admin_notification_email,dispatch_uid='send_new_admin_notification_email')


def send_file_uploaded_notification_email(sender,**kwargs):

    uploader = kwargs['uploader']
    comicsite = kwargs['comicsite']
    site = kwargs['site']
    title = "New upload for %s: '%s' " % (comicsite.short_name,kwargs["filename"])
    admins = User.objects.filter(groups__name=comicsite.admin_group_name())

    if not admins:
        admin_email_adresses = [x[1] for x in settings.ADMINS]
        kwargs['additional_message'] = '<i> Message from COMIC: I could not\
        find any administrator for '+comicsite.short_name+'. Somebody needs to\
        know about this new upload, so I am Sending this email to everyone set\
        as general COMIC admin (ADMINS in the /comic/settings/ conf file). To\
        stop getting these messages, set an admin for\
        '+comicsite.short_name+'.</i> <br/><br/>'
    else:
        kwargs['additional_message'] = ''
        admin_email_adresses = [x.email for x in admins]
    
    kwargs['project'] = comicsite
    send_templated_email(title, "admin/emails/file_uploaded_email.txt",kwargs,
                         admin_email_adresses ,"noreply@"+site.domain,
                         fail_silently=False)



# connect to signal
file_uploaded.connect(send_file_uploaded_notification_email,
                      dispatch_uid='send_file_uploaded_notification_email')



def send_templated_email(subject, email_template_name, email_context, recipients,
                        sender=None,bcc=None, fail_silently=True, files=None):

    """
    send_templated_mail() is a wrapper around Django's e-mail routines that
    allows us to easily send multipart (text/plain & text/html) e-mails using
    templates that are stored in the database. This lets the admin provide
    both a text and a HTML template for each message.

    email_template_name is the slug of the template to use for this message (see
        models.EmailTemplate)

    email_context is a dictionary to be used when rendering the template

    recipients can be either a string, eg 'a@b.com', or a list of strings.

    sender should contain a string, eg 'My Site <me@z.com>'. If you leave it
        blank, it'll use settings.DEFAULT_FROM_EMAIL as a fallback.

    bcc is an optional list of addresses that will receive this message as a
        blind carbon copy.

    fail_silently is passed to Django's mail routine. Set to 'True' to ignore
        any errors at send time.

    files can be a list of file paths to be attached, or it can be left blank.
        eg ('/tmp/file1.txt', '/tmp/image.png')

    """
    
    from comicmodels.models import get_project_admin_instance_name
    
    
    c = Context(email_context)
    # Add current app so {% url admin:index %} will resolve to project admin
    # like /site/vessel12/admin instead of /admin
    # if there is no project defined, do not add current app, which will render
    # email with links to main admin
    if "project" in c:  
        c.current_app =  c['project'].get_project_admin_instance_name()
        
    if not sender:
        sender = settings.DEFAULT_FROM_EMAIL

    template = loader.get_template(email_template_name)

    text_part = strip_tags(template.render(c))
    html_part = template.render(c)
    
    if type(recipients) == str:
        if recipients.find(','):
            recipients = recipients.split(',')
    elif type(recipients) != list:
        recipients = [recipients,]
    
    recipients = remove_empty(recipients)
    
    msg = EmailMultiAlternatives(subject,
                                text_part,
                                sender,
                                recipients,
                                bcc=bcc)
    msg.attach_alternative(html_part, "text/html")

    if files:
        if type(files) != list:
            files = [files,]

        for file in files:
            msg.attach_file(file)

    return msg.send(fail_silently)

def remove_empty(adresses):
    """ Remove invalid email adresses from list
    Currently only removed empty
    
    """
    cleaned = []
    for adress in adresses:
        if adress != "":
            cleaned.append(adress)
             
    
    return cleaned
