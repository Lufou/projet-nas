import json
import requests
import time

#negotiation auto
#The application GNS3 must be openned
#augmenter le nbr d'interface en fct du fichier


# Function that checks the other interface
def check(links, node1, node2):
    lists=links[node2]
    for i in lists:
        if i[1]==node1:
            return i[0][15]


#We open our configuration file
with open('config.json') as json_file:
    data = json.load(json_file)
    project_name = data["Project_name"]

# Retrieve the links between the routers
links={}
for router_name in data:
    if router_name != "Project_name":
        list_interfaces=[]
        for interface in data[router_name]['interfaces']:
            if interface['InterfaceName']!="Loopback0":
                l=[]
                l.append(interface['InterfaceName'])
                l.append(interface['Link'])
                list_interfaces.append(l)
        links[router_name]=list_interfaces



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
node_ids={}
for router, template in routers.items():
    # Dynamips should be treated as a different case
    if template=="c7200":
        data = {
        "symbol": ":/symbols/router.svg",
        "name": router,
        "properties": {"platform": "c7200", "nvram": 512, "image": "c7200-advipservicesk9-mz.152-4.S5.image", "ram": 512, "slot0": "IO-FE","slot1": "PA-GE", "slot2": "PA-GE" , "slot3":"PA-GE", "system_id": "FTX0945W0MY"},
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
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code == 201:
        print(f"Node '{router}' of type '{template}' added to project '{project_id}'.")
        node_ids[router]=(json.loads(response.text))["node_id"]
    else:
        print(f"Error adding node to project: {response.status_code} {response.reason}")
        print(response.text)

# Make the links between the routers
for router, allinks in links.items():
    node1_id=node_ids[router]
    for l in allinks:
        node2_id=node_ids[l[1]]
        interface1=int(l[0][15])
        interface2=int(check(links, router, l[1]))
        # Create the payload for the API call to create the link
        payload = {
            "nodes": [
                {
                    "node_id": node1_id,
                    "adapter_number": interface1,
                    "port_number": 0
                },
                {
                    "node_id": node2_id,
                    "adapter_number": interface2,
                    "port_number": 0
                }
            ]
        }
        # Make the API call to create the link
        response = requests.post(f"{address}/v2/projects/{project_id}/links", json=payload, headers=headers)

        # Check the response status code to make sure the link was created successfully
        if response.status_code == 201:
            print("Link created successfully")
        #else:
        #    print(response.text)
        #    print("Failed to create link")

