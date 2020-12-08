from kubernetes import client, config
import json
import requests
import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import pytz
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


aToken = "eyJhbGciOiJSUzI1NiIsImtpZCI6InhVblhMTzFwTnZPSG9qWjZrR1ZkYk5BWmR6MDJ6NzZsdHRGekozOTh3N0EifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4teGc5emwiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImY2ZmY4NjFkLWVhY2UtNDJmYi05Y2RiLWYzMzM2NDQ5MmI1NSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.lyMxyEyetbqMVxy9Wq3VA-Ci3TabIn7kIeEML7XTGDDJ-I0yx8sUHUc1oyP02l93S8vFDvMWfHD_eUcWlSI30PhnfkxP2TlYThrrsBhWwjAsl5UABj3LhkHWWioGY28i_m7hHlta711wfvFofuvVq95rn2D8mqUN_VfDvVRz5kj5zFBusFX54-QcSEKYmBoiKhtdYjYXcfV_4ESEvyHkhq-bHWD4kaL4YxgrpGBHWXyoIDKUvq5PmRvziOdugSBLJyqITsj0nTpucaU3dUfbRBVbRHjlxcQfN5QC4o9eqFYnzQ-wIjblmHAvsv8sgsvTjO3GE3kWhNacTawjGShkiQ"
api_server = "https://192.168.191.206:6443"

def authentication():
    # Define the barer token we are going to use to authenticate.
    # See here to create the token:
    # https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster/
    # aToken = aToken
    # Create a configuration object
    aConfiguration = client.Configuration()

    # Specify the endpoint of your Kube cluster
    aConfiguration.host = api_server

    # Security part.
    # In this simple example we are not going to verify the SSL certificate of
    # the remote cluster (for simplicity reason)
    aConfiguration.verify_ssl = False
    # Nevertheless if you want to do it you can with these 2 parameters
    # configuration.verify_ssl=True
    # ssl_ca_cert is the filepath to the file that contains the certificate.
    # configuration.ssl_ca_cert="certificate"

    aConfiguration.api_key = {"authorization": "Bearer " + aToken}

    # Create a ApiClient with our config
    aApiClient = client.ApiClient(aConfiguration)

    # Do calls
    v1 = client.CoreV1Api(aApiClient)
    return v1

#def add_label(nodename, type, label):
    #body = '[{"op": "test", "path": "/metadata/labels", "value":' + "{" + '"' + type + '"' + ":" + '"' + label + '"' + "}"+'}]'
    #print(body)
    #ret = authentication().patch_node(name=nodename, body=json.loads(body))
    #return ret.metadata.labels

def add_label(nodename,key,value):
    data = '{"metadata":{"labels":{' + '"' + key + '"' + ":" + '"' + value + '"' + "}" + '}}'
    url = api_server+"/api/v1/nodes/"+nodename
    headers = '{"Accept": "application/json","Content-type": "application/merge-patch+json", "Authorization": "Bearer '+aToken+'"}'
    response = requests.patch(url, headers=json.loads(headers), data=json.dumps(json.loads(data)), verify=False)
    return response

#add_label('worker-node-kuht2','type','run-app')


#boo is boolean
def cordon_node(nodename, is_it_unschedule):
    body = '[{"op": "replace", "path": "/spec/unschedulable", "value":'+ is_it_unschedule +'}]'
    ret = authentication().patch_node(name=nodename, body=json.loads(body))
    return ret.spec.unschedulable

def delete_node(nodename):
    url = api_server + "/api/v1/nodes/" + nodename
    headers = '{"Content-type": "application/json", "Authorization": "Bearer '+aToken+'"}'
    response = requests.delete(url,headers=json.loads(headers),verify=False)
#    print(json.loads(text))
    return response.status_code

#print(delete_node('worker-node-m9ar7'))


def evict_pod(podname, namespace):
    data = '{"apiVersion": "policy/v1beta1","kind": "Eviction","metadata": {"name": '+'"'+ podname +'"'+ ',"namespace": '+'"'+ namespace +'"'+'}}'
    url = api_server+"/api/v1/namespaces/"+namespace+"/pods/"+podname+"/eviction"
    headers = '{"Content-type": "application/json", "Authorization": "Bearer '+aToken+'"}'
    #print(data)
    #print(url)
    response = requests.post(url, headers=json.loads(headers), data=json.dumps(json.loads(data)), verify=False)
    return json.loads(response.text)



