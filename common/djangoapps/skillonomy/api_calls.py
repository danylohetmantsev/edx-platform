"""
Send user's achievements to external service during the course progress
"""
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class APICalls(object):
    """
    Send user data to the Gamification server
    """

    def __init__(self):
        self.is_enabled = settings.FEATURES.get('ENABLE_SKILLONOMY', False)
        if self.is_enabled:
            self.SKILLONOMY_PROPERTIES = settings.FEATURES.get('SKILLONOMY_PROPERTIES', {})
            if not self.SKILLONOMY_PROPERTIES:
                raise ImproperlyConfigured(
                    "You must set `SKILLONOMY_PROPERTIES` when "
                    "`FEATURES['ENABLE_SKILLONOMY']` is True."
                )
            required_params = ("API_URL", "APP_KEY", "APP_SECRET")
            for param in required_params:
                if param not in self.SKILLONOMY_PROPERTIES:
                    raise ImproperlyConfigured(
                        "You must set `{}` in `SKILLONOMY_PROPERTIES`".format(param)
                    )

    def api_call(self, course_id, org, username, event_type, uid):
        data = {
            'course_id': course_id,
            'org': org,
            'username': username,
            'event_type': event_type,
            'uid': uid,
        }
        headers = {
            'App-key': self.SKILLONOMY_PROPERTIES['APP_KEY'],
            'App-secret': self.SKILLONOMY_PROPERTIES['APP_SECRET']
        }
        requests.put(
            self.SKILLONOMY_PROPERTIES['API_URL']+'gamma-profile/',
            data=data,
            headers=headers,
            verify=False
        )
