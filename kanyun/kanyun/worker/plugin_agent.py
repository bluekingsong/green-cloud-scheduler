# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import datetime
import time
from xml.etree import ElementTree

import libvirt

# add by pyw
class Diff():
    """TODO:same as class Statistics() in server, merge."""
    def __init__(self):
        self.first = True
        self.count = 0
        self.previous = 0.0
        self.diff = 0.0
        self.previous_time = time.time()
        self.time_pass = 0
        
    def update(self, value):
        self.count += 1
        if self.first:
            self.first = False
            self.diff = 0.0
            self.previous = value
            self.time_pass = time.time() - self.previous_time
            self.previous_time = time.time()
            return

        self.diff = value - self.previous
        self.previous = value
        self.time_pass = time.time() - self.previous_time
        self.previous_time = time.time()
            
    def get_diff(self):
        return self.diff
        
    def get_time_pass(self):
        return self.time_pass


class LibvirtMonitor(object):

    def __init__(self, uri='qemu:///system'):
        self.conn = libvirt.openReadOnly(uri)
        self.hostname = self.conn.getHostname()
        self.diffs = dict()
	self.uri = uri
        """
        (model, memory_kb, cpus, mhz, nodes,
         sockets, cores, threads) = conn.getInfo()
        """
    def __get_pid_of_instances(self):
        from os import popen;
        cmd='''ps ax|fgrep '/usr/bin/kvm'|fgrep -v 'fgrep'|awk '{
    pid=$1;
    for(i=2;i<NF;i++){
        if($i=="-name" && match($(i+1),/instance-[a-z0-9]+/))
	    instance=$(i+1);
    }
#    print $0;
    if(instance!="")
        print pid"\t"instance;    
}' '''
        pid_map=dict();
        for line in popen(cmd).readlines():
            paras=line[:-1].split("\t");
            pid=paras[0];
            instance_id=paras[1];
            pid_map[instance_id]=pid;
        return pid_map;

    def collect_info(self):
        infos_by_dom_name = dict()
	try:
	        domainIDList=self.conn.listDomainsID();
	except Exception, e:
		self.conn = libvirt.openReadOnly(self.uri)
	        domainIDList=self.conn.listDomainsID();
				
        pid_map=self.__get_pid_of_instances();
        for dom_id in domainIDList:
            dom_conn = self.conn.lookupByID(dom_id)
            dom_key = dom_conn.name()
            dom_xml = dom_conn.XMLDesc(0)
            infos = list()
            # get domain's cpu, memory info
            infos.extend(self._collect_cpu_mem_info(dom_id,pid_map[dom_key],dom_conn))
            # get domain's network info
            nic_devs = self.get_xml_nodes(dom_xml, './devices/interface')
            if not nic_devs:
                # TODO(lzyeval): handle exception
                pass
            for nic_dev in nic_devs:
                infos.extend(self._collect_nic_dev_info(dom_conn, nic_dev))
            # get domain's stroage info
            blk_devs = self.get_xml_nodes(dom_xml, './devices/disk')
            if not blk_devs:
                # TODO(lzyeval): handle exception
                pass
            for blk_dev in blk_devs:
                infos.extend(self._collect_blk_dev_info(dom_conn, blk_dev))
            infos.append(dom_conn.UUIDString());
            infos_by_dom_name[dom_key] = infos
        return infos_by_dom_name

    @staticmethod
    def get_utc_sec():
        return time.time()

    @staticmethod
    def get_xml_nodes(dom_xml, path):
        disks = list()
        doc = None
        try:
            doc = ElementTree.fromstring(dom_xml)
        except Exception:
            return disks
        ret = doc.findall(path)
        for node in ret:
            devdst = None
            for child in list(node):#.children:
                if child.tag == 'target':
                    devdst = child.attrib['dev']
            if devdst is None:
                continue
            disks.append(devdst)
        return disks

    def _collect_cpu_mem_info(self, dom_id,pid,dom_conn):
        """Returns tuple of
           (total, utc_time_sec, dom_cpu_time, dom_max_mem_db, dom_memory_kb)
        """
        (dom_run_state, dom_max_mem_kb, dom_memory_kb,
         dom_nr_virt_cpu, dom_cpu_time) = dom_conn.info()
        from os import popen;
        cmd=''' awk '/VmRSS:/ { print $2;}' /proc/'''+pid+'/status';
        mem_used=int(popen(cmd).readlines()[0]);
        mem_free=dom_max_mem_kb-mem_used;
        if not dom_run_state:
            pass
        timestamp = self.get_utc_sec()
        
        if not self.diffs.has_key(dom_id):
            self.diffs[dom_id] = Diff()
        self.diffs[dom_id].update(dom_cpu_time)
        cpu = 100.0 * self.diffs[dom_id].get_diff() / (self.diffs[dom_id].get_time_pass() * 1 * 1e9)
        #print "dom_id:",dom_id, 'cpu:', cpu, '%, cpu_time:', dom_cpu_time, "mem:", mem_free, "/", dom_max_mem_kb
        return [('cpu', 'total', (timestamp, cpu)),
                ('mem', 'total', (timestamp, dom_max_mem_kb, mem_free))]

    def _collect_nic_dev_info(self, dom_conn, nic_dev):
        """Returns tuple of
           (nic_dev, utc_time_sec, rx_bytes, tx_bytes)
        """
        (rx_bytes, rx_packets, rx_errs, rx_drop, tx_bytes,
         tx_packets, tx_errs, tx_drop) = dom_conn.interfaceStats(nic_dev)
        timestamp = self.get_utc_sec()
        #print nic_dev, " rx=", rx_bytes, "tx=", tx_bytes
        return [('nic', nic_dev, (timestamp, rx_bytes, tx_bytes))]

    def _collect_blk_dev_info(self, dom_conn, blk_dev):
        """Returns tuple of
           (blk_dev, utc_time_sec, rx_bytes, tx_bytes)
        """
        rd_req, rd_bytes, wr_req, wr_bytes, errs = dom_conn.blockStats(blk_dev)
        timestamp = self.get_utc_sec()
        #print blk_dev, " r=", rd_bytes, "w=", wr_bytes
        return [('blk', blk_dev, (timestamp, rd_bytes, wr_bytes))]

agent = None
def plugin_call():
    global agent
    if agent is None:
        agent = LibvirtMonitor()
    ret = agent.collect_info()
    return ret
    
    
