import os
from ostack import openstack_client
from k8s import k8s_client
from prometheus import prometheus_client
import time, threading
import datetime
import math
import psutil
from threading import Lock
lock = Lock()

authen_op = openstack_client.authentication()
last_time_scale_up = datetime.datetime.utcnow()
last_created_server = ''

INSTANCE_PREFIX = "worker-node-"

def scale_up(required_resource: dict):
    name_server = openstack_client.create_server(authen_op, name=INSTANCE_PREFIX, vcpus=required_resource['cpu'], ram=required_resource['memory'], disk=15)
    return name_server


def get_required_resource(namespaces=["default"]):
    """
    predict required resource based on loads in namespaces (`default`,`mosquitto`)
    return required_resource map({"cpu": "", "mem": ""})
    """
    """
    min cpu = 1, min memory = 1024
    """
    resource = k8s_client.get_resource_requirement_of_hpa(namespaces=namespaces)
    cpu = math.ceil(resource['cpu'])
    memory = resource['memory']
    if (memory + 500) < 1024:
        memory = 1024
    else:
        memory = memory + 500
    spec = dict()
    spec["cpu"] = cpu
    spec["memory"] = memory
    print(spec)
    return spec

def has_enough_resource(conn, required_resource):
    cpu_sum = psutil.cpu_count()
    cpu_current = openstack_client.get_sum_cpu_and_memory_servers(conn)['cpu']
    memory_free = dict(psutil.virtual_memory()._asdict())['available']/(1024*1024) 
    cpu_request = required_resource['cpu']
    memory_request = required_resource['memory']
#    print('cpu sum: ',cpu_sum)
#    print('cpu current: ',cpu_current)
#    print('cpu request: ',cpu_request)
#    print('memory free: ',memory_free)
#    print('memory request: ',memory_request)

    if (cpu_sum - cpu_current) > cpu_request and memory_free > (memory_request + 400):
        return True
    else:
        return False


def has_pending_pods(namespaces=["default","mosquitto"]):
    for ns in namespaces:
        if k8s_client.check_pending_pods(ns) == True:
            #print(ns)
            return True
    return False



def node_has_pod(instance_name, namespaces=["default","mosquitto"]):
#    list all pods running on this instance
    count = 0
    for ns in namespaces:
        if len(k8s_client.list_pods_on_node(instance_name,ns)) > 0:
            count = count + 1
    return count > 0

def list_free_servers(name_filter):
    free_servers = []
    servers_list = openstack_client.list_servers(authen_op, name_filter)
    for sv in servers_list:
        if node_has_pod(sv,namespaces=["default"]) == False:
            free_servers.append(sv)
    return free_servers

def main_checker():
    lock.acquire()
    # check each interval to perform action, i.e. scale up/down
    # step, interval unit = second
    global last_created_server
    global last_time_scale_up 

    if has_pending_pods():
#            print(last_created_server)
        required_resource = get_required_resource(namespaces=["default"])
        if has_enough_resource(authen_op,required_resource):
            last_created_server = scale_up(required_resource)
            last_time_scale_up = datetime.datetime.utcnow()
            print(f"Scaled up: Server = {last_created_server}")

            while not k8s_client.is_node_ready(last_created_server):
                    pass
            k8s_client.add_label(last_created_server,'type','run-app')
            print("Node ready. Wait for scheduling pod on new server")
            time.sleep(15)
            print("Continue check")
        else:
            print("Cannot create new server. Not have enough resource.")

    #print('Last scaling up time:')
    #print(last_time_scale_up)
    free_servers = list_free_servers(INSTANCE_PREFIX)
    if len(free_servers) > 0:
#            print("Time remaining:")
#            print(200 - (datetime.datetime.utcnow() - last_time_scale_up).total_seconds())
        SCALE_DOWN_WAIT_TIME = 600
        if (datetime.datetime.utcnow() - last_time_scale_up).total_seconds() > SCALE_DOWN_WAIT_TIME:
            for sv in free_servers:
                print("Unschedule " + sv)
                k8s_client.cordon_node(sv,'true')

                print("Delete " + sv)
#Delete node from cluster
                k8s_client.delete_node(sv)
#Delete server
                server_id = openstack_client.get_server_id_by_name(authen_op,sv)
                openstack_client.delete_server(authen_op,server_id)
                print("Continue check")
    lock.release()

def run_app():
    MAIN_CHECK_INTERVAL = 10
    main_checker_thread = threading.Timer(MAIN_CHECK_INTERVAL, run_app)
    main_checker_thread.start()
    main_checker()
    main_checker_thread.join()

def main():
    print("Start autoscaler")
    run_app()


if __name__ == "__main__":
    main()
