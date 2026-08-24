"""
URL configuration for Marimo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from django.conf.urls.i18n import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path('rosetta/', include('rosetta.urls')),
    path('__debug__/', include('debug_toolbar.urls')),
    path('i18n/setlang/', set_language, name='set_language'),
]

urlpatterns += i18n_patterns(
    path(_('scheduling/'), include('scheduling.urls', namespace='scheduling')),
    path('', include('django.contrib.auth.urls')),
    path('', include('accounts.urls', namespace='accounts')),
)
