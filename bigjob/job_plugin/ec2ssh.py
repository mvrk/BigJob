#!/usr/bin/env python

from bigjob import logger
import os
import uuid
import time

from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo

import bliss.saga as saga
from pilot.api.api import PilotError

###############################################################################
# EC2 General
PLACEMENT_GROUP=None
SECURITY_GROUP="default"

# VM/Image specific configurations
# Recommendation Ubuntu > 1104
# apt-get install gcc python-all-dev git subversion vim
# EC2_AMI_ID="ami-c7943cae" #  ami-82fa58eb official Amazon Ubuntu 12.04 LTS (requires dev tools installation)
# EC2_AMI_ID="ami-d7f742be"
# EC2_USERNAME="ubuntu"
# EC2_KEYNAME="lsu-keypair"
# EC2_KEYNAME="MyKey"

# Authentication
# Please use ~/.boto file to configure your security credentials (if possible)
# see http://boto.readthedocs.org/en/latest/boto_config_tut.html
# 
# [Credentials]
# aws_access_key_id = <your access key>
# aws_secret_access_key = <your secret key>
#
# Alternatively you can use these two variables
AWS_ACCESS_KEY_ID=None
AWS_SECRET_ACCESS_KEY=None




class State:
    PENDING="pending"
    RUNNING="running"
    
    
class Service(object):
    """ Plugin for Amazon EC2 and EUCA
    
        Manages endpoint in the form of:
        
            ec2+ssh://<EC2 Endpoint>
            euca+ssh://<EUCA Endpoint>
    """

    def __init__(self, resource_url, pilot_compute_description=None):
        """Constructor"""
        self.resource_url = resource_url
        self.pilot_compute_description = pilot_compute_description
            
    
    def create_job(self, job_description):
        j = Job(job_description, self.resource_url, self.pilot_compute_description)
        return j
            
    
    def __del__(self):
        pass
    
    
    

class Job(object):
    """ Plugin for Amazon EC2 
    
        Starts VM and executes BJ agent on this VM    
        
        
        Eucalyptus on FutureGrid uses a self-signed certificate, which 1) needs to be added to boto configuration
        or 2) certificate validation needs to be disabled.
    """

    def __init__(self, job_description, resource_url, pilot_compute_description):
        
        self.job_description = job_description
        self.resource_url = saga.Url(resource_url)
        self.pilot_compute_description = pilot_compute_description
        
        self.id="bigjob-" + str(uuid.uuid1())
        self.network_ip=None
        
        self.ec2_conn=None
        if self.resource_url.scheme == "euca+ssh":
            region = RegionInfo(name="eucalyptus", endpoint=self.resource_url.host)
            logger.debug("Access Key: %s Secret: %s"%(self.pilot_compute_description["access_key_id"],
                                                      self.pilot_compute_description["secret_access_key"]))
            self.ec2_conn = EC2Connection(aws_access_key_id=self.pilot_compute_description["access_key_id"],
                                          aws_secret_access_key=self.pilot_compute_description["secret_access_key"], 
                                          region=region,
                                          port=8773,
                                          path="/services/Eucalyptus")
        else:
            self.ec2_conn = EC2Connection(aws_access_key_id=self.pilot_compute_description["access_key_id"], 
                                          aws_secret_access_key=self.pilot_compute_description["secret_access_key"])
        self.instance = None
        
        
    def run(self):
        """ Start VM and start BJ agent via SSH on VM """
        
        """ Map fields of Pilot description to EC2 API
            { "vm_id":"ami-d7f742be",
              "vm_ssh_username":"ubuntu",
              "vm_ssh_keyname":"MyKey",
              "vm_ssh_keyfile":"<path>",
              "vm_type":"t1.micro",
              "access_key_id":"xxx",
              "secret_access_key":"xxx"
            }
        """    
            
        reservation = self.ec2_conn.run_instances(self.pilot_compute_description["vm_id"],
                                    key_name=self.pilot_compute_description["vm_ssh_keyname"],
                                    instance_type=self.pilot_compute_description["vm_type"],
                                    security_groups=[SECURITY_GROUP])
                
        self.instance = reservation.instances[0]
        self.instance_id = self.instance.id
        logger.debug("Started EC2 instance: %s"%self.instance_id)
        if self.resource_url.scheme != "euca+ssh":
            self.ec2_conn.create_tags([self.instance_id], {"Name": self.id})
        self.wait_for_running()
        
        self.network_ip = self.instance.ip_address 
        url = "ssh://" + str(self.network_ip)
        logger.debug("Connect to: %s"%(url))
        js = saga.job.Service(url)
        
        # Submit job
        ctx = saga.Context()
        ctx.type = saga.Context.SSH
        ctx.userid = self.pilot_compute_description["vm_ssh_username"]
        ctx.userkey = self.pilot_compute_description["vm_ssh_keyfile"]
        js.session.contexts.append(ctx)

        job = js.create_job(self.job_description)
        trials=0
        while trials < 3:
            try:
                print ("Attempt: %d, submit pilot job to: %s "%(trials,str(url)))
                job.run()
                break
            except:
                trials = trials + 1 
                time.sleep(7)
                
        print "Job State : %s" % (job.get_state()) 
        
        

    def wait_for_running(self):
        while self.get_state()!=State.RUNNING:
            time.sleep(5)
        
    
    def get_state(self):
        self.instance.update()
        result=self.instance.state
        return result
    
    
    def cancel(self):
        self.instance.terminate()
        
        
    ###########################################################################
    # private methods
    
 
     
if __name__ == "__main__":
    ec2_service = Service("ec2+ssh://aws.amazon.com")
    j = ec2_service.create_job("blas")
    j.run()
    print j.get_state()
