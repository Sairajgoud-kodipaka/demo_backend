from rest_framework import generics
from rest_framework.response import Response
from .models import AutomationWorkflow, AutomationExecution, ScheduledTask, TaskExecution
from .serializers import AutomationWorkflowSerializer, AutomationExecutionSerializer, ScheduledTaskSerializer, TaskExecutionSerializer

class AutomationWorkflowListView(generics.ListAPIView):
    queryset = AutomationWorkflow.objects.all()
    serializer_class = AutomationWorkflowSerializer

class AutomationWorkflowCreateView(generics.CreateAPIView):
    queryset = AutomationWorkflow.objects.all()
    serializer_class = AutomationWorkflowSerializer

class AutomationWorkflowDetailView(generics.RetrieveAPIView):
    queryset = AutomationWorkflow.objects.all()
    serializer_class = AutomationWorkflowSerializer

class AutomationWorkflowUpdateView(generics.UpdateAPIView):
    queryset = AutomationWorkflow.objects.all()
    serializer_class = AutomationWorkflowSerializer

class AutomationWorkflowDeleteView(generics.DestroyAPIView):
    queryset = AutomationWorkflow.objects.all()
    serializer_class = AutomationWorkflowSerializer

class AutomationWorkflowExecuteView(generics.GenericAPIView):
    def post(self, request, pk):
        return Response({"message": "Workflow execution endpoint"})

class AutomationExecutionListView(generics.ListAPIView):
    queryset = AutomationExecution.objects.all()
    serializer_class = AutomationExecutionSerializer

class AutomationExecutionDetailView(generics.RetrieveAPIView):
    queryset = AutomationExecution.objects.all()
    serializer_class = AutomationExecutionSerializer

class ScheduledTaskListView(generics.ListAPIView):
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer

class ScheduledTaskCreateView(generics.CreateAPIView):
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer

class ScheduledTaskDetailView(generics.RetrieveAPIView):
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer

class ScheduledTaskUpdateView(generics.UpdateAPIView):
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer

class ScheduledTaskDeleteView(generics.DestroyAPIView):
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer

class ScheduledTaskExecuteView(generics.GenericAPIView):
    def post(self, request, pk):
        return Response({"message": "Task execution endpoint"})

class TaskExecutionListView(generics.ListAPIView):
    queryset = TaskExecution.objects.all()
    serializer_class = TaskExecutionSerializer

class TaskExecutionDetailView(generics.RetrieveAPIView):
    queryset = TaskExecution.objects.all()
    serializer_class = TaskExecutionSerializer
