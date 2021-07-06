from django.urls import path

from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('bank-table', views.BankTransactionTableView.as_view(), name='bank_table'),
    path('bank-table/unmachted', views.BankTransactionsNotUploadedTableView.as_view(), name='bank_table_unmatchted'),
    path('bank-detail/<int:pk>', views.BankTransactionDetailView.as_view(), name='bank_detail'),
    path('buxfer-table', views.BuxferTransactionTableView.as_view(), name='buxfer_table'),
    path('buxfer-table/unmachted', views.BuxferUnmatchedTransactionTableView.as_view(), name='buxfer_table_unmatchted'),
    path('buxfer-load', views.BuxferLoadDataView.as_view(), name='buxfer_load'),
    path('bank-load', views.BankLoadDataView.as_view(), name='bank_load'),
    path('buxfer-send-single', views.SendSingleTransactionToBuxferView.as_view(), name='buxfer_send_single'),
    path('buxfer-detail/<int:pk>', views.BuxferTransactionDetailView.as_view(), name='buxfer_detail'),
    path('upload-auto-tagging-strings', views.UploadAutoTaggingStringsView.as_view(), name="upload_auto_tagging_string"),
    path('match-transactions', views.MatchTransactionsView.as_view(), name="match_transactions"),
]
