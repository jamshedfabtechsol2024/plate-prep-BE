import threading
from rest_framework_simplejwt.authentication import JWTAuthentication
from app.utils import set_current_user

_request = threading.local()

def set_current_request(request):
    _request.request = request

def get_current_request():
    return getattr(_request, 'request', None)

def get_current_user():
    current_request = get_current_request()
    return getattr(current_request, 'user', None) if current_request else None

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = self.get_jwt_user(request)
        if user:
            set_current_user(user)
        else:
            set_current_user(None)
        
        set_current_request(request)
        response = self.get_response(request)
        set_current_request(None)
        return response

    def get_jwt_user(self, request):
        user = None
        jwt_authenticator = JWTAuthentication()
        try:
            # Decode the token and authenticate the user
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                validated_token = jwt_authenticator.get_validated_token(auth_header.split(' ')[1])
                user = jwt_authenticator.get_user(validated_token)
        except Exception as e:
            print(f"Error Extracting user: {e}")
        return user
