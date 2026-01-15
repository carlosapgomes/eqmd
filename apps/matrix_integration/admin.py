from django.contrib import admin

from .models import MatrixDirectRoom, MatrixGlobalRoom


@admin.register(MatrixGlobalRoom)
class MatrixGlobalRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "room_id", "created_at")
    search_fields = ("name", "room_id")
    readonly_fields = ("created_at",)


@admin.register(MatrixDirectRoom)
class MatrixDirectRoomAdmin(admin.ModelAdmin):
    list_display = ("user", "room_id", "created_at", "updated_at")
    search_fields = ("user__email", "user__username", "room_id")
    readonly_fields = ("created_at", "updated_at")
