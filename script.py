import sys
import requests
import json
import telnetlib
import time

# The address and port of the GNS3 server

project_id = ""

def serverQuery(endpoint, type="get", data1={}, jsonPayload=None):
    global project_id
    address = "http://localhost:3080"
    url = ""
    if (project_id != ""):
        url = f"{address}/v2/projects/{project_id}/{endpoint}"
    else:
        url = f"{address}/v2/{endpoint}"
    headers = {'Content-type': 'application/json'}
    if (type == "get"):
        return requests.get(url, headers=headers)
    elif (type == "post"):
        if jsonPayload != None:
            return requests.post(url, json=jsonPayload, headers=headers)
        return requests.post(url, data=json.dumps(data1), headers=headers)

def showHelp():
    # print commands help here
    print("script.py help - Show commands help")
    print("script.py init - Initialize a new GNS3 project based on the config.json file")
    print("script.py addCustomer <pe> <name> <ipAddressCE> <ipAddressPE> <interfaceName1> <interfaceName2> <asn> <vrf> [<rd> <rt>] - Add a new CE to a PE in an existing project.")

def get_nodes(project_id):
    return serverQuery(f"nodes").json()

def getRouterByName(name):
    global project_id
    try:
        if project_id == "":
            # Retrieving the project_id of the opened project
            project_id = list(filter(lambda p: p['status'] == 'opened', serverQuery("projects").json()))[0]['project_id']
    except requests.exceptions.ConnectionError as e:
        print("Error: Impossible to connect to GNS3 server.\n")
        exit(1)
    except IndexError:
        print("You have to select a correct GNS3 project.")
        exit(1)

    for node in get_nodes(project_id):
        if (node['node_type'] == 'dynamips' or node['symbol'] == ':/symbols/classic/router.svg') and node['name'] == name:
            return node

    return None

