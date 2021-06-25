from django.urls import path

from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('buxfer-table', views.BuxferTransactionTableView.as_view(), name='buxfer_table'),
]