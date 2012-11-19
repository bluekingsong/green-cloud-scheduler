#!/usr/bin/env python
#coding=utf-8
import MySQLdb as mysql;
import sys;
import pdb
from redisclient import CacheClient;

class MysqlDb(object):
    def __init__(self,conn_dict):
        self.conn=mysql.connect(conn_dict['host'],conn_dict['user'],conn_dict['passwd'],conn_dict['db']);
        self.cursor=self.conn.cursor();
    def __del__(self):
        print 'close connection to mysql...';
        self.cursor.close();
        self.conn.close();
    def __reconnect_db__(self):
        self.conn.ping(True);
        self.cursor=self.conn.cursor(); 

    def insert_monitor_data(self,data):
        self.__reconnect_db__();
        sql_cmd='''insert into vm_monitor(instance_id,cpu_usage,mem_free,mem_max,nic_in,nic_out,\
disk_read,disk_write,monitor_time,uuid)values('%s','%s',%s,%s,'%s','%s','%s','%s',from_unixtime('%s',\
'%%Y-%%m-%%d %%T'),'%s');'''%tuple(data);
        sys.stdout.flush();
        self.cursor.execute(sql_cmd);
        self.conn.commit();
        return True;

    def get_all_instances(self,start_time):
        """ list all instances from time ${start_time} to now"""
        self.__reconnect_db__();
        sql_cmd='''select distinct instance_id from vm_monitor where monitor_time>='%s';'''%start_time;
        self.cursor.execute(sql_cmd);
        return self.cursor.fetchall();

    def get_instance_info(self,instance_id,start_time):
        """ get vm info by instance_id from time $(start_time) to now"""
        self.__reconnect_db__();
        sql_cmd='''select cpu_usage,mem_free,mem_max,nic_in,nic_out,disk_read,disk_write,monitor_time uuid from vm_monitor where instance_id='%s' and monitor_time>='%s' '''%(instance_id,start_time);
        #print " in get instance info by id sql cmd=%s"%sql_cmd;
        self.cursor.execute(sql_cmd);
        return self.cursor.fetchall();


