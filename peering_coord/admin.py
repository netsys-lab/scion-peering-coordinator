from django.core.exceptions import ValidationError
from django.contrib import admin
from django import forms

from peering_coord.models import (
    Organization, ISD, AS, VLAN, VlanMembership, Link, AsPeerPolicy, IsdPeerPolicy, OrgPeerPolicy)
from peering_coord.peering_policy import update_accepted_peers


##########
### AS ###
##########

@admin.register(AS)
class AsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'isd', 'owner', 'is_core']
    list_filter = ['isd', 'owner', 'is_core']


############
### VLAN ###
############

@admin.register(VLAN)
class VlanAdmin(admin.ModelAdmin):
    fields = ['name', 'ip_network']
    list_display = ['name', 'ip_network']
    ordering = ['id']

    def get_readonly_fields(self, request, obj):
        if obj:
            return ('ip_network',) # read-only in change forms
        else:
            return ()


######################
### VlanMembership ###
######################

class VlanMembershipAdminForm(forms.ModelForm):
    class Meta:
        model = VlanMembership
        fields = ['vlan', 'asys', 'public_ip', 'first_br_port', 'last_br_port']

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
                except VLAN.AddressExhaustion:
                    raise ValidationError("VLAN IP addresses exhausted.",
                    code='addresses_exhausted')

        return cleaned_data


@admin.register(VlanMembership)
class IXPMemberAdmin(admin.ModelAdmin):
    form = VlanMembershipAdminForm
    list_display = ['vlan', 'asys', 'public_ip']
    ordering = ['vlan', 'asys']


############
### Link ###
############

@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ['vlan', 'link_type', 'as_a', 'br_port_a', 'as_b', 'br_port_b']
    list_filter = ['vlan', 'link_type']

    def has_add_permission(self, request):
        return False # cannot add link directly

    def has_change_permission(self, request, obj=None):
        return False # cannot change links directly

    def has_delete_premission(self, request, obj=None):
        return False # cannot delete links directly


################
### Policies ###
################

class PolicyAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        update_accepted_peers(obj.vlan, obj.asys)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        update_accepted_peers(obj.vlan, obj.asys)

    def delete_queryset(self, request, queryset):
        update = {(obj.vlan, obj.asys) for obj in queryset}
        super().delete_queryset(request, queryset)
        for vlan, asys in update:
            update_accepted_peers(vlan, asys)


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


@admin.register(OrgPeerPolicy)
class OrgPeerPolicyAdmin(PolicyAdmin):
    fields = ['vlan', 'asys', 'peer_org', 'accept']
    list_display = ['vlan', 'asys', 'peer_org', 'get_policy_type_str']
    ordering = ['vlan', 'asys', 'accept', 'peer_org']
    list_filter = ['vlan', 'asys']


##############
### Others ###
##############

admin.site.register([
    Organization,
    ISD
])
