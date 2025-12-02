from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Intentar buscar por email primero (case-insensitive)
        user = UserModel._default_manager.filter(email__iexact=username).first()
        
        # Si no se encuentra por email, buscar por username
        if not user:
            user = UserModel._default_manager.filter(username__iexact=username).first()
        
        if not user:
            return None
            
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None