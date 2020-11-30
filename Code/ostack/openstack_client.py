from openstack import connection
import base64
import string
import random
import time

def authentication():
    conn = connection.Connection(
        region_name='RegionOne',
        auth=dict(
            auth_url='http://192.168.125.128/identity/v3/',
            username='admin',
            password='123456',
            project_id='2464b6d55da945dcaa7bc1b32322f5ff',
            user_domain_id='default'),
#    compute_api_version='2.1',
#    identity_interface='internal'
    )
    return conn

provider_network_id = '8f795644-6436-43aa-967e-0f6e733139dc'

def stop_instance(conn, server_id):
    conn.compute.stop_server(server_id)

def start_instance(conn, server_id):
    conn.compute.start_server(server_id)


def list_servers(conn,name_filter):
    servers_list=[]
    for server in conn.compute.servers():
        if(server.name[0:12] == name_filter):
           servers_list.append(server.name)
    return servers_list

def get_server_id_by_name(conn, name_server):
    server = conn.compute.find_server(name_server)
    return server.id

def find_server(conn, name_server):
    res = conn.compute.find_server(name_server)
    return res

#find_server(authentication(),'worker-node-0erl')

def get_available_worker_node(conn):
    servers_list={}
    for server in conn.compute.servers():
        if server.name[0] == 'w' and server.status == 'SHUTOFF':
           servers_list.update({'name':server.name, 'id':server.id})
           break
    return servers_list


def list_running_worker_nodes(conn):
    servers_list=[]
    for server in conn.compute.servers():
        if server.name[0] == 'w' and server.status == 'ACTIVE':
           servers_list.append({'name':server.name, 'id':server.id})
    return servers_list

 

def list_images(conn):
    print("List Images:")

    for image in conn.compute.images():
        print(image.name)

def list_networks(conn):
    print("List Networks:")

    for network in conn.network.networks():
        print(network.name)


def name_generator(name, size=5, chars=string.ascii_lowercase + string.digits):
    id = ''.join(random.choice(chars) for _ in range(size))
    return name + id

def create_flavor(conn, name:str, vcpus:int, ram:int, disk:int, ephemeral = 0, swap = 0, rxtx_factor = 1):
    new_flavor = conn.create_flavor(name=name,
                                    vcpus=vcpus,
                                    ram=ram,
                                    disk=disk,
                                    ephemeral=ephemeral,
                                    swap=swap,
                                    rxtx_factor=rxtx_factor)
    return new_flavor.id


def create_server(conn,name,vcpus,ram,disk):
    print("Create Server:")
    name = name_generator(name)
    image = conn.compute.find_image('Bionic-18.04')
#create new flavor 
    flavor_id = create_flavor(conn,name=name,vcpus=vcpus,ram=ram,disk=disk)

    network = conn.network.find_network('private-k8s')
    f = open('/opt/stack/the_thesis/Code/ostack/user_data.txt','r')
    user_data = f.read()
    user_data = base64.b64encode(user_data.encode('ascii'))
    user_data = user_data.decode('ascii')


    server = conn.compute.create_server(
        name=name, image_id=image.id, flavor_id=flavor_id,
        networks=[{"uuid": network.id}], key_name='K8s-1', user_data = user_data)

    server = conn.compute.wait_for_server(server)

#get server id
    server_id = conn.compute.find_server(name)['id']

#create floating ip
    new_floating_ip = create_floating_ip(conn, provider_network_id)

#associate floating ip to new server
    assign_floating_ip(conn,server_id,new_floating_ip)
    return name



def assign_floating_ip(conn,server_id,floating_ip):
    conn.compute.add_floating_ip_to_server(server_id,floating_ip)

#assign_floating_ip(authentication())



def get_available_floating_ip(conn):
   for i in conn.network.ips():
       if i.status == 'DOWN' and i.floating_network_id == provider_network_id:
            print(i.floating_ip_address)

#get_available_floating_ip(authentication())

def test(conn):
   print(conn.compute.find_server('worker-node-1')['id'])


def create_floating_ip(conn, provider_network_id):
#network id of provider network
   new_floating_ip_info = conn.network.create_ip(floating_network_id = provider_network_id)
   return new_floating_ip_info.floating_ip_address

def delete_server(conn, id):
    flavor_id = conn.compute.find_flavor(conn.compute.get_server(id).flavor['original_name']).id
    server = conn.compute.delete_server(id)
#Sleep to floating ip change to DOWN
    time.sleep(10)
    for i in conn.network.ips():
        if i.status == 'DOWN' and i.floating_network_id == provider_network_id:
            delete_floating_ip(conn, i.floating_ip_address)
        #print(i)

#delete flavor
    delete_flavor(conn,flavor_id)
    return server

def find_floating_ip(conn, ip):
    ip_info = conn.network.find_ip(name_or_id=ip)
    return ip_info

def delete_floating_ip(conn, ip):
    ip_info = find_floating_ip(conn, ip)
    response = conn.network.delete_ip(ip_info.id)
#    print(response)
    return response

def delete_flavor(conn, id):
    flavor = conn.compute.delete_flavor(id)
    return flavor


#def test(conn, id):
#    print(conn.compute.find_flavor(conn.compute.get_server(id).flavor['original_name']).id)

#test(authentication(),'93b2a68c-747b-4345-bbc2-32628e506f2d')

#find_floating_ip(authentication(),'192.168.191.232')
#delete_floating_ip(authentication(),'192.168.191.232')
#create_flavor(authentication(),name="HungCao",vcpus=1,ram=128,disk=5)
#create_floating_ip(authentication(),provider_network_id)

#create_server(authentication(), name= "INSTANCE_PREFIX-", vcpus=1, ram=1224, disk=15)

#print(delete_server(authentication(),'f42fc5fe-9f59-46b0-b8f9-851c6d27f624'))
#list_floating_ips(authentication())
#delete_server(authentication(),'31fbd873-2e4b-4128-878b-043ad4d3c99d')
