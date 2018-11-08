"""
APIView endpoints for user creating
"""
import logging
import re
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from social_django.models import UserSocialAuth

from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from openedx.core.lib.api.authentication import OAuth2AuthenticationAllowInactiveUser
from openedx.core.lib.api.permissions import ApiKeyHeaderPermission
from student.views import create_account_with_params
from third_party_auth.models import OAuth2ProviderConfig
from django.core.exceptions import ObjectDoesNotExist

log = logging.getLogger(__name__)


class CreateUserAccountWithoutPasswordView(APIView):
    """
    Create user account.
    """
    authentication_classes = (OAuth2AuthenticationAllowInactiveUser,)
    permission_classes = (ApiKeyHeaderPermission,)
    
    _error_dict = {
        "username": "Username is required parameter.",
        "email": "Email is required parameter.",
        "gender": "Gender parameter must contain 'm'(Male), 'f'(Female) or 'o'(Other. Default if parameter is missing)",
        "uid": "Uid is required parameter."
    }
    
    def post(self, request):
        """
        Create a user by  the email and the username.
        """
        data = request.data
        data['honor_code'] = "True"
        data['terms_of_service'] = "True"
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        try:
            email = self._check_available_required_params(request.data.get('email'), "email")
            username = self._check_available_required_params(request.data.get('username'), "username")
            uid = self._check_available_required_params(request.data.get('uid'), "uid")
            data['gender'] = self._check_available_required_params(
                request.data.get('gender', 'o'), "gender", ['m', 'f', 'o']
            )
            if check_account_exists(username=username, email=email):
                return Response(data={"error_message": "User already exists"}, status=status.HTTP_409_CONFLICT)
            if UserSocialAuth.objects.filter(uid=uid).exists():
                return Response(data={"error_message": "Parameter 'uid' isn't unique."}, status=status.HTTP_409_CONFLICT)
            
            data['name'] = "{} {}".format(first_name, last_name).strip() if first_name or last_name else username
            data['password'] = uuid4().hex
            user = create_account_with_params(request, data)
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = True
            user.save()
            idp_name = OAuth2ProviderConfig.objects.first().backend_name
            UserSocialAuth.objects.create(user=user, provider=idp_name, uid=uid)
        except ValueError as e:
            log.error(e.message)
            return Response(
                data={"error_message": e.message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            return Response(data={"error_message": e.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data={'user_id': user.id, 'username': username}, status=status.HTTP_200_OK)

    def patch(self, request):
        """
        Update user by social auth uid
        """
        try:
            uid = self._check_available_required_params(request.data.get('uid'), "uid")
            user_social_auth = UserSocialAuth.objects.select_related("user__id", "user__username").get(uid=uid)
            first_name = request.data.get('first_name')
            last_name = request.data.get('last_name')
            email = request.data.get('email')
            username = request.data.get('username')
            gender = request.data.get('gender')

            if not (first_name or last_name or email or username or gender):
                return Response(
                    data={'user_id': user_social_auth.user.id, 'username': user_social_auth.user.username},
                    status=status.HTTP_200_OK
                )
            
            if email:
                validate_email(email)
            if username and re.sub(r'[a-zA-Z0-9_]', '', username):
                #TODO (AndreyLykhoman): write correct message
                return Response(
                    data={"error_message": "Wrong username"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            conflicts = check_account_exists(username=username, email=email)
            if conflicts:
                conflicts_string = " and the ".join(conflicts)
                return Response(
                    data={"error_message": "User already exists with given the {}".format(conflicts_string)},
                    status=status.HTTP_409_CONFLICT
                )
            user = user_social_auth.user
            user.username = username or user.username
            user.email = email or user.email
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            
            if first_name or last_name:
                new_full_name = "{} {}".format(user.first_name, user.last_name).strip()
                user.profile.name = new_full_name
            
            if gender:
                gender = self._check_available_required_params(
                    request.data.get('gender', 'o'), "gender", ['m', 'f', 'o']
                )
                user.profile.gender = gender

            user.profile.save()
            user.save()
        except ObjectDoesNotExist:
            return Response(
                data={"error_message": "User is missing with given the 'uid'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as e:
            log.error(e.message)
            return Response(
                data={"error_message": e.message},
                status=status.HTTP_400_BAD_REQUEST,
            )
       
        
        except ValidationError as e:
            return Response(data={"error_message": e.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data={'user_id': user.id, 'username': username}, status=status.HTTP_200_OK)

    def _check_available_required_params(self, parameter, parameter_name, values_list=None):
        """
        Check required parameter is correct.

        If parameter isn't correct ValueError is raised.

        :param parameter: object
        :param parameter_name: string. Parameter's name
        :param values_list: List of values
    
        :return: parameter
        """
        if not parameter or (values_list and isinstance(values_list, list) and parameter not in values_list):
            raise ValueError(self._error_dict[parameter_name].format(value=parameter))
        return parameter
        
