from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Sale, SaleItem, SalesPipeline
from .serializers import SaleSerializer, SaleItemSerializer, SalesPipelineSerializer
from apps.users.middleware import ScopedVisibilityMixin


class SaleListView(generics.ListAPIView, ScopedVisibilityMixin):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter sales by user scope and add search/filtering"""
        # Use scoped visibility middleware
        queryset = self.get_scoped_queryset(Sale)
        
        # Search by order number or client name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search)
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(
                created_at__date__range=[start_date, end_date]
            )
        
        return queryset.order_by('-created_at')


class SaleCreateView(generics.CreateAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Set tenant and generate order number"""
        serializer.save(
            tenant=self.request.user.tenant,
            sales_representative=self.request.user
        )


class SaleDetailView(generics.RetrieveAPIView, ScopedVisibilityMixin):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.get_scoped_queryset(Sale)


class SaleUpdateView(generics.UpdateAPIView, ScopedVisibilityMixin):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.get_scoped_queryset(Sale)


class SaleDeleteView(generics.DestroyAPIView, ScopedVisibilityMixin):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.get_scoped_queryset(Sale)


class SalesPipelineListView(generics.ListAPIView, ScopedVisibilityMixin):
    queryset = SalesPipeline.objects.all()
    serializer_class = SalesPipelineSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter pipelines by user scope and add search/filtering"""
        print("=== SalesPipelineListView.get_queryset called ===")
        print(f"User: {self.request.user.username}, Role: {getattr(self.request.user, 'role', 'No role')}")
        
        # Use scoped visibility middleware
        queryset = self.get_scoped_queryset(SalesPipeline)
        print(f"After scoped filtering: {queryset.count()} pipelines")
        
        # Search by title or client name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search)
            )
        
        # Filter by stage
        stage_filter = self.request.query_params.get('stage', None)
        if stage_filter:
            queryset = queryset.filter(stage=stage_filter)
        
        # Filter by sales rep
        rep_filter = self.request.query_params.get('sales_rep', None)
        if rep_filter:
            queryset = queryset.filter(sales_representative_id=rep_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(
                created_at__date__range=[start_date, end_date]
            )
        
        print(f"Final queryset count: {queryset.count()}")
        return queryset.order_by('-updated_at')


class MySalesPipelineListView(generics.ListAPIView):
    """Get pipelines assigned to the current user"""
    serializer_class = SalesPipelineSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter pipelines to only show those assigned to the current user"""
        print("=== MySalesPipelineListView.get_queryset called ===")
        print(f"User: {self.request.user.username}, Role: {getattr(self.request.user, 'role', 'No role')}")
        
        # Filter to only show pipelines assigned to the current user
        queryset = SalesPipeline.objects.filter(
            sales_representative=self.request.user,
            tenant=self.request.user.tenant
        )
        print(f"My pipelines count: {queryset.count()}")
        
        # Search by title or client name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search)
            )
        
        # Filter by stage
        stage_filter = self.request.query_params.get('stage', None)
        if stage_filter:
            queryset = queryset.filter(stage=stage_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(
                created_at__date__range=[start_date, end_date]
            )
        
        print(f"Final my pipelines count: {queryset.count()}")
        return queryset.order_by('-updated_at')


class MySalesPipelineDetailView(generics.RetrieveAPIView):
    """Get a specific pipeline assigned to the current user"""
    serializer_class = SalesPipelineSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter pipelines to only show those assigned to the current user"""
        print("=== MySalesPipelineDetailView.get_queryset called ===")
        print(f"User: {self.request.user.username}, Role: {getattr(self.request.user, 'role', 'No role')}")
        
        # Filter to only show pipelines assigned to the current user
        queryset = SalesPipeline.objects.filter(
            sales_representative=self.request.user,
            tenant=self.request.user.tenant
        )
        print(f"My pipeline detail count: {queryset.count()}")
        return queryset


class SalesPipelineCreateView(generics.CreateAPIView):
    queryset = SalesPipeline.objects.all()
    serializer_class = SalesPipelineSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Set tenant and sales representative"""
        try:
            print(f"Creating pipeline with data: {serializer.validated_data}")
            pipeline = serializer.save(
                tenant=self.request.user.tenant,
                sales_representative=self.request.user
            )
            print(f"Pipeline created successfully: {pipeline.id}")
        except Exception as e:
            print(f"Error creating pipeline: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


class SalesPipelineDetailView(generics.RetrieveAPIView, ScopedVisibilityMixin):
    queryset = SalesPipeline.objects.all()
    serializer_class = SalesPipelineSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.get_scoped_queryset(SalesPipeline)


class SalesPipelineUpdateView(generics.UpdateAPIView, ScopedVisibilityMixin):
    queryset = SalesPipeline.objects.all()
    serializer_class = SalesPipelineSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.get_scoped_queryset(SalesPipeline)


class SalesPipelineDeleteView(generics.DestroyAPIView, ScopedVisibilityMixin):
    queryset = SalesPipeline.objects.all()
    serializer_class = SalesPipelineSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.get_scoped_queryset(SalesPipeline)


class PipelineStageTransitionView(generics.GenericAPIView):
    """Move pipeline to next stage"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            pipeline = SalesPipeline.objects.get(
                pk=pk,
                tenant=request.user.tenant
            )
            
            new_stage = request.data.get('stage')
            if new_stage not in dict(SalesPipeline.Stage.choices):
                return Response(
                    {'error': 'Invalid stage'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Move to new stage
            pipeline.move_to_stage(new_stage)
            
            return Response({
                'message': f'Pipeline moved to {pipeline.get_stage_display()}',
                'pipeline': SalesPipelineSerializer(pipeline).data
            })
            
        except SalesPipeline.DoesNotExist:
            return Response(
                {'error': 'Pipeline not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PipelineStatsView(generics.GenericAPIView, ScopedVisibilityMixin):
    """Get pipeline statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            print(f"=== PipelineStatsView.get called ===")
            print(f"User: {request.user.username}, Role: {getattr(request.user, 'role', 'No role')}")
            print(f"Store: {getattr(request.user, 'store', 'No store')}")
            
            # Get scoped queryset for pipelines
            pipelines = self.get_scoped_queryset(SalesPipeline)
            print(f"Scoped pipelines count: {pipelines.count()}")
            
            # Calculate statistics
            active_pipelines = pipelines.exclude(
                stage__in=[SalesPipeline.Stage.CLOSED_WON, SalesPipeline.Stage.CLOSED_LOST]
            )
            
            total_value = active_pipelines.aggregate(
                total=Sum('expected_value')
            )['total'] or Decimal('0')
            
            active_deals = active_pipelines.count()
            total_deals = pipelines.count()
            won_deals = pipelines.filter(stage=SalesPipeline.Stage.CLOSED_WON).count()
            
            conversion_rate = (won_deals / total_deals * 100) if total_deals > 0 else 0
            avg_deal_size = (total_value / active_deals) if active_deals > 0 else 0
            
            print(f"Active deals: {active_deals}, Total deals: {total_deals}, Won deals: {won_deals}")
            
            return Response({
                'totalValue': float(total_value),
                'activeDeals': active_deals,
                'conversionRate': round(conversion_rate, 1),
                'avgDealSize': float(avg_deal_size),
            })
        except Exception as e:
            print(f"Error in PipelineStatsView: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PipelineStagesView(generics.GenericAPIView, ScopedVisibilityMixin):
    """Get pipeline stages with statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            print(f"=== PipelineStagesView.get called ===")
            print(f"User: {request.user.username}, Role: {getattr(request.user, 'role', 'No role')}")
            print(f"Store: {getattr(request.user, 'store', 'No store')}")
            
            # Get scoped queryset for pipelines
            pipelines_queryset = self.get_scoped_queryset(SalesPipeline)
            print(f"Scoped pipelines count: {pipelines_queryset.count()}")
            
            stages_data = []
            for stage_code, stage_name in SalesPipeline.Stage.choices:
                # Use scoped queryset for each stage
                stage_pipelines = pipelines_queryset.filter(stage=stage_code)
                
                count = stage_pipelines.count()
                value = stage_pipelines.aggregate(
                    total=Sum('expected_value')
                )['total'] or Decimal('0')
                
                stages_data.append({
                    'label': stage_name,
                    'value': float(value),
                    'count': count,
                    'color': self.get_stage_color(stage_code)
                })
            
            return Response(stages_data)
        except Exception as e:
            print(f"Error in PipelineStagesView: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_stage_color(self, stage_code):
        """Get color for each stage"""
        colors = {
            'lead': 'bg-gray-500',
            'contacted': 'bg-blue-500',
            'qualified': 'bg-yellow-500',
            'proposal': 'bg-orange-500',
            'negotiation': 'bg-purple-500',
            'closed_won': 'bg-green-500',
            'closed_lost': 'bg-red-500',
        }
        return colors.get(stage_code, 'bg-gray-400')


class SalesDashboardView(generics.GenericAPIView, ScopedVisibilityMixin):
    """Get sales dashboard data including sales and closed won pipeline revenue"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            print(f"=== SalesDashboardView.get called ===")
            print(f"User: {user.username}, Role: {user.role}")
            
            # Get date range for current month
            today = timezone.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            # Base filters for user scope
            base_sales_filter = {'tenant': user.tenant}
            base_pipeline_filter = {'tenant': user.tenant}
            
            # Apply role-based filtering
            if user.role in ['manager', 'inhouse_sales'] and hasattr(user, 'store') and user.store:
                base_sales_filter['client__store'] = user.store
                base_pipeline_filter['client__store'] = user.store
                print(f"Filtering by store: {user.store.name}")
            
            # Get sales data for current month
            monthly_sales = Sale.objects.filter(
                **base_sales_filter,
                created_at__gte=start_of_month,
                created_at__lte=end_of_month
            )
            
            # Get closed won pipeline data for current month
            # Include pipelines that are closed_won but don't have actual_close_date set
            monthly_closed_won = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).filter(
                Q(actual_close_date__gte=start_of_month, actual_close_date__lte=end_of_month) |
                Q(actual_close_date__isnull=True)  # Include pipelines without close date
            )
            
            # Calculate combined revenue
            sales_revenue = monthly_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            closed_won_revenue = monthly_closed_won.aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
            total_monthly_revenue = sales_revenue + closed_won_revenue
            
            # Get total deals (sales + closed won pipelines)
            total_deals = monthly_sales.count() + monthly_closed_won.count()
            
            # Sales count should include both actual sales and closed won pipelines
            sales_count = monthly_sales.count() + monthly_closed_won.count()
            
            # Get total customers (unique clients from sales and pipelines)
            from apps.clients.models import Client
            base_client_filter = {'tenant': user.tenant}
            if user.role in ['manager', 'inhouse_sales'] and hasattr(user, 'store') and user.store:
                base_client_filter['store'] = user.store
            
            total_customers = Client.objects.filter(**base_client_filter).count()
            
            # Calculate conversion rate (deals / customers)
            conversion_rate = (total_deals / total_customers * 100) if total_customers > 0 else 0
            
            print(f"DEBUG: Sales revenue: {sales_revenue}, Closed won revenue: {closed_won_revenue}")
            print(f"DEBUG: Total monthly revenue: {total_monthly_revenue}")
            print(f"DEBUG: Total deals: {total_deals}, Total customers: {total_customers}")
            
            dashboard_data = {
                'monthly_revenue': float(total_monthly_revenue),
                'total_deals': total_deals,
                'total_customers': total_customers,
                'conversion_rate': round(conversion_rate, 2),
                'sales_revenue': float(sales_revenue),
                'closed_won_revenue': float(closed_won_revenue),
                'sales_count': sales_count,  # Now includes closed won pipelines
                'closed_won_count': monthly_closed_won.count()
            }
            
            return Response({
                'success': True,
                'data': dashboard_data
            })
            
        except Exception as e:
            print(f"Error in SalesDashboardView: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to fetch dashboard data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PipelineDashboardView(generics.GenericAPIView, ScopedVisibilityMixin):
    """Get pipeline dashboard data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            print(f"=== PipelineDashboardView.get called ===")
            print(f"User: {request.user.username}, Role: {getattr(request.user, 'role', 'No role')}")
            print(f"Store: {getattr(request.user, 'store', 'No store')}")
            
            # Get scoped queryset for pipelines
            pipelines_queryset = self.get_scoped_queryset(SalesPipeline)
            print(f"Scoped pipelines count: {pipelines_queryset.count()}")
            
            # Pipeline summary by stage
            stage_summary = {}
            for stage_code, stage_name in SalesPipeline.Stage.choices:
                # Use scoped queryset for each stage
                stage_pipelines = pipelines_queryset.filter(stage=stage_code)
                
                count = stage_pipelines.count()
                value = stage_pipelines.aggregate(
                    total=Sum('expected_value')
                )['total'] or Decimal('0')
                
                stage_summary[stage_code] = {
                    'name': stage_name,
                    'count': count,
                    'value': float(value),
                    'percentage': 0  # Will be calculated below
                }
            
            # Calculate percentages
            total_pipelines = sum(stage['count'] for stage in stage_summary.values())
            if total_pipelines > 0:
                for stage in stage_summary.values():
                    stage['percentage'] = round((stage['count'] / total_pipelines) * 100, 1)
            
            # Recent activities - use scoped queryset
            recent_pipelines = pipelines_queryset.order_by('-updated_at')[:10]
            
            # Upcoming actions - filter out closed pipelines, use scoped queryset
            upcoming_actions = pipelines_queryset.filter(
                next_action_date__gte=timezone.now()
            ).exclude(
                stage__in=[SalesPipeline.Stage.CLOSED_WON, SalesPipeline.Stage.CLOSED_LOST]
            ).order_by('next_action_date')[:5]
            
            print(f"Recent pipelines count: {recent_pipelines.count()}")
            print(f"Upcoming actions count: {upcoming_actions.count()}")
            
            return Response({
                'stage_summary': stage_summary,
                'recent_pipelines': SalesPipelineSerializer(recent_pipelines, many=True).data,
                'upcoming_actions': SalesPipelineSerializer(upcoming_actions, many=True).data,
            })
        except Exception as e:
            print(f"Error in PipelineDashboardView: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SalesExportView(generics.GenericAPIView, ScopedVisibilityMixin):
    """Export sales data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Export sales data in various formats"""
        format_type = request.query_params.get('format', 'json')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Use scoped visibility instead of just tenant filtering
        queryset = self.get_scoped_queryset(Sale)
        
        # Apply date filters if provided
        if start_date and end_date:
            queryset = queryset.filter(
                created_at__date__range=[start_date, end_date]
            )
        
        if format_type == 'json':
            serializer = SaleSerializer(queryset, many=True)
            return Response(serializer.data)
        elif format_type == 'csv':
            # TODO: Implement CSV export
            return Response({'message': 'CSV export not implemented yet'})
        else:
            return Response(
                {'error': 'Unsupported format'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PipelineExportView(generics.GenericAPIView, ScopedVisibilityMixin):
    """Export pipeline data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Export pipeline data in various formats"""
        format_type = request.query_params.get('format', 'json')
        stage_filter = request.query_params.get('stage')
        
        # Use scoped visibility instead of just tenant filtering
        queryset = self.get_scoped_queryset(SalesPipeline)
        
        # Apply stage filter if provided
        if stage_filter:
            queryset = queryset.filter(stage=stage_filter)
        
        if format_type == 'json':
            serializer = SalesPipelineSerializer(queryset, many=True)
            return Response(serializer.data)
        elif format_type == 'csv':
            # TODO: Implement CSV export
            return Response({'message': 'CSV export not implemented yet'})
        else:
            return Response(
                {'error': 'Unsupported format'},
                status=status.HTTP_400_BAD_REQUEST
            )
