"""standalone_coord URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.urls import path, register_converter, include

import peering_coord.api as api
import peering_coord.api.info
import peering_coord.api.peering
import peering_coord.api.info_pb2_grpc
import peering_coord.api.peering_pb2_grpc
import peering_coord.views as views
from peering_coord.path_converters import AsnConverter


register_converter(AsnConverter, 'asn')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/login', views.LoginView.as_view(), name='login'),
    path('user/logout', views.LogoutView.as_view(), name='logout'),
    path('user/password_change', views.PasswordChangeView.as_view(), name='password_change'),
    path('', views.index, name='index'),
    path('vlan/<slug:name>', views.VlanView.as_view(), name='vlan'),
    path('owner/<slug:name>', views.OwnerView.as_view(), name='owner_details'),
    path('as/<asn:asn>', views.AsView.as_view(), name='as_details'),
    path('as/<asn:asn>/<slug:client>/secret', views.ClientSecretView.as_view(),
        name='client_secret'),
    path('as/<asn:asn>/<slug:client>/interface/<slug:vlan>/links', views.LinkDataView.as_view(),
        name='link_data')
]


def grpc_handlers(server):
    api.info_pb2_grpc.add_InfoServicer_to_server(
        api.info.InfoServive.as_servicer(), server)
    api.peering_pb2_grpc.add_PeeringServicer_to_server(
        api.peering.PeeringService.as_servicer(), server)
