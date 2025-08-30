from django.contrib import admin

# Register your models here.
from .models import Order,OrderItem,OrderStatusHistory,Payment,OrderStatus

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('dish','dish_name','unit_price','quantity','line_total')
    
class OrderStatusInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "message", "created_at")
    

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id','user','status','total_amount','created_at','paid_at',"table_no")
    list_filter = ('status',"service_type")
    search_fields = ("id","user__username","contact_phone","address_line")
    inlines = [OrderItemInline,OrderStatusInline]
    readonly_fields = ('total_amount','created_at','paid_at','updated_at')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id","order","method","amount","paid_at","created_at")
    search_fields= ("order__id","trade_no")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id','order','dish_name','unit_price','quantity','line_total')
    
@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('id','order','from_status','to_status','message','created_at')


