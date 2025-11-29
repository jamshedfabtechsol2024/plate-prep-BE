from django.shortcuts import get_object_or_404
from app.models import Page, PagePermission
from app import choices
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied


def check_permissions(user, page_name, permission_type):
    page = get_object_or_404(Page, name=page_name)
    permission = PagePermission.objects.filter(user=user, page=page).first()
    if not permission:
        return False
    return getattr(permission, f"can_{permission_type}", False)

class IsHeadChefRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == choices.Usertypes.HEAD_CHEF

class IsStaffRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == choices.Usertypes.STAFF

class IsAdminOrHeadChef(BasePermission):
    def has_permission(self, request, view):
        """Check if the user is an admin or a head chef. else raise error"""
        return request.user.is_authenticated and (request.user.is_superuser or request.user.role == choices.Usertypes.HEAD_CHEF or request.user.role == choices.Usertypes.ADMIN)

class IsAdminOrHeadChefOrStaff(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_superuser or request.user.role == choices.Usertypes.HEAD_CHEF or request.user.role == choices.Usertypes.STAFF)

class TaskEditDeletePermission(BasePermission):
    """
    - Prevents Head Chefs and Staff from editing/deleting tasks assigned to them by an Admin.
    - Admins have full control over all tasks.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user

        if user.role == choices.Usertypes.ADMIN:
            return True

        if obj.user.role == choices.Usertypes.ADMIN:
            if obj.staff == user:
                return False

        return obj.user == user

class IsSubscribedORSuperUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if user.is_superuser:
            return True

        if not user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this resource.")

        if not user.resturant:
            raise PermissionDenied("You are not associated with any restaurant.")

        if not user.resturant.plan:
            raise PermissionDenied("Your restaurant has no active subscription plan.")

        if not user.resturant.plan_end_date or user.resturant.plan_end_date <= timezone.now().date():
            raise PermissionDenied("Your restaurant's subscription has expired. Please renew it to continue.")
        
        return True