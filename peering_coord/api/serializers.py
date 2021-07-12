"""Serializers for the gRPC APIs"""

from rest_framework import serializers
from django_grpc_framework import proto_serializers

from peering_coord.api import peering_pb2
from peering_coord.models.ixp import VLAN, Owner
from peering_coord.models.scion import AS, ISD
from peering_coord.models.policies import (
    AsPeerPolicy, DefaultPolicy, IsdPeerPolicy, OwnerPeerPolicy)
from peering_coord.scion_addr import ASN


class VlanRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(name=data)
        except VLAN.DoesNotExist:
            raise serializers.ValidationError("VLAN does not exist.")

    def get_queryset(self):
        return VLAN.objects.get_queryset()


class AsRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return str(value.asn)

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(asn=ASN(data))
        except ValueError:
            raise serializers.ValidationError("Invalid ASN.")
        except AS.DoesNotExist:
            raise serializers.ValidationError("AS does not exist.")

    def get_queryset(self):
        return AS.objects.get_queryset()


class OwnerRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(name=data)
        except Owner.DoesNotExist:
            raise serializers.ValidationError("Owner does not exist.")

    def get_queryset(self):
        return Owner.objects.get_queryset()


class IsdRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return str(value.isd_id)

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(isd_id=int(data))
        except ValueError:
            raise serializers.ValidationError("Invalid ISD.")
        except Owner.DoesNotExist:
            raise serializers.ValidationError("ISD does not exist.")

    def get_queryset(self):
        return ISD.objects.get_queryset()


class PolicyProtoSerializer(proto_serializers.ProtoSerializer):
    """Django REST/gRPC framework serializer for policies. Creates the correct policy ORM model
    depending on policy type in the protocol buffer representation.
    """
    class Meta:
        proto_class = peering_pb2.Policy

    vlan = VlanRelatedField()
    asn = AsRelatedField(source='asys')
    accept = serializers.BooleanField()

    peer_asn = AsRelatedField(source='peer_as', required=False)
    peer_owner = OwnerRelatedField(required=False)
    peer_isd = IsdRelatedField(required=False)

    def create(self, validated_data):
        if 'peer_as' in validated_data:
            return AsPeerPolicy.objects.create(**validated_data)
        elif 'peer_owner' in validated_data:
            return OwnerPeerPolicy.objects.create(**validated_data)
        elif 'peer_isd' in validated_data:
            return IsdPeerPolicy.objects.create(**validated_data)
        else:
            return DefaultPolicy.objects.create(**validated_data)

    def get(self):
        """Get an existing policy from the DB."""
        if 'peer_as' in self.validated_data:
            return AsPeerPolicy.objects.get(**self.validated_data)
        elif 'peer_owner' in self.validated_data:
            return OwnerPeerPolicy.objects.get(**self.validated_data)
        elif 'peer_isd' in self.validated_data:
            return IsdPeerPolicy.objects.get(**self.validated_data)
        else:
            return DefaultPolicy.objects.get(**self.validated_data)
