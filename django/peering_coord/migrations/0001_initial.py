# Generated by Django 3.2.7 on 2021-09-11 12:19

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.expressions
import peering_coord.custom_fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AcceptedPeer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='AS',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asn', peering_coord.custom_fields.AsnField(help_text='AS number', unique=True, verbose_name='ASN')),
                ('name', models.CharField(max_length=256)),
                ('is_core', models.BooleanField(help_text='Whether the AS is port of the ISD core.', verbose_name='Is Core AS')),
                ('accept', models.ManyToManyField(through='peering_coord.AcceptedPeer', to='peering_coord.AS')),
            ],
            options={
                'verbose_name': 'AS',
                'verbose_name_plural': 'ASes',
            },
        ),
        migrations.CreateModel(
            name='Interface',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_ip', peering_coord.custom_fields.IpAddressField(verbose_name='IP Address')),
                ('first_port', peering_coord.custom_fields.L4PortField(default=0, help_text='First UDP port to assign to SCION links.', verbose_name='First BR Port')),
                ('last_port', peering_coord.custom_fields.L4PortField(default=0, help_text='One past the last UDP port to assign to SCION links.', verbose_name='Last BR Port')),
            ],
        ),
        migrations.CreateModel(
            name='ISD',
            fields=[
                ('isd_id', models.PositiveIntegerField(help_text='Integer identifying the ISD.', primary_key=True, serialize=False, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)], verbose_name='ID')),
                ('name', models.CharField(help_text='A human-readable name for the ISD.', max_length=256)),
            ],
            options={
                'verbose_name': 'ISD',
                'verbose_name_plural': 'ISDs',
            },
        ),
        migrations.CreateModel(
            name='Owner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.SlugField(help_text='Uniquely identifies the owner in the API.', max_length=32, unique=True, verbose_name='Identifier')),
                ('long_name', models.CharField(help_text='Full name of the owner.', max_length=256, verbose_name='Name')),
                ('contact', models.TextField(blank=True, help_text='Contact information for administrative purposes.', null=True)),
                ('users', models.ManyToManyField(help_text='User accounts with access to this entities ASes.', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PeeringClient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.SlugField(default='default', help_text='A per-AS unique identifier for the border router.')),
                ('secret_token', models.CharField(blank=True, help_text='Secrect API authentication token.', max_length=32, verbose_name='API Token')),
                ('asys', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='peering_clients', to='peering_coord.as', verbose_name='AS')),
            ],
            options={
                'verbose_name': 'Peering Client',
                'verbose_name_plural': 'Peering Clients',
            },
        ),
        migrations.CreateModel(
            name='VLAN',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.SlugField(help_text='Uniquely identifies the VLAN.', max_length=32, unique=True, verbose_name='Identifier')),
                ('long_name', models.CharField(help_text='Verbose name.', max_length=256, verbose_name='Name')),
                ('ip_network', peering_coord.custom_fields.IpNetworkField(help_text='IP subnet used by the SCION underlay.', verbose_name='IP Network')),
                ('members', models.ManyToManyField(related_name='vlans', through='peering_coord.Interface', to='peering_coord.PeeringClient')),
            ],
            options={
                'verbose_name': 'VLAN',
                'verbose_name_plural': 'VLANs',
            },
        ),
        migrations.CreateModel(
            name='OwnerPeerPolicy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accept', models.BooleanField(default=True, help_text='Whether this rule accepts peering connection or filters them out.')),
                ('asys', models.ForeignKey(help_text='Owner of the policy.', on_delete=django.db.models.deletion.CASCADE, to='peering_coord.as', verbose_name='AS')),
                ('peer_owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='peering_coord.owner', verbose_name='Peer Owner')),
                ('vlan', models.ForeignKey(help_text='VLAN the policy is applied to.', on_delete=django.db.models.deletion.CASCADE, to='peering_coord.vlan', verbose_name='VLAN')),
            ],
            options={
                'verbose_name': 'Owner Peering Policy',
                'verbose_name_plural': 'Owner Peering Policies',
            },
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link_type', models.SmallIntegerField(choices=[(0, 'Core Link'), (1, 'Peering Link'), (2, 'Provider to Customer Link')], help_text='Type of the link in SCION.', verbose_name='Type')),
                ('port_a', peering_coord.custom_fields.L4PortField(verbose_name='UDP Port A')),
                ('port_b', peering_coord.custom_fields.L4PortField(verbose_name='UDP Port B')),
                ('interface_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='peering_coord.interface', verbose_name='Interface A')),
                ('interface_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='peering_coord.interface', verbose_name='Interface B')),
            ],
        ),
        migrations.CreateModel(
            name='IsdPeerPolicy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accept', models.BooleanField(default=True, help_text='Whether this rule accepts peering connection or filters them out.')),
                ('asys', models.ForeignKey(help_text='Owner of the policy.', on_delete=django.db.models.deletion.CASCADE, to='peering_coord.as', verbose_name='AS')),
                ('peer_isd', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='peering_coord.isd', verbose_name='Peer ISD')),
                ('vlan', models.ForeignKey(help_text='VLAN the policy is applied to.', on_delete=django.db.models.deletion.CASCADE, to='peering_coord.vlan', verbose_name='VLAN')),
            ],
            options={
                'verbose_name': 'ISD Peering Policy',
                'verbose_name_plural': 'ISD Peering Policies',
            },
        ),
        migrations.AddField(
            model_name='interface',
            name='links',
            field=models.ManyToManyField(related_name='_peering_coord_interface_links_+', through='peering_coord.Link', to='peering_coord.Interface'),
        ),
        migrations.AddField(
            model_name='interface',
            name='peering_client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interfaces', to='peering_coord.peeringclient', verbose_name='Peering Client'),
        ),
        migrations.AddField(
            model_name='interface',
            name='vlan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interfaces', to='peering_coord.vlan', verbose_name='VLAN'),
        ),
        migrations.CreateModel(
            name='DefaultPolicy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accept', models.BooleanField(default=True, help_text='Whether this rule accepts peering connection or filters them out.')),
                ('asys', models.ForeignKey(help_text='Owner of the policy.', on_delete=django.db.models.deletion.CASCADE, to='peering_coord.as', verbose_name='AS')),
                ('vlan', models.ForeignKey(help_text='VLAN the policy is applied to.', on_delete=django.db.models.deletion.CASCADE, to='peering_coord.vlan', verbose_name='VLAN')),
            ],
            options={
                'verbose_name': 'Default Policy',
                'verbose_name_plural': 'Default Policies',
            },
        ),
        migrations.CreateModel(
            name='AsPeerPolicy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accept', models.BooleanField(default=True, help_text='Whether this rule accepts peering connection or filters them out.')),
                ('asys', models.ForeignKey(help_text='Owner of the policy.', on_delete=django.db.models.deletion.CASCADE, to='peering_coord.as', verbose_name='AS')),
                ('peer_as', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='peering_coord.as', verbose_name='Peer AS')),
                ('vlan', models.ForeignKey(help_text='VLAN the policy is applied to.', on_delete=django.db.models.deletion.CASCADE, to='peering_coord.vlan', verbose_name='VLAN')),
            ],
            options={
                'verbose_name': 'AS Peering Policy',
                'verbose_name_plural': 'AS Peering Policies',
            },
        ),
        migrations.AddField(
            model_name='as',
            name='isd',
            field=models.ForeignKey(help_text='Every AS is part of a single ISD.', on_delete=django.db.models.deletion.CASCADE, related_name='ases', to='peering_coord.isd', verbose_name='ISD'),
        ),
        migrations.AddField(
            model_name='as',
            name='owner',
            field=models.ForeignKey(help_text='The entity owning the AS.', on_delete=django.db.models.deletion.CASCADE, related_name='ases', to='peering_coord.owner'),
        ),
        migrations.AddField(
            model_name='acceptedpeer',
            name='asys',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='peering_coord.as'),
        ),
        migrations.AddField(
            model_name='acceptedpeer',
            name='peer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='peering_coord.as'),
        ),
        migrations.AddField(
            model_name='acceptedpeer',
            name='vlan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='peering_coord.vlan', verbose_name='VLAN'),
        ),
        migrations.AddConstraint(
            model_name='peeringclient',
            constraint=models.UniqueConstraint(fields=('asys', 'name'), name='unique_peering_client_name'),
        ),
        migrations.AddConstraint(
            model_name='ownerpeerpolicy',
            constraint=models.UniqueConstraint(fields=('vlan', 'asys', 'peer_owner'), name='unique_org_policy'),
        ),
        migrations.AddConstraint(
            model_name='link',
            constraint=models.UniqueConstraint(fields=('interface_a', 'interface_b'), name='unique_links_per_interface'),
        ),
        migrations.AddConstraint(
            model_name='link',
            constraint=models.CheckConstraint(check=models.Q(('interface_a', django.db.models.expressions.F('interface_b')), _negated=True), name='different_interfaces'),
        ),
        migrations.AddConstraint(
            model_name='isdpeerpolicy',
            constraint=models.UniqueConstraint(fields=('vlan', 'asys', 'peer_isd'), name='unique_isd_policy'),
        ),
        migrations.AddConstraint(
            model_name='defaultpolicy',
            constraint=models.UniqueConstraint(fields=('vlan', 'asys'), name='unique_default_policy'),
        ),
        migrations.AddConstraint(
            model_name='aspeerpolicy',
            constraint=models.UniqueConstraint(fields=('vlan', 'asys', 'peer_as'), name='unique_as_policy'),
        ),
        migrations.AddConstraint(
            model_name='acceptedpeer',
            constraint=models.UniqueConstraint(fields=('asys', 'peer', 'vlan'), name='unique_peer_relation'),
        ),
    ]