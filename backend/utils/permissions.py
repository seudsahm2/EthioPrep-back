from rest_framework.permissions import BasePermission


def is_admin_principal(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return bool(
        getattr(user, "role", "") == "admin"
        or getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
        or user.groups.filter(name__iexact="admin").exists()
    )


class IsAdminUserRole(BasePermission):
    def has_permission(self, request, view):
        return is_admin_principal(getattr(request, "user", None))
