import sys
import requests
import json
import nas
import telnetlib
import time

# The address and port of the GNS3 server

project_id = ""

def serverQuery(endpoint, type="get", data1={}):
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
        return requests.post(url, data=json.dumps(data1), headers=headers)

def showHelp():
    # print commands help here
    print("")

def get_nodes(project_id):
    return serverQuery(f"nodes").json()

def getRouterByName(name):
    global project_id
    try:
        # Prepare the data for the POST request
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
            nas.start()
        elif (sys.argv[1] == "addCustomer"):
            # add customer <pe> <name> <asn> <flux vpn>
            if (len(sys.argv) != 9):
                print("Invalid command: addCustomer <pe> <name> <ipAddress> <interfaceName1> <interfaceName2> <asn> <flux vpn>")
            else:
                toAttachTo = sys.argv[2]
                customerName = sys.argv[3]
                ipAddress = sys.argv[4]
                interfaceName1 = sys.argv[5]
                interfaceName2 = sys.argv[6]
                try:
                    asn = int(sys.argv[7])
                except ValueError:
                    print("Invalid ASN.")
                    exit(1)
                fluxVPN = sys.argv[8]
                # récupère la topologie GNS3, les routeurs etc...
                toAttachTo = getRouterByName(toAttachTo)
                ports = {}
                ports[toAttachTo["node_id"]] = toAttachTo["console"]
                portsDest = toAttachTo["ports"]
                # check si l'interface existe n'est pas déjà connecté
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
                    print("L'interface du router cible est déjà occupé.")
                    exit(1)
                
                data = {
                    "symbol": ":/symbols/router.svg",
                    "name": customerName,
                    "properties": {"platform": "c7200", "nvram": 512, "image": "c7200-advipservicesk9-mz.152-4.S5.image", "ram": 512, "slot0": "IO-FE","slot1": "PA-GE", "slot2": "PA-GE" , "slot3":"PA-GE", "system_id": "FTX0945W0MY"},
                    "node_type": "dynamips",
                    "compute_id":"local"
                }
                
                response = serverQuery("nodes", "post", data)
                new_node_id = ""
                portsFrom = {}
                newRouter = None
                if response.status_code == 201:
                    print(f"Node '{customerName}' added to project '{project_id}'.")
                    new_node_id = response.json()["node_id"]
                    newRouter = getRouterByName(customerName)
                    portsFrom = newRouter["ports"]
                else:
                    print(f"Error adding node to project: {response.status_code} {response.reason}")
                    print(response.text)

                adapter1 = -1
                adapter2 = -1
                for p in portsFrom:
                    if(p["name"] == interfaceName1 or p["short_name"] == interfaceName1):
                        adapter1 = p["adapter_number"]
                for p in portsDest:
                     if(p["name"] == interfaceName2 or p["short_name"] == interfaceName2):
                        adapter2 = p["adapter_number"]
                
                if (adapter1 == -1 or adapter2 == -1):
                    print("Impossible d'ajouter le lien : adapter1 ou adapter2 introuvable.")
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
                response = serverQuery("links", "post", payload)

                if response.status_code == 201:
                    print("Link created successfully")
                else:
                    print("Failed to create link : "+response.text)
                    exit(1)
                
                
                response = serverQuery(f"nodes/{new_node_id}/start", "post")
                ports[new_node_id] = newRouter["console"]
                if response.status_code == 201:
                    print("New node successfully started.")
                else:
                    print("Failed to start new node : " + response.text)
                    exit(1)
                time.sleep(3)

                tn = telnetlib.Telnet("127.0.0.1", ports[new_node_id])
                print("Opened telnet session for the new node")

                 # Initialization
                tn.write(b"no\r")
                tn.write(b"\r")
                tn.write(b"enable\r")  

                # Change the hostname
                tn.write(b"conf t\r")
                tn.write(f"hostname {customerName}\r".encode())
                tn.write(b"ip cef\r")
                tn.write(b"end\r")

                tn.write(b"conf t\r")
                
                tn.write(f"inter {interfaceName1}\r".encode())
                tn.write(f"ip address {ipAddress} 255.255.255.0\r".encode())
                tn.write(b"no shutdown\r")
                tn.write(b"exit\r")

                tn.write(f"router bgp {asn}")
                    
            
                tn.write(b"end\r")
                


                
                
                