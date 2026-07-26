from rest_framework import permissions

class IsGroupMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        group = obj if hasattr(obj, 'members') else obj.group
        return group.members.filter(user=request.user).exists()