import psutil

def get_available_resource():

#OK
    number_of_cores = psutil.cpu_count()
    print(number_of_cores)

#Chua chac lam
#    cpu_percent = psutil.cpu_percent()
#    print(cpu_percent)
#    available_cores = number_of_cores*(1-cpu_percent)

    memory = dict(psutil.virtual_memory()._asdict())['free']/(1024*1024)
    print(memory)

get_available_resource()