def list_pods_on_node(nodename, namespace):
#    print("Listing pods in node:")
    pods = []
    ret = authentication().list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        if i.spec.node_name == nodename and i.metadata.namespace == namespace:
           #print("%s\t%s\t%s" %
            #     (i.spec.node_name, i.metadata.namespace, i.metadata.name))
           pods.append({'podname':i.metadata.name})
    return pods


#def list_pending_pods(namespace):
#    pods = []
#    ret = authentication().list_namespaced_pod(namespace)
#    for i in ret.items:
#        if pod.status.phase == 'Pending':
#            pods.append({'podname':i.metadata.name})
#            print(i.status.conditions[0])
#    return pods

def check_pending_pods(namespace):  
    pod_list = authentication().list_namespaced_pod(namespace)
    for pod in pod_list.items:
        now = datetime.datetime.now(pytz.utc)
        start_time = pod.metadata.creation_timestamp
        period = now - start_time
        #total_second = period.days * 86400 + period.hours*3600 + period.minutes*60 + period.second
        #print(period.total_seconds())
        if pod.status.phase == 'Pending' and period.total_seconds() > 20 and pod.status.start_time == None:
#            print("%s\t%s\t%s" % (pod.metadata.name,pod.status.phase,pod.status.pod_ip))
            #print(pod.metadata.name)
            #print(pod.status)
            return True
    return False



def check_running_pods(namespace):  
    pod_list = authentication().list_namespaced_pod(namespace)
    for pod in pod_list.items:
        if pod.status.phase == 'Running':
#            print("%s\t%s\t%s" % (pod.metadata.name,pod.status.phase,pod.status.pod_ip))
            return True

#print(check_pending_pods("default"))

#for pod in list_pods('worker-node-2','default'):
#    print(pod['podname'])

def convert_cpu_unit(cpu):
    if cpu[len(cpu) - 1] == 'm':
        return int(cpu[0:len(cpu) - 1])/1000
    else:
        return int(cpu)

def convert_memory_unit(memory):
#value will be converted to MB:
    if memory[len(memory) - 1] == 'i':
        if memory[len(memory) - 2] == 'G':
            return int(memory[0:len(memory) - 2])*1024
        if memory[len(memory) - 2] == 'M':
            return int(memory[0:len(memory) - 2])
        if memory[len(memory) - 2] == 'K':
            return int(memory[0:len(memory) - 2])/1024

    if memory[len(memory) - 1] == 'G':
        return int(memory[0:len(memory) - 1])*1024
    if memory[len(memory) - 1] == 'M':
        return int(memory[0:len(memory) - 1])
    if memory[len(memory) - 1] == 'K':
        return int(memory[0:len(memory) - 1])/1024
    
    if int(memory) :
        return int(memory)/1048576 


def get_resource_requirement_of_hpa(namespaces=["default"]):
#return core and mb
    sum_cpu = 0
    sum_memory = 0
    for namespace in namespaces:
        pods_list = authentication().list_namespaced_pod(namespace)
        for i in pods_list.items:
            if i.status.phase == 'Pending' and i.status.start_time == None:
#                print(i.metadata.name)
                cpu = i.spec.containers[0].resources.requests['cpu']
                sum_cpu += convert_cpu_unit(cpu)

                memory = i.spec.containers[0].resources.requests['memory']
                sum_memory += convert_memory_unit(memory)

    data = dict()
    data['cpu'] = round(sum_cpu,2)
    data['memory'] = round(sum_memory,2)

    return data


def is_node_ready(nodename):
    if nodename == '':
        return True

    url = api_server + "/api/v1/nodes/" + nodename + "/status"
    headers = '{"Content-type": "application/json", "Authorization": "Bearer '+aToken+'"}'
    response = requests.get(url,headers=json.loads(headers),verify=False)
    if response.status_code == 404:
        return False
    conditions = json.loads(response.text)['status']['conditions']
    type = conditions[len(conditions) -1 ]['type']
    status = conditions[len(conditions) -1 ]['status']
    #print(type(status))
    return type == 'Ready' and (status == 'True' or status == True) 

#print(is_node_ready('worker-node-b237c'))



#print(is_node_ready('worker-node-xyz'))


#print(get_resource_requirement_of_hpa())

#print(authentication())
