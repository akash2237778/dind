import logging
from kubernetes import client, config
import os
import shutil
import time


from flask import (current_app, request)
from werkzeug.exceptions import InternalServerError, NotFound
import yaml
from git import Repo

fname = "template.yaml"
save_location = ""
repo_dir = ""

logger = logging.getLogger(__name__)

error_response = {
    'code': 500,
    'message': 'Something went wrong.',
}

k8s_config = config.load_incluster_config()
v1 = client.CoreV1Api()
apiV1 = client.AppsV1Api()
namespace='default'

def startBuild():
    try:
      repo_url = request.json['url']
      repo_dir = repo_url.split('/')[4].split('.')[0]
      save_location = repo_dir+'-kaniko.yaml'
      gitClone(repo_url, '/file/'+repo_dir)
      deploymentFile = createDeploymentYAML(dockerfile='/file/'+ repo_dir + '/' + request.json['dockerfile'], destination=request.json['destination'], buildContext='/file/'  +repo_dir + '/', save_location=save_location)
      buildAndPushImage(deploymentFile)
      time.sleep(350)
      remove_files('/file/'+repo_dir, save_location, 'kaniko', namespace)
      return 'successful'
    except InternalServerError:
        raise InternalServerError


def gitClone(git_url, repo_dir):
    Repo.clone_from(git_url, repo_dir)

def createDeploymentYAML(dockerfile: str, destination: str, buildContext: str, save_location: str):
    stream = open(fname, 'r')
    data = yaml.load(stream)
    data['spec']['containers'][0]['args'] = [f"--dockerfile={dockerfile}", f"--destination={destination}", f"--context={buildContext}"]    
    with open(save_location, 'w') as yaml_file:
        yaml_file.write( yaml.dump(data, default_flow_style=False))
    return save_location

def buildAndPushImage(deploymentLocation: str):
    with open(deploymentLocation) as f:
        dep = yaml.safe_load(f)
        resp = v1.create_namespaced_pod(
            body=dep, namespace="default")
        print("Deployment created. status='%s'" % resp.metadata.name)
    return 0

def get_deployments(name=None):
    if name is None:
        pod_list = apiV1.list_namespaced_deployment(namespace)
        pods = []
        for pod in pod_list.items:
            pods.append(pod.metadata.name)
        return pods
    deployments = apiV1.list_namespaced_deployment(namespace)
    for deployment in deployments.items:
        if deployment.metadata.name == name:
            return deployment.spec.template.spec.containers[0].image
    return None

def remove_files(dirLocation: str, kaniko_file: str, pod_name: str, namespace: str):
    shutil.rmtree(dirLocation)
    delete_pod(pod_name, namespace)
    os.remove(kaniko_file)


def delete_pod(name, namespace):
	api_instance = client.CoreV1Api()
	body = client.V1DeleteOptions()
	api_response = api_instance.delete_namespaced_pod(name, namespace)
	return api_response