import sys

def showHelp():
    # print commands help here
    print("")

def networkInit():
    # we will init the whole network here, maybe with a config file template?
    print("")

if __name__ == '__main__':
    if (len(sys.argv) == 0):
        showHelp()
    elif (len(sys.argv) == 1 and sys.argv[0] == "help"):
        showHelp()
    else:
        if (sys.argv[0] == "init"):
            networkInit()
        elif (sys.argv[0] == "addCustomer"):
            # add customer
            print("")