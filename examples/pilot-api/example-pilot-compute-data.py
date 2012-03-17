import sys
import os
import time
import logging
logging.basicConfig(level=logging.DEBUG)

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from pilot import PilotComputeService, PilotDataService, ComputeDataService, State

 
if __name__ == "__main__":      
    
    pilot_compute_service = PilotComputeService()

    # create pilot job service and initiate a pilot job
    pilot_compute_description = {
                             "service_url": 'fork://localhost',
                             "number_of_processes": 1,                             
                             "working_directory": "/tmp/pilot-compute/",
                             'affinity_datacenter_label': "eu-de-south",              
                             'affinity_machine_label': "mymachine-1" 
                            }
    
    pilotjob = pilot_compute_service.create_pilot(pilot_compute_description=pilot_compute_description)
    
    
    # create pilot data service (factory for data pilots (physical, distributed storage))
    # and pilot data
    pilot_data_service = PilotDataService()
    pilot_data_description={
                                "service_url": "ssh://localhost/tmp/pilot-data/",
                                "size": 100,   
                                "affinity_datacenter_label": "eu-de-south",              
                                "affinity_machine_label": "mymachine-1"                              
                             }
    ps = pilot_data_service.create_pilot(pilot_data_description=pilot_data_description)
     
    compute_data_service = ComputeDataService()
    compute_data_service.add_pilot_compute_service(pilot_compute_service)
    compute_data_service.add_pilot_data_service(pilot_data_service)
    
    # Create Data Unit Description
    base_dir = "/Users/luckow/workspace-saga/applications/pilot-store/test/data1"
    url_list = os.listdir(base_dir)
    # make absolute paths
    absolute_url_list = [os.path.join(base_dir, i) for i in url_list]
    data_unit_description = {
                              "file_urls":absolute_url_list,
                              "affinity_datacenter_label": "eu-de-south",              
                              "affinity_machine_label": "mymachine-1"
                             }    
      
    
    # submit pilot data to a pilot store    
    data_unit = compute_data_service.submit_data_unit(data_unit_description)
    data_unit.wait()
    logging.debug("Pilot Data URL: %s Description: \n%s"%(data_unit, str(pilot_data_description)))
    
    
    # start work unit
    compute_unit_description = {
            "executable": "/bin/sleep",
            "arguments": ["100"],
            "total_core_count": 1,
            "number_of_processes": 1,
            "working_directory": data_unit.url,
            #"working_directory": os.getcwd(),
            "output": "stdout.txt",
            "error": "stderr.txt",   
            "affinity_datacenter_label": "eu-de-south",              
            "affinity_machine_label": "mymachine-1" 
    }    
    compute_unit = compute_data_service.submit_compute_unit(compute_unit_description)
    logging.debug("Finished setup of PSS and PDS. Waiting for scheduling of PD")
    compute_data_service.wait()
    #while data_unit.get_state() != State.Done and compute_unit != State.Done:
    #    logging.debug("Check state")
    #    state_data_unit = data_unit.get_state()
    #    state_compute_unit = compute_unit.get_state()
    #    print "PJS State %s" % pilot_compute_service
    #    print "DU: %s State: %s"%(data_unit, state_data_unit)
    #    print "CU: %s State: %s"%(compute_unit, state_compute_unit)
    #    if state_compute_unit==State.Done and state_data_unit==State.Running:
    #        break
    #    time.sleep(2)  
    
    logging.debug("Terminate Pilot Compute/Data Service")
    compute_data_service.cancel()
    pilot_data_service.cancel()
    pilot_compute_service.cancel()