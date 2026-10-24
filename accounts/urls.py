from django.urls import path

from django.urls import path



from .utils import *
from .views import *





urlpatterns = [
    
    #web urls
    path("", landing_page, name="landing"),
    path("register/", register_page, name="register"),
    path("login/", login_page,name="login"),
   # path("dashboard/", dashboard_page, name="dashboard"),
    path("logout/",logout_page,name="logout"),
    path("otp/",otp,name="otp"),
    path("home", home, name="home"),
   # path('forgot-password/', forgot_password_otp_request, name='forgot_password_otp_request'),
    #path('forgot-password/verify/', forgot_password_otp_verify, name='forgot_password_otp_verify'),
    path('forgot-password/', forgot_password_email_request, name='forgot_password_email_request'),
    path('forgot-password/verify/', forgot_password_email_verify, name='forgot_password_email_verify'),
    
    



]
