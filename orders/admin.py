from django.contrib import admin
from orders.models import Order, ItemOrder


class ItemOrderInline(admin.TabularInline):
    model = ItemOrder
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'phone_number', 'pickup_datetime', 'subtotal', 'status']
    list_filter = ['status', 'store_id', 'pickup_datetime']
    search_fields = ['customer_name', 'phone_number', 'email']
    readonly_fields = ['subtotal', 'created_at', 'updated_at']
    inlines = [ItemOrderInline]
    date_hierarchy = 'pickup_datetime'


@admin.register(ItemOrder)
class ItemOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'item', 'quantity', 'line_total', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['line_total', 'created_at', 'updated_at']
    search_fields = ['order__customer_name', 'item__name']
