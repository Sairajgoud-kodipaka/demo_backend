from django.db import models
from django.utils.translation import gettext_lazy as _


class AnalyticsEvent(models.Model):
    """
    Model for tracking analytics events.
    """
    class EventType(models.TextChoices):
        PAGE_VIEW = 'page_view', _('Page View')
        CLICK = 'click', _('Click')
        FORM_SUBMIT = 'form_submit', _('Form Submit')
        PURCHASE = 'purchase', _('Purchase')
        SIGNUP = 'signup', _('Sign Up')
        LOGIN = 'login', _('Login')
        CUSTOM = 'custom', _('Custom Event')

    # Event Information
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    event_name = models.CharField(max_length=100)
    event_data = models.JSONField(default=dict, blank=True)
    
    # User and Session Information
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events'
    )
    session_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Page and Referrer Information
    page_url = models.URLField(blank=True, null=True)
    page_title = models.CharField(max_length=200, blank=True, null=True)
    referrer_url = models.URLField(blank=True, null=True)
    
    # Device and Browser Information
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='analytics_events'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Analytics Event')
        verbose_name_plural = _('Analytics Events')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.event_name} - {self.created_at}"


class BusinessMetrics(models.Model):
    """
    Model for storing calculated business metrics.
    """
    class MetricType(models.TextChoices):
        SALES = 'sales', _('Sales')
        REVENUE = 'revenue', _('Revenue')
        CUSTOMERS = 'customers', _('Customers')
        PRODUCTS = 'products', _('Products')
        CONVERSION = 'conversion', _('Conversion Rate')
        RETENTION = 'retention', _('Customer Retention')

    # Metric Information
    metric_type = models.CharField(max_length=20, choices=MetricType.choices)
    metric_name = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Time Period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('monthly', _('Monthly')),
            ('quarterly', _('Quarterly')),
            ('yearly', _('Yearly')),
        ]
    )
    
    # Comparison
    previous_value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    change_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Additional Data
    metadata = models.JSONField(default=dict, blank=True)
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='business_metrics'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Business Metric')
        verbose_name_plural = _('Business Metrics')
        ordering = ['-period_end']
        unique_together = ['metric_type', 'metric_name', 'period_start', 'period_end', 'tenant']

    def __str__(self):
        return f"{self.metric_name} - {self.period_start.date()} to {self.period_end.date()}"


class DashboardWidget(models.Model):
    """
    Model for storing dashboard widget configurations.
    """
    class WidgetType(models.TextChoices):
        CHART = 'chart', _('Chart')
        METRIC = 'metric', _('Metric')
        TABLE = 'table', _('Table')
        LIST = 'list', _('List')

    class ChartType(models.TextChoices):
        LINE = 'line', _('Line Chart')
        BAR = 'bar', _('Bar Chart')
        PIE = 'pie', _('Pie Chart')
        DONUT = 'donut', _('Donut Chart')
        AREA = 'area', _('Area Chart')

    # Widget Information
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WidgetType.choices)
    chart_type = models.CharField(
        max_length=20,
        choices=ChartType.choices,
        blank=True,
        null=True
    )
    
    # Configuration
    config = models.JSONField(default=dict, blank=True)
    position = models.JSONField(default=dict, blank=True)  # x, y, width, height
    is_visible = models.BooleanField(default=True)
    
    # Data Source
    data_source = models.CharField(max_length=100, blank=True, null=True)
    refresh_interval = models.PositiveIntegerField(default=300, help_text=_('Refresh interval in seconds'))
    
    # User and Tenant
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='dashboard_widgets'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='dashboard_widgets'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Dashboard Widget')
        verbose_name_plural = _('Dashboard Widgets')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.get_widget_type_display()}"


class Report(models.Model):
    """
    Model for storing generated reports.
    """
    class ReportType(models.TextChoices):
        SALES_REPORT = 'sales_report', _('Sales Report')
        CUSTOMER_REPORT = 'customer_report', _('Customer Report')
        PRODUCT_REPORT = 'product_report', _('Product Report')
        FINANCIAL_REPORT = 'financial_report', _('Financial Report')
        CUSTOM = 'custom', _('Custom Report')

    class Format(models.TextChoices):
        PDF = 'pdf', _('PDF')
        EXCEL = 'excel', _('Excel')
        CSV = 'csv', _('CSV')
        JSON = 'json', _('JSON')

    # Report Information
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    format = models.CharField(max_length=10, choices=Format.choices, default=Format.PDF)
    
    # Configuration
    parameters = models.JSONField(default=dict, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    
    # File Storage
    file_path = models.CharField(max_length=500, blank=True, null=True)
    file_size = models.PositiveIntegerField(blank=True, null=True)
    
    # Status
    is_generated = models.BooleanField(default=False)
    generation_started = models.DateTimeField(blank=True, null=True)
    generation_completed = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # User and Tenant
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reports'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='reports'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_report_type_display()}"
