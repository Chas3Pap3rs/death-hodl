from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from . import views
from .views import *


urlpatterns = [
    path("", views.home_view, name="home"),
    
    # user authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    
    path("signup/", views.signup_view, name="signup"),
    path('signup/<str:referral_code>/', views.signup_with_referrer_view, name='signup_with_referrer_view'),

    # wallet page
    path("portfolio/", views.portfolio_view, name="portfolio"),

    path('trade_in_points/', views.trade_in_points, name='trade_in_points'),

    # charts page
    path('charts/', crypto_chart, name='charts'),
    
    # CRUD operations on cryptos
    path("buy/", views.buy_view, name="buy"),
    path('sell/<int:pk>/', views.sell_view, name='sell'),
    path("add_to_portfolio/", views.add_to_portfolio_view, name="add_to_portfolio"),
    path('subtract_from_portfolio/<int:pk>/', views.subtract_from_portfolio_view, name='subtract_from_portfolio'),
    
    # password reset stuff
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name="reset/password_reset.html"), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name="reset/password_reset_done.html"), name='password_reset_done'),
    path('password_reset_confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
    template_name='reset/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(
    template_name='reset/password_reset_complete.html'), name='password_reset_complete'),

    # Reset portfolio
    path('reset_portfolio/', views.reset_portfolio_view, name='reset_portfolio'),

    # User delete
    path('delete_account/', delete_account_view, name='delete_account'),
]
