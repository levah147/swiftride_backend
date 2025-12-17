

"""
FILE LOCATION: support/admin.py
Enhanced admin interfaces for support/helpdesk app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import SupportCategory, SupportTicket, TicketMessage, TicketAttachment, FAQ


@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'ticket_count_display', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20
    list_editable = ['sort_order', 'is_active']
    actions = ['export_as_csv', 'activate_categories', 'deactivate_categories']
    
    def ticket_count_display(self, obj):
        count = obj.tickets.filter(status__in=['open', 'in_progress']).count()
        color = '#dc3545' if count > 10 else '#ffc107' if count > 5 else '#28a745'
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, count
        )
    ticket_count_display.short_description = 'Open Tickets'
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="support_categories_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Slug', 'Description', 'Icon', 'Sort Order', 'Is Active'])
        
        for category in queryset:
            writer.writerow([
                category.name, category.slug, category.description,
                category.icon, category.sort_order,
                'Yes' if category.is_active else 'No'
            ])
        return response
    export_as_csv.short_description = '📥 Export to CSV'
    
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} category/categories activated.')
    activate_categories.short_description = 'Activate selected categories'
    
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} category/categories deactivated.')
    deactivate_categories.short_description = 'Deactivate selected categories'


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = [
        'ticket_id', 'subject', 'user_phone', 'category', 
        'status_badge', 'priority_badge', 'assigned_to', 
        'response_time_display', 'created_at'
    ]
    list_filter = ['status', 'priority', 'category', 'created_at', 'assigned_to']
    search_fields = ['ticket_id', 'subject', 'user__phone_number', 'user__first_name']
    readonly_fields = ['ticket_id', 'created_at', 'updated_at', 'resolved_at', 'closed_at']
    list_per_page = 30
    date_hierarchy = 'created_at'
    actions = [
        'export_tickets_csv', 'assign_to_me', 'mark_in_progress', 
        'mark_resolved', 'mark_closed'
    ]
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_id', 'user', 'subject', 'description', 'category')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'assigned_to')
        }),
        ('Metadata', {
            'fields': ('user_email', 'user_phone', 'created_at', 'updated_at', 'resolved_at', 'closed_at')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'User'
    user_phone.admin_order_field = 'user__phone_number'
    
    def status_badge(self, obj):
        colors = {
            'open': '#dc3545',  # Red
            'in_progress': '#ffc107',  # Yellow
            'waiting_user': '#17a2b8',  # Cyan
            'resolved': '#28a745',  # Green
            'closed': '#6c757d',  # Gray
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def priority_badge(self, obj):
        colors_and_icons = {
            'low': ('#28a745', '⬇️'),
            'medium': ('#ffc107', '➡️'),
            'high': ('#ff6b6b', '⬆️'),
            'urgent': ('#dc3545', '🚨'),
        }
        color, icon = colors_and_icons.get(obj.priority, ('#6c757d', '—'))
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_priority_display().upper()
        )
    priority_badge.short_description = 'Priority'
    priority_badge.admin_order_field = 'priority'
    
    def response_time_display(self, obj):
        response_time = obj.response_time()
        if response_time:
            hours = response_time.total_seconds() / 3600
            if hours < 1:
                return format_html('<span style="color: #28a745;">✓ {}min</span>', int(hours * 60))
            elif hours < 24:
                return format_html('<span style="color: #ffc107;">{:.1f}h</span>', hours)
            else:
                days = hours / 24
                return format_html('<span style="color: #dc3545;">{:.1f}d</span>', days)
        return format_html('<span style="color: #6c757d;">—</span>')
    response_time_display.short_description = 'Response Time'
    
    def export_tickets_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="support_tickets_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Ticket ID', 'Subject', 'User', 'Phone', 'Category',
            'Status', 'Priority', 'Assigned To', 'Created At', 'Resolved At'
        ])
        
        for ticket in queryset.select_related('user', 'category', 'assigned_to'):
            writer.writerow([
                ticket.ticket_id, ticket.subject, ticket.user.get_full_name(),
                ticket.user.phone_number, ticket.category.name,
                ticket.get_status_display(), ticket.get_priority_display(),
                ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Unassigned',
                ticket.created_at, ticket.resolved_at if ticket.resolved_at else 'Not resolved'
            ])
        return response
    export_tickets_csv.short_description = '📥 Export to CSV'
    
    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f'{updated} ticket(s) assigned to you.')
    assign_to_me.short_description = '👤 Assign to me'
    
    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} ticket(s) marked as in progress.')
    mark_in_progress.short_description = '⏳ Mark as in progress'
    
    def mark_resolved(self, request, queryset):
        for ticket in queryset:
            ticket.mark_resolved()
        self.message_user(request, f'{queryset.count()} ticket(s) marked as resolved.')
    mark_resolved.short_description = '✅ Mark as resolved'
    
    def mark_closed(self, request, queryset):
        for ticket in queryset:
            ticket.mark_closed()
        self.message_user(request, f'{queryset.count()} ticket(s) closed.')
    mark_closed.short_description = '🔒 Close tickets'


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'sender_info', 'message_preview', 'is_staff_reply', 'is_internal', 'created_at']
    list_filter = ['is_staff_reply', 'is_internal', 'created_at']
    search_fields = ['ticket__ticket_id', 'sender__phone_number', 'message']
    readonly_fields = ['ticket', 'sender', 'message', 'created_at', 'updated_at']
    raw_id_fields = ['ticket', 'sender']
    list_per_page = 40
    date_hierarchy = 'created_at'
    actions = ['export_messages_csv']
    
    def has_add_permission(self, request):
        return False
    
    def ticket_id(self, obj):
        return obj.ticket.ticket_id
    ticket_id.short_description = 'Ticket'
    ticket_id.admin_order_field = 'ticket__ticket_id'
    
    def sender_info(self, obj):
        if obj.is_staff_reply:
            return format_html(
                '<span style="color: #007bff; font-weight: bold;">👨‍💼 {}</span>',
                obj.sender.get_full_name()
            )
        return format_html(
            '<span style="color: #6c757d;">👤 {}</span>',
            obj.sender.phone_number
        )
    sender_info.short_description = 'Sender'
    
    def message_preview(self, obj):
        preview = obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
        if obj.is_internal:
            return format_html(
                '<span style="background: #fff3cd; padding: 2px 5px; border-radius: 3px;">🔒 {}</span>',
                preview
            )
        return preview
    message_preview.short_description = 'Message'
    
    def export_messages_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ticket_messages_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Ticket ID', 'Sender', 'Message', 'Is Staff', 'Is Internal', 'Created At'])
        
        for msg in queryset.select_related('ticket', 'sender'):
            writer.writerow([
                msg.ticket.ticket_id, msg.sender.phone_number, msg.message,
                'Yes' if msg.is_staff_reply else 'No',
                'Yes' if msg.is_internal else 'No',
                msg.created_at
            ])
        return response
    export_messages_csv.short_description = '📥 Export to CSV'


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'file_name', 'file_size_formatted', 'file_type', 'uploaded_by_info', 'uploaded_at']
    list_filter = ['uploaded_at', 'file_type']
    search_fields = ['ticket__ticket_id', 'file_name', 'uploaded_by__phone_number']
    readonly_fields = ['ticket', 'message', 'file', 'file_name', 'file_type', 'file_size_formatted', 'uploaded_by', 'uploaded_at']
    raw_id_fields = ['ticket', 'message', 'uploaded_by']
    list_per_page = 30
    date_hierarchy = 'uploaded_at'
    
    def has_add_permission(self, request):
        return False
    
    def ticket_id(self, obj):
        return obj.ticket.ticket_id
    ticket_id.short_description = 'Ticket'
    
    def uploaded_by_info(self, obj):
        return obj.uploaded_by.phone_number
    uploaded_by_info.short_description = 'Uploaded By'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'category', 'popularity_badge', 'is_published', 'sort_order']
    list_filter = ['category', 'is_published']
    search_fields = ['question', 'answer']
    list_editable = ['is_published', 'sort_order']
    list_per_page = 25
    actions = ['export_faqs_csv', 'publish_faqs', 'unpublish_faqs']
    
    fieldsets = (
        ('FAQ Content', {
            'fields': ('question', 'answer', 'category')
        }),
        ('Publishing', {
            'fields': ('is_published', 'sort_order')
        }),
        ('Statistics', {
            'fields': ('view_count', 'helpful_count', 'not_helpful_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ['view_count', 'helpful_count', 'not_helpful_count', 'created_at', 'updated_at']
    
    def question_preview(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_preview.short_description = 'Question'
    
    def popularity_badge(self, obj):
        views = obj.view_count
        helpful_ratio = (obj.helpful_count / max(obj.helpful_count + obj.not_helpful_count, 1)) * 100
        
        if views > 100:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 3px;">🔥 {} views | {}% helpful</span>',
                views, int(helpful_ratio)
            )
        elif views > 50:
            return format_html(
                '<span style="background: #ffc107; color: black; padding: 2px 8px; border-radius: 3px;">📊 {} views | {}% helpful</span>',
                views, int(helpful_ratio)
            )
        return format_html(
            '<span style="color: #6c757d;">{} views</span>',
            views
        )
    popularity_badge.short_description = 'Popularity'
    
    def export_faqs_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="faqs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Question', 'Answer', 'Category', 'Views', 'Helpful', 'Not Helpful', 'Is Published'])
        
        for faq in queryset.select_related('category'):
            writer.writerow([
                faq.question, faq.answer, faq.category.name,
                faq.view_count, faq.helpful_count, faq.not_helpful_count,
                'Yes' if faq.is_published else 'No'
            ])
        return response
    export_faqs_csv.short_description = '📥 Export to CSV'
    
    def publish_faqs(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} FAQ(s) published.')
    publish_faqs.short_description = '📢 Publish selected FAQs'
    
    def unpublish_faqs(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} FAQ(s) unpublished.')
    unpublish_faqs.short_description = '🔒 Unpublish selected FAQs'
