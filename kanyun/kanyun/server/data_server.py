# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Sina Corporation
# All Rights Reserved.
# Author: YuWei Peng <pengyuwei@gmail.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys
import time
import signal
import traceback
import logging
import ConfigParser
import json
import zmq
from kanyun.common.const import *
from kanyun.common.app import *

living_status = dict()

app = App(conf="kanyun.conf", log="/tmp/kanyun-server.log")
logger = app.get_logger()
tool = None

class LivingStatus():

    def __init__(self, worker_id='1'):
        self.dietv = 2 * 60  # default die threshold value: 2min
        self.alert_interval = 60 # one alert every 60 seconds
        self.update()
        self.alerted = False
        self.worker_id = worker_id
        self.previous_alert_time = 0
        
    def update(self):
        self.update_time = time.time()
        self.alerted = False
        
    def is_die(self):
        return time.time() - self.update_time > self.dietv
        
    def on_die(self):
        ret = 0
        if not self.alerted:
            self.alert_once()
            ret += 1
            
        # each minutes less than once
        if time.time() - self.previous_alert_time > self.alert_interval: 
            self.alert()
            ret += 1
            
        return ret
        
    ####### private ########
    def alert_once(self):
        # TODO: dispose timeout worker here 
        print '*' * 400
        print '[WARNING]worker', self.worker_id, "is dead. email sendto admin"
        print '*' * 400
        self.alerted = True
        
    def alert(self):
        print '\033[0;31m[WARNING]\033[0mworker', self.worker_id, "is dead. Total=", len(living_status)
        self.previous_alert_time = time.time()


def autotask_heartbeat():
    global living_status
    for worker_id, ls in living_status.iteritems():
        if ls.is_die():
            ls.on_die()


def clean_die_warning():
    global config
    global living_status
    
    new_list = dict()
    i = 0
    for worker_id, ls in living_status.iteritems():
        if not ls.is_die():
            new_list[worker_id] = ls
        else:
            i = i + 1

    living_status = new_list
    print i, "workers cleaned:"
    
    
def list_workers():
    global living_status
    print "-"*30, "list_workers", "-" * 30
    for worker_id, ls in living_status.iteritems():
        print 'worker', worker_id, "update @", ls.update_time
    print len(living_status), "workers."
    
    
def plugin_heartbeat(app, db, cache, data):
    if data is None or len(data) < 3:
        return
    worker_id, update_time, status = data
    if living_status.has_key(worker_id):
        living_status[worker_id].update()
    else:
        living_status[worker_id] = LivingStatus(worker_id)
    if 0 == status:
        del living_status[worker_id]


def plugin_decoder_agent(app=None, db=None, cache=None, data=None):
    if data is None or len(data) <= 0:
        return
    def formate_vm_info(info):
        formated_info=[];
        for instance in info:
            ## create a list with length 10
            data=range(10);
            data[0]=instance;
#            data[9]=tool.get_uuid_by_novaid(instance);
            ## get uuid directly from worker
            instance_info=info[instance];
            data[9]=str(instance_info[-1]);
           # print 'novaid(%s)--->uuid(%s)'%(data[0],data[9]);
            nic_in_info="";
            nic_out_info="";
            blk_read_info="";
            blk_write_info="";
            for item_info in instance_info:
                if item_info[0]==unicode("cpu"):
                    cpu_usage=str(item_info[2][1]);
                    ##print 'cpu_usage=',cpu_usage;
                    data[1]=cpu_usage[0:5];
                    data[8]=timestamp=str(int(item_info[2][0]));
                elif item_info[0]==unicode("mem"):
                    data[2]=mem_free=str(item_info[2][2]);
                    data[3]=mem_max=str(item_info[2][1]);
                elif item_info[0]==unicode("nic"):
                    vnet_in=item_info[1]+":"+str(item_info[2][1]);
                    vnet_out=item_info[1]+":"+str(item_info[2][2]);
                    if nic_in_info is "" or nic_out_info is "":
                        nic_in_info=vnet_in;
                        nic_out_info=vnet_out;
                    else:
                        nic_in_info=nic_in_info+"#"+vnet_in;
                        nic_out_info=nic_out_info+"#"+vnet_out;
                elif item_info[0]==unicode("blk"):
                    vd_read=item_info[1]+":"+str(item_info[2][1]);
                    vd_write=item_info[1]+":"+str(item_info[2][2]);
                    if blk_read_info is "" or blk_write_info is "":
                        blk_read_info=vd_read;
                        blk_write_info=vd_write;
                    else:
                        blk_read_info=blk_read_info+"#"+vd_read;
                        blk_write_info=blk_write_info+"#"+vd_write;
            data[4]=nic_in_info;
            data[5]=nic_out_info;
            data[6]=blk_read_info;
            data[7]=blk_write_info; 
            formated_info.append(data);
        return formated_info;
##################################
    print "-"*30, "vminfo", "-" * 30
    pass_time = time.time()
    formated_info=formate_vm_info(data);
    for info in formated_info:
 	print info
        db.insert_monitor_data(info);
        cache.push_vm_info(info);
    print 'spend \033[1;33m%f\033[0m seconds' % (time.time() - pass_time)
    
def SignalHandler(sig, id):
    global running
    
    if sig == signal.SIGUSR1:
        list_workers()
    elif sig == signal.SIGUSR2:
        clean_die_warning()
    elif sig == signal.SIGINT:
        running = False


def register_signal():
    signal.signal(signal.SIGUSR1, SignalHandler)
    signal.signal(signal.SIGUSR2, SignalHandler)
    signal.signal(signal.SIGINT, SignalHandler)
   
