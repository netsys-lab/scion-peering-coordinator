"""Database models of the perring policies"""

from django.db import models
from django.core.exceptions import ValidationError

from peering_coord.models.ixp import Owner, VLAN, Interface
from peering_coord.models.scion import AS, ISD


class PeeringPolicy(models.Model):
    """Abstract base class for accept/reject peering policies."""
    vlan = models.ForeignKey(
        VLAN,
        verbose_name="VLAN",
        help_text="VLAN the policy is applied to.",
        on_delete=models.CASCADE
    )
    asys = models.ForeignKey(
        AS,
        verbose_name="AS",
        help_text="Owner of the policy.",
        on_delete=models.CASCADE
    )
    accept = models.BooleanField(
        help_text="Whether this rule accepts peering connection or filters them out.",
        default=True
    )

    class Meta:
        abstract = True

    def save(self, **kwargs):
        self.full_clean()
        super().save(**kwargs)

    def clean(self):
        try:
            # Make sure the AS is actually connected to the VLAN.
            if not self.asys.is_connected_to_vlan(self.vlan):
                raise ValidationError("%(asys)s is not a member of %(vlan)s.",
                    code='not_a_vlan_member',
                    params={'asys': self.asys, 'vlan': self.vlan})
        except (VLAN.DoesNotExist, AS.DoesNotExist):
            pass # vlan or asys are empty, will be caught during form validation.

    def get_policy_type_str(self) -> str:
        """String representation of the policy type (accept/reject) for the admin interface."""
        if self.accept:
            return "Accept"
        else:
            return "Reject"
    get_policy_type_str.admin_order_field = 'accept'
    get_policy_type_str.short_description = "Type"


class DefaultPolicy(PeeringPolicy):
    """Whether to accept peering with another AS in abscense of any other applicable rules.
    If no default peering policy is set, the default is to reject peering.
    """

    class Meta:
        verbose_name = 'Default Policy'
        verbose_name_plural = 'Default Policies'
        constraints = [
            models.UniqueConstraint(fields=['vlan', 'asys'], name="unique_default_policy")
        ]

    def __str__(self):
        return "Default policy for %s (%s)" % (self.asys, self.vlan)


class AsPeerPolicy(PeeringPolicy):
    """AS accept/reject policy."""
    peer_as = models.ForeignKey(
        AS,
        verbose_name="Peer AS",
        related_name="+",
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'AS Peering Policy'
        verbose_name_plural = 'AS Peering Policies'
        constraints = [
            models.UniqueConstraint(fields=['vlan', 'asys', 'peer_as'], name="unique_as_policy")
        ]

    def clean(self):
        super().clean()
        try:
            if self.asys == self.peer_as:
                raise ValidationError("AS and peer AS are identical.", code='peer_with_self')
        except AS.DoesNotExist:
            pass # asys or peer_as are empty, will be caught during form validation.

    def __str__(self):
        if self.accept:
            return "Accept %s -> %s (%s)" % (self.asys, self.peer_as, self.vlan)
        else:
            return "Reject %s -> %s (%s)" % (self.asys, self.peer_as, self.vlan)


class IsdPeerPolicy(PeeringPolicy):
    """ISD accept/accept policy."""
    peer_isd = models.ForeignKey(
        ISD,
        verbose_name="Peer ISD",
        related_name="+",
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'ISD Peering Policy'
        verbose_name_plural = 'ISD Peering Policies'
        constraints = [
            models.UniqueConstraint(fields=['vlan', 'asys', 'peer_isd'], name="unique_isd_policy")
        ]

    def __str__(self):
        if self.accept:
            return "Accept %s -> %s (%s)" % (self.asys, self.peer_isd, self.vlan)
        else:
            return "Reject %s -> %s (%s)" % (self.asys, self.peer_isd, self.vlan)


class OwnerPeerPolicy(PeeringPolicy):
    """Owner accept/reject policy."""
    peer_owner = models.ForeignKey(
        Owner,
        verbose_name="Peer Owner",
        related_name="+",
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Owner Peering Policy'
        verbose_name_plural = 'Owner Peering Policies'
        constraints = [
            models.UniqueConstraint(
                fields=['vlan', 'asys', 'peer_owner'], name="unique_org_policy")
        ]

    def __str__(self):
        if self.accept:
            return "Accept %s -> %s (%s)" % (self.asys, self.peer_owner, self.vlan)
        else:
            return "Reject %s -> %s (%s)" % (self.asys, self.peer_owner, self.vlan)
