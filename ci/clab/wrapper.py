#!/bin/python3

print('go make so things')
import docker
import yaml
import os
import time
import re
import sys
# Start Docker daemon
os.system('rm /var/run/docker.pid')
os.system('rm /var/run/docker/containerd/containerd.pid')
os.system('dockerd --host=unix:///var/run/docker.sock &')
time.sleep(5)


# Check and create containers if necessary
client = docker.from_env()
img_docker = [ image.tags[0] for image in client.images.list(name='vrnetlab/*')]
a_yaml_file = open("clab.yaml")
parsed_yaml_file = yaml.load(a_yaml_file, Loader=yaml.FullLoader)
for item, value in parsed_yaml_file.get("topology").get("kinds").items():
    if item.startswith("vr"):
        if value['image']not in img_docker:
            type = re.match(r'vrnetlab\/vr-(.*):', value['image'])
            os.system('ln -fs /app/images/{}/* /app/vrnetlab/{}/'.format(type.group(1),type.group(1)))
            os.system('cd /app/vrnetlab/{} && make'.format(type.group(1)))

# Check if all necessary containers exists
img_docker = [ image.tags[0] for image in client.images.list(name='vrnetlab/*')]
for item, value in parsed_yaml_file.get("topology").get("kinds").items():
    if value['image']not in img_docker:
        sys.exit("container {} don't exist and no image available".format(value['image']))

os.system('/app/containerlab/bin/containerlab deploy --reconfigure --topo /app/clab.yaml')
liste = []
for x in os.listdir("/var/lib/docker/containers/"):
    liste.append("/var/lib/docker/containers/{}/{}-json.log".format(x,x))
os.system('tail -f {}'.format(" ".join(liste)))
#os.system("watch 'docker ps --format \"{{.Names}}\" | sort | xargs -n1 -I {} docker logs {} --tail=8'")
