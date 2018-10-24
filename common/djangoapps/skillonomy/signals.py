"""
Catch changes in user progress and send it by API
"""
import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from opaque_keys.edx.keys import CourseKey
from skillonomy.tasks import send_api_request
from certificates.models import CertificateStatuses
from referrals.models import ActivatedLinks
from xmodule.modulestore.django import modulestore
from django.contrib.sites.models import Site

SKILLONOMY_FIELDS = (
    'skillonomy_base_url',
    'skillonomy_secret',
    'skillonomy_key',
)

log = logging.getLogger(__name__)


# @receiver(post_save, sender='courseware.StudentModule')
# def send_achievement(sender, instance, **kwargs):
#     # Remove check for GAMMA_ALLOWED_USERS after release
#     if instance.module_type in ('video', 'problem'):
#         ## TODO: resolve this when find out how to
#         #if (
#         #    instance.module_type == 'video' and
#         #    (instance.modified - instance.created).total_seconds() <= 1
#         #):
#         #    return None
#         if (
#             instance.module_type == 'problem' and
#             (not instance.grade or type(instance.grade) != float)
#         ):
#             return None
#         data = {
#             'username': instance.student.username,
#             'course_id': unicode(instance.course_id),
#             'org': instance.course_id.org,
#             'event_type': instance.module_type,
#             'uid': unicode(instance.module_state_key),
#         }
#         send_api_request.delay(data)

def _is_valid(fields):
    for field in SKILLONOMY_FIELDS:
        if not fields.get(field):
            log.error('Field "{}" is improperly configured.'.format(field))
            return False
    return True


@receiver(post_save, sender='student.CourseEnrollment')
def send_enroll_achievement(sender, instance, created, **kwargs):
    org = instance.course_id.org
    course_id = unicode(instance.course_id)
    course_key = CourseKey.from_string(course_id)
    course = modulestore().get_course(course_key)
    skillonomy_fields = {
        'skillonomy_secret': course.skillonomy_secret,
        'skillonomy_key': course.skillonomy_key,
        'skillonomy_base_url': course.skillonomy_base_url
    }
    if course.skillonomy_enabled:
        if _is_valid(skillonomy_fields):

            payload = {
                'student_id': "{}:{}".format(instance.user.email, Site.objects.get_current().domain),
                'course_id': course_id,
                'org': org,
                'event_type': 1,
                'uid': '{}_{}'.format(instance.user.pk, course_id),
            }

            data = {
                'payload': payload,
                'secret': course.skillonomy_secret,
                'key': course.skillonomy_key,
                'base_url': course.skillonomy_base_url,
            }
            send_api_request.delay(data)


# @receiver(post_save, sender='certificates.GeneratedCertificate')
# def send_certificate_generation(sender, instance, created, **kwargs):
#     # Remove check for GAMMA_ALLOWED_USERS after release
#     if instance.status == CertificateStatuses.generating:
#         org = instance.course_id.org
#         course_id = unicode(instance.course_id)
#         data = {
#             'username': instance.user.username,
#             'course_id': course_id,
#             'org': org,
#             'event_type': 'course',
#             'uid': '{}_{}'.format(instance.user.pk, course_id),
#         }
#         send_api_request.delay(data)
