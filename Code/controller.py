import os
from ostack import openstack_client
from k8s import k8s_client
from prometheus import prometheus_client
import time, threading
import datetime
import math
from threading import Lock
lock = Lock()

authen_op = openstack_client.authentication()
last_time_scale_up = datetime.datetime.utcnow()
last_created_server = ''

INSTANCE_PREFIX = "worker-node-"

def scale_up(required_resource: dict):
    # TODO: check and aquire scale lock
    name_server = openstack_client.create_server(authen_op, name=INSTANCE_PREFIX, vcpus=required_resource['cpu'], ram=required_resource['memory'], disk=15)   
    # TODO: release scale lock after success
    return name_server

def scale_down(server_info, name_filter=INSTANCE_PREFIX):
#    server_info = openstack_client.scale_down_instance(authen_op)
    # TODO: check and aquire scale lock

    # TODO: handle filter instance to scale down with prefix
    if server_info:
        print('Start scaling down...')
        instance_name = server_info['name']
        instance_id = server_info['id']
        # TODO: handle all namespace (except kube-system, monitoring)
        namespace = 'default'

#cordon node in k8s cluster
        if k8s_client.cordon_node(instance_name,'true') == True:
            print(instance_name+' cordoned')
        else:
            print('Something is wrong ???')

#list all pods running on this instance
#        pods = k8s_client.list_pods_on_node(instance_name,namespace)

#evict all pods running on this instance
#        if pods:
#            for pod in pods:
#                print('evict pod' + pod['podname'] + " " + k8s_client.evict_pod(pod['podname'],namespace)['status'])
#        else:
#            print('The number of pods is 0')

#shutdown this instance
#        time.sleep(10)
        openstack_client.stop_instance(authen_op,instance_id)
        print(instance_name+' is stopped')
    # TODO: release scale lock after success


# def get_loads(type="cpu",interval=10, step=10,namespaces=["default","mosquitto"]):
#     """
#     return timeseries_load: list(map({time: load}))
#     """
#     #loads = prometheus_client.get_cpu_time_series_data(interval,step)
#     #loads = prometheus_client.get_average_resource_request_data_by_minute(interval=interval,step=step,namespaces=namespaces)
#     return loads


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
    if memory < 1024:
        memory = 1024
    else:
        memory = memory + 200
    spec = dict()
    spec["cpu"] = cpu
    spec["memory"] = memory
    print(spec)
    return spec



def has_pending_pods(namespaces=["default","mosquitto"]):
    # TODO: get pending pods
    for ns in namespaces:
        if k8s_client.check_pending_pods(ns) == True:
            #print(ns)
            return True
    return False


#print(has_pending_pods())

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
    try:
        # check each interval to perform action, i.e. scale up/down
        # step, interval unit = second
        global last_created_server
        global last_time_scale_up 
        #loads = get_loads(interval=5, step=60, namespaces=["default"])
        #print(loads)
        #print('has pending pod ?')
        #print(has_pending_pods())
        #print(last_created_server + ' is ready ?')
        #print(k8s_client.is_node_ready(last_created_server))

        #if last_created_server != '' and openstack_client.find_server(authen_op, last_created_server) == None:
        #    last_created_server = ''

        if has_pending_pods():
            print(last_created_server)
            required_resource = get_required_resource(namespaces=["default"])
            last_created_server = scale_up(required_resource)
            last_time_scale_up = datetime.datetime.utcnow()
            print(f"Scaled up: Server = {last_created_server}")

            while not k8s_client.is_node_ready(last_created_server):
                    pass
            k8s_client.add_label(last_created_server,'type','run-app')
            print("Node ready. Wait for scheduling pod on new server")
            time.sleep(10)
            print("Continue check")

            
        #print('Last scaling up time:')
        #print(last_time_scale_up)
             
            
        free_servers = list_free_servers(INSTANCE_PREFIX)
        
        #print("free servers:")
        #print(free_servers)
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
                    
    finally:
        lock.release()




def test():
    MAIN_CHECK_INTERVAL = 10
    main_checker_thread = threading.Timer(MAIN_CHECK_INTERVAL, test)
    main_checker_thread.start()
    main_checker()
    main_checker_thread.join()

def main():
    print("Start autoscaler")
    # TODO: update interval values to appropriate values
    test()





if __name__ == "__main__":
    main()
