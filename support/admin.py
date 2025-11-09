

"""
FILE LOCATION: support/admin.py
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import SupportCategory, SupportTicket, TicketMessage, TicketAttachment, FAQ

@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'ticket_count_display']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def ticket_count_display(self, obj):
        count = obj.tickets.filter(status__in=['open', 'in_progress']).count()
        return format_html('<strong>{}</strong>', count)
    ticket_count_display.short_description = 'Open Tickets'

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'subject', 'user', 'category', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['ticket_id', 'subject', 'user__phone_number']
    readonly_fields = ['ticket_id', 'created_at', 'updated_at']
    
    def has_add_permission(self, request):
        return False

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'view_count', 'helpful_count', 'is_published']
    list_filter = ['category', 'is_published']
    search_fields = ['question', 'answer']

