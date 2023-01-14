import json
import requests
import telnetlib
import time

#negotiation auto
#The application GNS3 must be openned

#//////////////Creation of the project//////////////
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

#//////////////Routers' configuration//////////////

# Start the routers
ports={}
for router,router_id in node_ids.items():
    response = requests.post(f"{address}/v2/projects/{project_id}/nodes/{router_id}/start", headers=headers)
    ports[router]=(json.loads(response.text))["console"]
print("Nodes activated")

# The telnet session for each router configuration
ip="127.0.0.1"
for router, port in ports.items():
    # Create a new Telnet connection
    tn = telnetlib.Telnet(ip, port)
    print("created")

    # Initialization
    tn.write(b"no\r")
    tn.write(b"\r")
    tn.write(b"enable\r")  

    # Change the hostname
    tn.write(b"conf t\r")
    tn.write(f"hostname {router}\r".encode())
    tn.write(b"end\r")

    # Check if ipv6
    #ipv6_present = False
    #for interface in data[router]['interfaces']:
    #    if interface['InterfaceName']!="Loopback0":
    #        if "IPv6" in interface:
    #            ipv6_present = True
    #            break

    # Activate ipv6
    #if ipv6_present:  
    #    tn.write(b"end\r")
    #    tn.write(b"conf t\r")
    #    tn.write(b"ipv6 unicast-routing\r")
    #    tn.write(b"end\r")
    
    # Assign different ip address
    for interface in data[router]['interfaces']:
        interface_name=interface["InterfaceName"]

        # Configure ipv4 address
        if "IPv4" in interface:
            ipv4=interface["IPv4"]
            tn.write(b"end\r")
            tn.write(b"conf t\r")

            # Configuration in an interface
            tn.write(f"int {interface_name}\r".encode())

            # Configure the address
            tn.write(f"ip add {ipv4[0]} {ipv4[1]}\r".encode())

            # No shutdown
            tn.write(b"no shutdown\r")
            tn.write(b"end\r")
        
        # Configure ipv6 address
        #if "IPv6" in interface:
        #    ipv6=interface["IPv6"]
        #    tn.write(b"end\r")
        #    tn.write(b"conf t\r")

            # Configuration in an interface
        #    tn.write(f"int {interface_name}\r".encode())

            # Configure the address
        #    tn.write(f"ipv6 add {ipv6}\r".encode())

            # No shutdown
        #    tn.write(b"no shutdown\r")
        #    tn.write(b"end\r")
        
    # Check if OSPF
    if "OSPF_id" in data[router]:
        ospf_id=data[router]["OSPF_id"]
        tn.write(b"end\r")  
        tn.write(b"conf t\r")

        # OSPFv2 activation
        tn.write(b"router ospf 1\r")
        tn.write(f"router-id {ospf_id}\r".encode())

        # OSPFv3 if ipv6
        #if ipv6_present:
            #tn.write(b"end\r")  
            #tn.write(b"conf t\r")
            #tn.write(b"ipv6 router ospf 2\r")
            #tn.write(f"router-id {ospf_id}\r".encode())

    # Activate OSPF on the interfaces
    for interface in data[router]['interfaces']:
        if "OSPF_area" in interface:
            interface_name=interface["InterfaceName"]
            ospf_area=interface["OSPF_area"]
            tn.write(b"end\r")  
            tn.write(b"conf t\r")

            # Configuration in an interface
            tn.write(f"int {interface_name}\r".encode())

            # Configuration of the ospf area
            tn.write(f"ip ospf 1 area {ospf_area}\r".encode())
            
            # If ipv6 in interface, OSPFv3
            #if "IPv6" in interface:
                #tn.write(f"ipv6 ospf 2 area {ospf_area}\r".encode())
            
            #tn.write(b"end\r")

    # Check OSPF neighbors for ipv4
    if "OSPF_neighboripv4" in data[router]:
        neighbors=data[router]["OSPF_neighboripv4"]
        tn.write(b"end\r")  
        tn.write(b"conf t\r")
        tn.write(b"router ospf 1\r")

        # We set each neighbor
        for neighbor in neighbors:
            tn.write(f"network {neighbor[0]} {neighbor[1]} area {neighbor[2]}\r".encode())

    # Check OSPF Neighbors for ipv6
    #if "OSPF_neighboripv6" in data[router]:
    #    neighbors=data[router]["OSPF_neighboripv6"]
    #    tn.write(b"end\r")  
    #    tn.write(b"conf t\r")
    #    tn.write(b"ipv6 router ospf 2\r")

        # We set each neighbor
    #    for neighbor in neighbors:
    #        tn.write(f"network {neighbor[0]} {neighbor[1]} area {neighbor[2]}\r".encode())
    

    # Check if MBBGP
    if "BGP" in data[router]:
        ass=data[router]["BGP"]["AS"]
        tn.write(b"end\r")  
        tn.write(b"conf t\r")
        tn.write(f"router bgp {ass}\r".encode())
        tn.write(b"no bgp default ipv4-unicast\r")

        # Check if MBGP neighbors
        if "neighbors" in data[router]["BGP"]:
            # Configure MBGP neighbors
            neighbors=data[router]["BGP"]["neighbors"]
            for neighbor in neighbors:
                tn.write(f"neighbor {neighbor['addr']} remote-as {neighbor['AS']}\r".encode())
                tn.write(f"neighbor {neighbor['addr']} update-source Loopback 0\r".encode())
        
        tn.write(b"end\r")  

        # VPN on MBGP

    # Check Express forwarding
    if "ipcef" in data[router]:
        tn.write(b"end\r")  
        tn.write(b"conf t\r")
        tn.write(b"ip cef\r")
        tn.write(b"end\r")

    # Check if MPLS
    for interface in data[router]['interfaces']:
        if "MPLS" in interface:
            interface_name=interface["InterfaceName"]
            tn.write(b"end\r")  
            tn.write(b"conf t\r")

            # Configuration in an interface
            tn.write(f"int {interface_name}\r".encode())

            # Configuration of mpls in the interface
            tn.write(b"mpls ip\r")
            tn.write(b"end\r")
    
    # Check if VRF
    if "VRF" in data[router]:
        for vrf in data[router]["VRF"]:

            # Activate VRF
            vrf_name=vrf["name"]
            vrf_rd=vrf["rd"]
            vrf_import=vrf["rt_import"]
            vrf_export=vrf["rt_export"]

            tn.write(b"end\r")  
            tn.write(b"conf t\r")
            tn.write(f"ip vrf {vrf_name}\r".encode())

            # Configure Route Distinguisher
            tn.write(f"rd {vrf_rd}\r".encode())

            # Configure Route Target in and out
            for rt_in in vrf_import:
                tn.write(f"route-target import {rt_in}\r".encode())
            for rt_out in vrf_export:
                tn.write(f"route-target export {rt_out}\r".encode())
            
            tn.write(b"end\r")


            # Activate VRF on OSPF

            # Activate VRF on BGP

        # Activate VRF on the interfaces
        for interface in data[router]['interfaces']:
            if "VRF" in interface:
                interface_name=interface["InterfaceName"]
                vrf_name=interface["VRF"]
                tn.write(b"end\r")  
                tn.write(b"conf t\r")
                
                # Configuration in an interface
                tn.write(f"int {interface_name}\r".encode())

                # Enable VRF
                tn.write(f"ip vrf forwarding {vrf_name}\r".encode())

                tn.write(b"end")

    # Save configuration
    tn.write(b"end\r")
    tn.write(b"write")
    tn.write(b"\r")

    print("Ending")
    time.sleep(5)








    
    