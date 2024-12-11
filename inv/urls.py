from django.urls import path
from .views import MovementListView, MovementCreateView, MovementUpdateView, MovementDeleteView

urlpatterns = [
   
    path('movements/', MovementListView.as_view(), name='movement_list'),
    path('movements/create/', MovementCreateView.as_view(), name='movement_create'),
    path('movements/update/<int:pk>/', MovementUpdateView.as_view(), name='movement_update'),
    path('movements/delete/<int:pk>/', MovementDeleteView.as_view(), name='movement_delete'),

]