if __name__ == '__main__':
    if (len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == "help")):
        showHelp()
    else:
        if (sys.argv[1] == "init"):
            import nas
        elif (sys.argv[1] == "addCustomer"):
            if (len(sys.argv) < 10 or len(sys.argv) > 12):
                print("Invalid command: addCustomer <pe> <name> <ipAddressCE> <ipAddressPE> <interfaceName1> <interfaceName2> <asn> <vrf> [<rd> <rt>]")
            else:
                toAttachTo = sys.argv[2]
                customerName = sys.argv[3]
                ipAddress = sys.argv[4]
                ipAddress2 = sys.argv[5]
                interfaceName1 = sys.argv[6]
                interfaceName2 = sys.argv[7]
                try:
                    asn = int(sys.argv[8])
                except ValueError:
                    print("Invalid ASN.")
                    exit(1)
                vrf = sys.argv[9]
                rd = None
                rt = None
                newVrf = len(sys.argv) > 10
                if newVrf:
                    rd = sys.argv[10]
                    rt = sys.argv[10]
                # Retrieving the targeted PE node
                print("Get PE router")
                toAttachTo = getRouterByName(toAttachTo)
                ports = {}
                ports[toAttachTo["node_id"]] = toAttachTo["console"]
                portsDest = toAttachTo["ports"]
                # Check if the interface is not already connected to something
                print("Get links")
                links = serverQuery("links").json()
                exist = False
                for l in links:
                    for node in l["nodes"]:
                        for p in portsDest:
                            if (node["node_id"] == toAttachTo["node_id"]):
                                if((p["name"] == interfaceName2 or p["short_name"] == interfaceName2) and p["adapter_number"] == node["adapter_number"]):
                                    exist = True
                                    break
                if exist:
                    print(f"Target router interface {interfaceName2} is already connected to something else.")
                    exit(1)
                
                data = {
                    "symbol": ":/symbols/router.svg",
                    "name": customerName,
                    "properties": {"platform": "c7200", "nvram": 512, "image": "c7200-advipservicesk9-mz.152-4.S5.image", "ram": 512, "slot0": "IO-FE","slot1": "PA-GE", "slot2": "PA-GE" , "slot3":"PA-GE", "system_id": "FTX0945W0MY"},
                    "node_type": "dynamips",
                    "compute_id":"local"
                }

                print("Create new router")
                response = serverQuery("nodes", "post", data)
                new_node_id = ""
                portsFrom = {}
                if response.status_code == 201:
                    print(f"Node '{customerName}' added to project '{project_id}'.")
                    new_node_id = response.json()["node_id"]
                else:
                    print(f"Error adding node to project: {response.status_code} {response.reason}")
                    print(response.text)
                    exit(1)

                newRouter = getRouterByName(customerName)
                portsFrom = newRouter["ports"]
                adapter1 = -1
                adapter2 = -1
                for p in portsFrom:
                    if(p["name"] == interfaceName1 or p["short_name"] == interfaceName1):
                        adapter1 = p["adapter_number"]
                for p in portsDest:
                     if(p["name"] == interfaceName2 or p["short_name"] == interfaceName2):
                        adapter2 = p["adapter_number"]
                
                if (adapter1 == -1 or adapter2 == -1):
                    print("Unable to add the link: adapter1 or adapter2 not found.")
                    exit(1)
                
                payload = {
                    "nodes": [
                        {
                            "node_id": new_node_id,
                            "adapter_number": adapter1,
                            "port_number": 0
                        },
                        {
                            "node_id": toAttachTo["node_id"],
                            "adapter_number": adapter2,
                            "port_number": 0
                        }
                    ]
                }
                print("Create links")
                response = serverQuery("links", "post", jsonPayload=payload)

                if response.status_code == 201:
                    print("Link created successfully")
                else:
                    print("Failed to create link : "+response.text)
                    exit(1)
                
                print("Starting the new router")
                response = serverQuery(f"nodes/{new_node_id}/start", "post")
                ports[new_node_id] = newRouter["console"]
                if response.status_code == 200:
                    print("New node successfully started.")
                else:
                    print("Failed to start new node : " + response.text)
                    exit(1)
                time.sleep(10)

                with telnetlib.Telnet("127.0.0.1", ports[new_node_id]) as tn:
                    time.sleep(1)
                    print("Opened telnet session for the new node")
                    
                    # Config of the new node

                    tn.write(b"no\r")
                    tn.write(b"\r")
                    time.sleep(1)
                    tn.write(b"enable\r")  
                    tn.write(b"conf t\r")
                    tn.write(f"hostname {customerName}\r".encode())
                    tn.write(b"ip cef\r")
                    tn.write(b"end\r")
                    time.sleep(0.5)

                    tn.write(b"conf t\r")
                    
                    tn.write(f"inter {interfaceName1}\r".encode())
                    tn.write(f"ip address {ipAddress} 255.255.255.0\r".encode())
                    tn.write(b"no shutdown\r")
                    tn.write(b"exit\r")
                    time.sleep(0.5)

                    tn.write(f"router bgp {asn}\r".encode())
                    tn.write(b"redistribute connected\r")
                    tn.write(f"neighbor {ipAddress2} remote-as 101\r".encode())
                    tn.write(b"exit\r")
                    time.sleep(0.5)
                
                    tn.write(b"end\r")
                    tn.write(b"write\r")
                    tn.write(b"\r")
                    time.sleep(1)
                    
                    print("Next Router")

                    time.sleep(5)

                
                # Config of PE
                with telnetlib.Telnet("127.0.0.1", ports[toAttachTo["node_id"]]) as tn:
                    time.sleep(1)
                    print("Opened telnet session for the PE node")

                    tn.write(b"\r")
                    tn.write(b"enable\r")
                    time.sleep(0.5)
                    if newVrf:
                        tn.write(b"conf t\r")
                        tn.write(f"vrf definition {vrf}\r".encode())
                        tn.write(f"rd {rd}\r".encode())
                        tn.write(f"route-target export {rt}\r".encode())
                        tn.write(f"route-target import {rt}\r".encode())
                        tn.write(b"address-family ipv4\r")
                        tn.write(b"end\r")

                    time.sleep(0.5)

                    tn.write(b"conf t\r")
                    tn.write(f"inter {interfaceName2}\r".encode())
                    tn.write(f"ip address {ipAddress2} 255.255.255.0\r".encode())
                    tn.write(f"vrf forwarding {vrf}\r".encode())
                    tn.write(f"ip address {ipAddress2} 255.255.255.0\r".encode())
                    tn.write(b"no shutdown\r")
                    tn.write(b"exit\r")
                    time.sleep(0.5)

                    tn.write(b"router bgp 101\r")
                    tn.write(f"address-family ipv4 vrf {vrf}\r".encode())
                    tn.write(f"neighbor {ipAddress} remote-as {asn}\r".encode())
                    tn.write(f"neighbor {ipAddress} activate\r".encode())
                    tn.write(b"exit\r")
                    time.sleep(0.5)   
                
                    tn.write(b"end\r")
                    tn.write(b"write\r")
                    tn.write(b"\r")
                    time.sleep(1)
                print("End")
        else:
            print("Unknown command.")
            showHelp()
                
                