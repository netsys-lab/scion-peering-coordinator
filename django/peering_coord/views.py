from peering_coord.models.policies import AsPeerPolicy, DefaultPolicy
from django.contrib.auth import views as auth_views
from django.http.response import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, DetailView
from django.views.decorators.http import require_safe
from django.core.exceptions import PermissionDenied

from django.conf import settings
from django.http import Http404
from django.db.models import Count, Q

from rest_framework import generics

from peering_coord.models.ixp import VLAN, PeeringClient, Interface, Link, Owner
from peering_coord.models.scion import AS
from peering_coord.models.policies import DefaultPolicy, AsPeerPolicy, OwnerPeerPolicy, IsdPeerPolicy
from peering_coord.scion_addr import ASN
from peering_coord.serializers import LinkSerializer


################
## Index View ##
################

@require_safe
def index(request):
    vlans = VLAN.objects.all()

    context = {
        'title': settings.INSTANCE_NAME,
        'description': settings.INSTANCE_DESCRIPTION,
        'vlans': VLAN.objects.all()
    }

    if request.user.is_authenticated:
        ases = AS.objects.filter(owner__in=request.user.owner_set.all())

        peer_count = {}
        for asys in ases:
            peers = []
            for vlan in vlans:
                peers.append(asys.query_connected_peers(vlan=vlan).count())
            peer_count[asys.id] = peers

        context['ases'] = ases
        context['peer_count'] = peer_count

    return render(request, "peering_coord/index.html", context)


##############################
## Account Management Views ##
##############################

class LoginView(auth_views.LoginView):
    test = auth_views.PasswordChangeView
    extra_context = {'title': settings.INSTANCE_NAME}


class LogoutView(auth_views.LogoutView):
    next_page = "/"


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "registration/password_change.html"
    success_url = "/"
    extra_context = {'title': settings.INSTANCE_NAME}


###############
## VLAN View ##
###############

SORT_BY_KEY = "sort"
ORDER_KEY = "order"
ORDER_ASC = "asc"
ORDER_DESC = "dsc"
VLAN_KEY = "vlan"


def validate_sort_order(order: str):
    if order not in [ORDER_ASC, ORDER_DESC]:
        raise Http404()


class VlanView(ListView):
    model = AS
    template_name = "peering_coord/vlan.html"
    context_object_name = "ases"

    def get_queryset(self):
        # Filter for VLAN
        self.vlan = get_object_or_404(VLAN, name=self.kwargs['name'])
        ases = self.vlan.members.values_list('asys', flat=True).all()
        queryset = AS.objects.filter(id__in=ases)

        # Filter according to query string
        self.query = self.request.GET.get("query")
        if self.query:
            if self.query.startswith("AS"):
                try:
                    queryset = queryset.filter(asn=ASN(self.query[2:]))
                except ValueError:
                    queryset = AS.objects.none()
            else:
                queryset = queryset.filter(
                    Q(name__icontains=self.query) | Q(owner__long_name__icontains=self.query))

        # Ordering
        self.sort_order = self.request.GET.get(ORDER_KEY, ORDER_ASC)
        validate_sort_order(self.sort_order)

        self.order_by = self.request.GET.get(SORT_BY_KEY)
        if self.order_by in ["name", "asn", "owner"]:
            queryset = queryset.order_by(self.order_by)
        elif self.order_by == "isd":
            queryset = queryset.order_by("isd__isd_id")
        elif self.order_by == "links":
            queryset = queryset.annotate(link_count=Count('links'))
        elif self.order_by:
            raise Http404()

        if self.sort_order == ORDER_DESC:
            queryset = queryset.reverse()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = settings.INSTANCE_NAME
        context['sort'] = {
            'by': self.order_by,
            'order': self.sort_order,
            'reverse_order': ORDER_DESC if self.sort_order == ORDER_ASC else ORDER_ASC
        }
        context['vlan'] = self.vlan
        context['query'] = self.query
        return context


################
## Owner View ##
################

class OwnerView(DetailView):
    model = Owner
    template_name = "peering_coord/owner.html"
    context_object_name = "owner"

    def get_object(self):
        return get_object_or_404(self.model, name=self.kwargs['name'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = settings.INSTANCE_NAME
        return context


#############
## AS View ##
#############

class AsView(DetailView):
    model = AS
    template_name = "peering_coord/as.html"
    context_object_name = "asys"

    def get_object(self):
        return get_object_or_404(self.model, asn=self.kwargs['asn'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = settings.INSTANCE_NAME

        interfaces = self.object.query_interfaces().order_by('peering_client', 'vlan').all()
        context['interfaces'] = interfaces

        if (self.request.user.is_superuser or
            self.object.owner.users.filter(id=self.request.user.id).exists()):
            default_policies = DefaultPolicy.objects.filter(
                asys=self.object).order_by('vlan', 'accept').all()
            context['default_policies'] = default_policies
            isd_policies = IsdPeerPolicy.objects.filter(
                asys=self.object).order_by('vlan', 'accept').all()
            context['isd_policies'] = isd_policies
            owner_policies = OwnerPeerPolicy.objects.filter(
                asys=self.object).order_by('vlan', 'accept').all()
            context['owner_policies'] = owner_policies
            as_policies = AsPeerPolicy.objects.filter(
                asys=self.object).order_by('vlan', 'accept').all()
            context['as_policies'] = as_policies

        return context


######################
## Data for AS View ##
######################

class ClientSecretView(View):
    def get(self, request, *args, **kwargs):
        try:
            asys = AS.objects.get(asn=kwargs['asn'])
            pc = asys.peering_clients.get(name=kwargs['client'])
        except (AS.DoesNotExist, PeeringClient.DoesNotExist):
            raise PermissionDenied
        if self.check_permission(request.user, asys):
            return HttpResponse(pc.secret_token)
        else:
            raise PermissionDenied

    def post(self, request, *args, **kwargs):
        try:
            asys = AS.objects.get(asn=kwargs['asn'])
            pc = asys.peering_clients.get(name=kwargs['client'])
        except (AS.DoesNotExist, PeeringClient.DoesNotExist):
            raise PermissionDenied
        if self.check_permission(request.user, asys):
            pc.secret_token = PeeringClient.gen_secret_token()
            pc.save()
            return HttpResponse(pc.secret_token)
        else:
            raise PermissionDenied

    def check_permission(self, user, asys):
        return user.is_superuser or asys.owner.users.filter(id=user.id).exists()


class LinkDataView(generics.ListAPIView):
    serializer_class = LinkSerializer

    def get_queryset(self):
        interfaces = Interface.objects.filter(
            peering_client__asys__asn=self.kwargs['asn'],
            peering_client__name=self.kwargs['client'],
            vlan__name=self.kwargs['vlan'])

        if not interfaces:
            raise Http404()

        return Link.objects.filter(Q(interface_a__in=interfaces) | Q(interface_b__in=interfaces))
