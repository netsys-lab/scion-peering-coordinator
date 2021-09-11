"""Serializers for table data in the AS detail views"""

from rest_framework import serializers

from peering_coord.models.ixp import Link, Interface, PeeringClient
from peering_coord.api.serializers import AsRelatedField, VlanRelatedField


class PeeringClientSerializer(serializers.ModelSerializer):
    asys = AsRelatedField()

    class Meta:
        model = PeeringClient
        fields = ['asys', 'name']


class InterfaceSerializer(serializers.ModelSerializer):
    peering_client = PeeringClientSerializer()
    vlan = VlanRelatedField()

    class Meta:
        model = Interface
        fields = ['peering_client', 'vlan']


class LinkTypeField(serializers.Field):
    def to_representation(self, value):
        try:
            return Link.Type(value).name
        except ValueError:
            raise serializers.ValidationError("Invalid link type.")

    def to_internal_value(self, data):
        try:
            return Link.Type[data]
        except KeyError:
            raise serializers.ValidationError("Invalid link type.")


class LinkSerializer(serializers.ModelSerializer):
    link_type = LinkTypeField()
    interface_a = InterfaceSerializer()
    interface_b = InterfaceSerializer()

    class Meta:
        model = Link
        fields = ['link_type', 'interface_a', 'port_a', 'interface_b', 'port_b']
