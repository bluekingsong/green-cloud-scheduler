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
import iso8601
import types
import json
import logging
import traceback
import ConfigParser
import zmq
from collections import OrderedDict
from kanyun.common.const import *
from kanyun.common.buffer import HallBuffer
#from kanyun.database.cassadb import CassaDb
from kanyun.database.mysqldb import MysqlDb;

"""
Save the vm's system info data to db.

protocol:
    http://wiki.sinaapp.com/doku.php?id=monitoring
[u'S', u'instance-000001@pyw.novalocal', u'cpu', u'total', 0, 5, 1332897600, 0]
"""

class Statistics():

    def __init__(self):
        self.clean()
        
    def clean(self):
        self.first = True
        self.count = 0
        self.sum = 0.0
        self.min = 0.0
        self.max = 0.0
        self.previous = 0.0
        self.diff = 0.0
        
    def update(self, value):
        self.count += 1
        self.sum += value
        if self.first:
            self.first = False
            self.previous = value
            self.max = value
            self.min = value
            return
            
        if value > self.previous:
            self.max = value
        elif value < self.previous:
            self.min = value
        self.diff = value - self.previous
        self.previous = value
        
    def get_value(self, w):
        if w == 'avg' or w == STATISTIC.AVERAGE:
            return self.get_agerage()
        elif w == 'min' or w == STATISTIC.MINIMUM:
            return self.get_min()
        elif w == 'max' or w == STATISTIC.MAXIMUM:
            return self.get_max()
        elif w == 'sum' or w == STATISTIC.SUM:
            return self.get_sum()
        elif w == 'sam' or w == STATISTIC.SAMPLES:
            return self.get_samples()
        else:
            print 'error:', w
            return 0
            
    def get_diff(self):
        return self.diff
        
    def get_agerage(self):
        if self.count == 0:
            return 0
        else:
            return self.sum / self.count
    def get_sum(self):
        return self.sum
        
    def get_max(self):
        return self.max
        
    def get_min(self):
        return self.min
        
    def get_samples(self):
        # TODO
        return 0;


class ApiServer():

    def __init__(self, 
                 mysql_cfg={}, 
                 log_file="/tmp/api-server.log",
                 log_level=logging.NOTSET):
        # cassandra database object
        self.db = None
        self.mysql_cfg=mysql_cfg;
        self.buf = HallBuffer()
        self.logger = logging.getLogger()
        handler = logging.FileHandler(log_file)
        self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        
    def get_db(self):
        if self.db is None:
             self.db=MysqlDb(self.mysql_cfg);
#            self.db = CassaDb('data', self.db_host)
        return self.db
   
### change by lanjinsong 2012-08-10
    def get_instances_list(self,start_time=time.strftime("%Y-%m-%d %T",time.gmtime(0))):
        """ show all instances in the databases"""
        db=self.get_db();
        return self.db.get_instances_in_cache();
        #result_set=db.get_all_instances(start_time);
        #print type(result_set),'result_set=',result_set;
        #instances=[];
        #for row in result_set:
        #    instances.append(row[0]);
        #return instances;

    def __get_instances_list(self, cf_str):
        if not isinstance(cf_str, unicode):
            print 'param types error'
            return None
        ret = list()
        limit = 20000
        time_to = int(time.time())
        time_from = time_to - 24 * 60 * 60
        db = self.get_db()

        rs = db.get_range2(cf_str, row_count=20)
        return list(rs)
        if not rs is None:
            print rs
            for i in rs:
                ret.append(i[0])

        return ret
 
    def __get_instances_list(self, cf_str):
        if not isinstance(cf_str, unicode):
            print 'param types error'
            return None
        ret = list()
        limit = 20000
        time_to = int(time.time())
        time_from = time_to - 24 * 60 * 60
        db = self.get_db()
        
        rs = db.get_range2(cf_str, row_count=20)
        return list(rs)
        if not rs is None:
            print rs
            for i in rs:
                ret.append(i[0])
        
        return ret
        
    def get_by_instance_id(self, row_id, cf_str):
        if not isinstance(row_id, unicode) \
            or not isinstance(cf_str, unicode):
            print 'param types error'
            return None, 0, True
        db = self.get_db()
        rs = db.getbykey(cf_str, row_id)
        count = 0 if rs is None else len(rs)
        
        return rs, count, False if (count == 20000) else True
        
    ##  change by lanjinsong
    def query_usage_report(self,args,**kwargs):
        """ query usage report modified by lanjinsong to use MySQL"""
        instance_id=str(args['instance_id']);
        start_time=args['start_time'] if ('start_time' in args) else time.strftime("%Y-%m-%d %T",time.gmtime(0));
        db=self.get_db();
        #result_set=db.get_instance_info(instance_id,start_time);
        result_set=db.get_instance_info_in_cache(instance_id);
#        print 'instance_id=%s start_time=%s'%(instance_id,start_time);
#        print 'result_set=',result_set;
        return result_set;
### TODO: decode it
        results=[];
        for row in result_set:
            info=list(row);
#            print 'info=',info,'type of info[-1]=',type(info[-1]);
            info[-1]=info[-1].strftime("%Y-%m-%d %T");
            results.append(info);
        return results;

    def __query_usage_report(self, args, **kwargs):
# TODO: how to use kwargs?
#    def query_usage_report(self, arg, id=None, metric='cpu', 
#                           metric_param='total',
#                           statistic='avg', period=5,
#                           timestamp_from=None, timestamp_to=None,
#                           **kwargs):
        """statistic is STATISTIC enum
        period default=5 minutes
        time_to default=0(now)"""
        """
        {
            'id': 'instance00001',
            'metric': 'network',
            'metric_param': 'vnet0',
            'statistic': 'sum',
            'period': 5,
            'timestamp_from': '2012-02-20T12:12:12',
            'timestamp_to': '2012-02-22T12:12:12',
        }
        """
#        usage_report = dict()
#        datetime_from = iso8601.parse_date(timestamp_from)
#        datetime_to = iso8601.parse_date(timestamp_to)
#        # TODO: implement
#        return {'data': usage_report}
        
        row_id = args['id']
        cf_str = args['metric']
        scf_str = args['metric_param']
        statistic = args['statistic']
        period = int(args['period'])
        timestamp_from = args['timestamp_from']
        timestamp_to = args['timestamp_to']
        time_from = iso8601.parse_date(timestamp_from)
        time_from = int(time.mktime(time_from.timetuple()))
        time_to = int(time.time())
        if not timestamp_to is None:
            time_to = iso8601.parse_date(timestamp_to)
            time_to = int(time.mktime(time_to.timetuple()))
            
        bufkey = str([row_id, cf_str, scf_str, 
                      statistic, period, time_from, time_to])
        if self.buf.hit_test(bufkey):
            print "buffer hit:", bufkey
            return self.buf.get_buf(bufkey)
            
        ret_len = 0
        (rs, count, all_data) = self.get_data(row_id, cf_str, scf_str, 
                                          time_from, time_to)
        if not rs is None and count > 0:
            buf = self.analyize_data(rs, 1, statistic)
            ret = self.analyize_data(buf, period, statistic)
            if ret is None:
                ret_len = 0
            else:
                ret = OrderedDict(sorted(ret.items(), key=lambda t: t[0]))
                ret_len = len(ret)
            print ret_len, "result."
        else:
            print "no result."
            ret = None
            ret_len = 0
            
        result = ret, ret_len, all_data
        if (not result is None and time.time() - time_to > 120):
            self.buf.cleanup()
            self.buf.save(bufkey, result)
        return result

    ##################### end public API interface ########################

