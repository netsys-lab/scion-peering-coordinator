from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from peering_coord import policy_resolver
from peering_coord.models.ixp import VLAN, Interface, Owner, PeeringClient
from peering_coord.models.policies import (
    AsPeerPolicy, DefaultPolicy, IsdPeerPolicy, OwnerPeerPolicy)
from peering_coord.models.scion import AS, ISD, VLAN, Link


################
## IXP Models ##
################

@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    fields = ['name', 'long_name', 'contact', 'users']
    list_display = ['long_name', 'name', 'fmt_as_list']


@admin.register(PeeringClient)
class PeeringClientAdmin(admin.ModelAdmin):
    list_display = ['asys', 'name', 'fmt_vlan_list']
    list_filter = ['asys']
    ordering = ['asys', 'name']
    readonly_fields = ['secret_token']


class PeeringClientInline(admin.TabularInline):
    model = PeeringClient
    fields = ['name']
    extra = 1


@admin.register(VLAN)
class VlanAdmin(admin.ModelAdmin):
    fields = ['name', 'long_name', 'ip_network']
    list_display = ['long_name', 'name', 'ip_network']
    ordering = ['long_name', 'name']

    def get_readonly_fields(self, request, obj):
        if obj:
            return ('ip_network',) # read-only in change forms
        else:
            return ()


class InterfaceAdminForm(forms.ModelForm):
    class Meta:
        model = Interface
        fields = ['peering_client', 'vlan', 'public_ip', 'first_port', 'last_port']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['public_ip'].required = False # allow an empty input string for 'public_ip'

    def clean_public_ip(self):
        public_ip = self.cleaned_data['public_ip']
        if len(public_ip) == 0:
            public_ip = None # assign IP in self.clean()
        return public_ip

    def clean(self):
        cleaned_data = super().clean()

        # Automatically assign an IP address if the 'public_ip' field was empty.
        if 'public_ip' in cleaned_data and cleaned_data['public_ip'] is None:
            if 'vlan' in cleaned_data:
                try:
                    cleaned_data['public_ip'] = cleaned_data['vlan'].get_unused_ip()
                except VLAN.NoUnusedIps:
                    raise ValidationError("VLAN IP addresses exhausted.",
                    code='addresses_exhausted')

        return cleaned_data


def update_links(modeladmin, request, queryset):
    for iface in queryset.all():
        policy_resolver.update_links(iface.vlan, iface.peering_client.asys)


@admin.register(Interface)
class InterfaceAdmin(admin.ModelAdmin):
    form = InterfaceAdminForm
    list_display = ['peering_client', 'vlan', 'public_ip', 'first_port', 'last_port']
    list_filter = ['vlan']
    ordering = ['peering_client', 'vlan']
    actions = [update_links]


##################
## SCION Models ##
##################

admin.site.register(ISD)


@admin.register(AS)
class AsAdmin(admin.ModelAdmin):
    list_display = ['name', 'asn', 'isd', 'owner', 'fmt_vlan_list', 'is_core']
    list_filter = ['isd', 'owner', 'is_core']
    inlines = [PeeringClientInline]


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ['link_type', 'interface_a', 'port_a', 'interface_b', 'port_b']
    list_filter = ['link_type']

    def has_add_permission(self, request):
        return False # cannot add link directly

    def has_change_permission(self, request, obj=None):
        return False # cannot change links directly

    def has_delete_premission(self, request, obj=None):
        return False # cannot delete links directly


###################
## Policy Models ##
###################

class PolicyAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        policy_resolver.update_accepted_peers(obj.vlan, obj.asys)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        policy_resolver.update_accepted_peers(obj.vlan, obj.asys)

    def delete_queryset(self, request, queryset):
        update = {(obj.vlan, obj.asys) for obj in queryset}
        super().delete_queryset(request, queryset)
        for vlan, asys in update:
            policy_resolver.update_accepted_peers(vlan, asys)


@admin.register(DefaultPolicy)
class DefaultPolicyAdmin(admin.ModelAdmin):
    fields = ['vlan', 'asys', 'accept']
    list_display = ['vlan', 'asys', 'accept']
    list_filter = ['vlan', 'asys', 'accept']


@admin.register(AsPeerPolicy)
class AsPeerPolicyAdmin(PolicyAdmin):
    fields = ['vlan', 'asys', 'peer_as', 'accept']
    list_display = ['vlan', 'asys', 'peer_as', 'get_policy_type_str']
    ordering = ['vlan', 'asys', 'accept', 'peer_as']
    list_filter = ['vlan', 'asys']


@admin.register(IsdPeerPolicy)
class IsdPeerPolicyAdmin(PolicyAdmin):
    fields = ['vlan', 'asys', 'peer_isd', 'accept']
    list_display = ['vlan', 'asys', 'peer_isd', 'get_policy_type_str']
    ordering = ['vlan', 'asys', 'accept', 'peer_isd']
    list_filter = ['vlan', 'asys']


@admin.register(OwnerPeerPolicy)
class OwnerPeerPolicyAdmin(PolicyAdmin):
    fields = ['vlan', 'asys', 'peer_owner', 'accept']
    list_display = ['vlan', 'asys', 'peer_owner', 'get_policy_type_str']
    ordering = ['vlan', 'asys', 'accept', 'peer_owner']
    list_filter = ['vlan', 'asys']
