import json
import requests
import time

#negotiation auto
#script python qui genere json
#The application GNS3 must be openned

#We open our configuration file
with open('config.json') as json_file:
    data = json.load(json_file)
    project_name = data["Project_name"]


# Adding all the routers available as keys and their template as values in a dictionnary 
routers={}
for router_name in data:
    if router_name != "Project_name":
        router = data[router_name]
        if "Type" in router:
            routers[router_name] = router["Type"]
        else:
            print(f"The key 'Type' is not present in the dictionary for router {router_name}.")


# The address and port of the GNS3 server
address = "http://localhost:3080"

# Prepare the data for the POST request
data = {
    "name": project_name
}

# Prepare the POST request to the GNS3 API
url = f"{address}/v2/projects"
headers = {'Content-type': 'application/json'}
response = requests.post(url, data=json.dumps(data), headers=headers)

# Check the response status code
if response.status_code == 201:
    print(f"Project '{project_name}' created successfully")
    project_data = response.json()
    project_id = project_data["project_id"]
    print("Project ID:", project_id)
else:
    print(f"Error creating project: {response.status_code} {response.reason}")
    exit()

## Get the templates available
## Send the GET request to the GNS3 API
#url = f"{address}/v2/templates"
#response = requests.get(url)

# Check the response status code
#if response.status_code == 200:
#    templates = response.json()
#    for template in templates:
#        print(template["name"])
#else:
#    print(f"Error retrieving node templates: {response.status_code} {response.reason}")


# Adding the nodes in the project
for router, template in routers.items():
    # Dynamips should be treated as a different case
    if template=="c7200":
        data = {
        "symbol": ":/symbols/router.svg",
        "name": router,
        "properties": {"platform": "c7200", "nvram": 512, "image": "c7200-adventerprisek9-mz.153-3.XB12.image", "ram": 512, "slot0": "IO-FE", "system_id": "FTX0945W0MY"},
        "node_type": "dynamips",
        "compute_id":"local"
        }
    else:
        data={
            "name": router,
            "node_type": template,
            "compute_id": "local"
        }

    # Prepare the POST request to the GNS3 API
    url = f"{address}/v2/projects/{project_id}/nodes"
    headers = {'Content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code == 201:
        print(f"Node '{router}' of type '{template}' added to project '{project_id}'.")
    else:
        print(f"Error adding node to project: {response.status_code} {response.reason}")
        print(response.text)

# Make the links between the routers