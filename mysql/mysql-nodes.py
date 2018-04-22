# Copyright 2016 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


COMPUTE_URL_BASE = 'https://www.googleapis.com/compute/v1/'

def _ConfigName(context):
    """Return the short config name."""
    return '{}-config'.format(context.env['deployment'])


"""Creates a MySQL Cluster configuration."""


def GenerateConfig(context):
    """Generates config."""

    region = context.properties['zones'][0][:-2]

    config = {'resources': []}

    deployment_name = context.env['deployment']
    machine_type = context.properties['machineType']
    network = context.properties['network']
    subnetwork = context.properties['subnetwork']
    nodes_per_zone = context.properties['nodesPerZone']
    assign_public_ip = context.properties['assignPublicIp']
    image = context.properties['image']
    template_name = context.env['name']
    disk_per_zone = context.properties['diskPerNode']
    num_dcs = len(context.properties['zones'])
    project = context.env["project"]
    node_seq = 0

    for zone_name in context.properties['zones']:
        for node_id in range(1, nodes_per_zone+1):
            ip = {
                'name': deployment_name + '-ip-' + zone_name[-1] + str(node_id),
                'type': 'compute.v1.address',
                'properties': {
                    'region': region,
                    'addressType': 'INTERNAL',
                    'subnetwork': 'regions/' + region + '/subnetworks/' + subnetwork
                }
            }
            config['resources'].append(ip)

        for node_id in range(1, nodes_per_zone+1):
            disks_to_attach = [{
                'deviceName': 'boot',
                'boot': True,
                'type': 'PERSISTENT',
                'autoDelete': True,
                'mode': 'READ_WRITE',
                'initializeParams': {
                    'sourceImage': image
                }
            }]
            for disk_id in range(1, disk_per_zone+1):
                disk_name = deployment_name + '-data' + str(disk_id) + '-' + str(node_seq)
                disk = {
                    'name': disk_name,
                    'type': 'compute.v1.disk',
                    'properties': {
                        'zone': zone_name,
                        'sizeGb': context.properties['dataDiskSize'],
                        'type': ''.join([COMPUTE_URL_BASE,
                                         'projects/', project, '/zones/',
                                         zone_name,
                                         '/diskTypes/', context.properties['dataDiskType']])
                    }
                }

                config['resources'].append(disk)
                disk_to_attach = {
                    'deviceName': disk_name,
                    'type': 'PERSISTENT',
                    'boot': False,
                    'autoDelete': False,
                    'mode': 'READ_WRITE',
                    'source': ''.join(['$(ref.', disk_name, '.selfLink)'])
                }
                disks_to_attach.append(disk_to_attach)

            if assign_public_ip:
                tags = [deployment_name,template_name,'mysql-node','prometheus-node-exporter','prometheus-mysqld-exporter','cluster-' + deployment_name]
                network_interfaces = [{
                    'accessConfigs': [{
                        'name': 'external-nat',
                        'type': 'ONE_TO_ONE_NAT'
                    }],
                    'network': 'global/networks/' + network,
                    'networkIP': '$(ref.' + deployment_name + '-ip-' + zone_name[-1] + str(node_id) + '.address)',
                    'subnetwork': 'regions/' + region + '/subnetworks/' + subnetwork
                }]
            else:
                tags = [deployment_name,template_name,'mysql-node','no-ip', 'prometheus-node-exporter','prometheus-mysqld-exporter', 'cluster-' + deployment_name]
                network_interfaces = [{
                    'network': 'global/networks/' + network,
                    'networkIP': '$(ref.' + deployment_name + '-ip-' + zone_name[-1] + str(node_id) + '.address)',
                    'subnetwork': 'regions/' + region + '/subnetworks/' + subnetwork
                }]
            if node_seq == 0:
                tags.extend(['mysql-master', deployment_name + '-master'])
            else:
                tags.extend(['mysql-slave', deployment_name + '-slave'])

            instance = {
                'name': deployment_name + '-' + str(node_seq),
                'type': 'compute.v1.instance',
                'properties': {
                    'zone': zone_name,
                    'tags': {
                        'items': tags
                    },
                    'disks': disks_to_attach,
                    'networkInterfaces': network_interfaces,
                    'machineType': 'projects/' + project + '/zones/' + zone_name + '/machineTypes/' + machine_type,
                    'serviceAccounts': [{
                        'email': 'default',
                        'scopes': [
                            'https://www.googleapis.com/auth/monitoring'
                        ]
                    }]

                }
            }
            node_seq += 1
            config['resources'].append(instance)

    return config

