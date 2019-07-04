import atexit
import argparse
from vcenter_utils import utils
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
import requests
import json
from collections import namedtuple
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def GetArgs():
   """
   Supports the command-line arguments listed below.
   """

   parser = argparse.ArgumentParser(description='Process args for powering on a Virtual Machine')
   parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=True, action='store', help='Password to use when connecting to host')
   parser.add_argument('-n', '--netboxhost', required=True, action='store', help='Host of netbox server')
   parser.add_argument('-t', '--netboxtoken', required=True, action='store', help='The API token assigned to the user for netbox api access')
   args = parser.parse_args()
   return args
args = GetArgs()

netboxhost = args.netboxhost
netbox_token = args.netboxtoken

def get_clusters():

    obj_utils = utils()
    si = obj_utils.si_instance(args.host, args.user, args.password, args.port)
    atexit.register(connect.Disconnect, si)
    content = si.RetrieveContent()
    container = content.rootFolder  # starting point to look into
    viewType = [vim.ClusterComputeResource]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(container, viewType, recursive)
    children = containerView.view
    cluster_list = []
    for child in children:
        logger.debug('Set Cluster name : ' + child.name)
        cluster_list.append({'name' : child.name})
    return cluster_list

def get_netbox_object():

    clusters = requests.get('http://' + netboxhost + '/api/virtualization/clusters/?limit=100')
    cfg = json.loads(clusters.content)
    cluster_object = namedtuple('ConfigObject', cfg.keys())(**cfg)
    for c in cluster_object.results:
        logger.debug(c['name'])

def add_netbox_clusters(host, token, cluster_type, cluster_group, cluster_site, cluster_object):
    """
    Used to add clusters to netbox
    """
    request_content = {}
    for obj in cluster_object:
        logger.debug('Cluser Name to be added : ' + obj['name'])
        logger.debug('Cluser Type to be added : ' + str(cluster_type))
        logger.debug('Cluser Group to be added : ' + str(cluster_group))
        request_content.update({'name': obj['name']})
        request_content.update({'type': cluster_type})
        request_content.update({'group': cluster_group})
        request_content.update({'site': cluster_site})
        successful = 0
        failed = 0
        try:
            request = requests.post(url='http://' + host + '/api/virtualization/clusters/', json=request_content, headers={'Content-Type':'application/json', 'Authorization': 'token ' + token})
            successful += 1
        except Exception as e:
            logger.warning(e)
            failed += 1
    status = 'Number of Successful Request : ' + str(successful) + '  Number of Failed Request : ' + str(failed)
    return status


clusters = get_clusters()
add_netbox_clusters(netboxhost, netbox_token, 2, 2, 6, clusters)
print('done')