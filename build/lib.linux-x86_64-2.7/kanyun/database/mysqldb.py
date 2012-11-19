#!/usr/bin/env python
#coding=utf-8
import MySQLdb as mysql;
import sys;
from redisclient import CacheClient;

class MysqlDb(object):
    def __init__(self,conn_dict):
#        self.conn=mysql.connect(host="localhost",user="root",passwd="ljsljs",db="openstack");
        self.conn=mysql.connect(conn_dict['host'],conn_dict['user'],conn_dict['passwd'],conn_dict['db']);
        self.cursor=self.conn.cursor();
        ### create Memecached Client Object
        self.cache=CacheClient(conn_dict);
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
        #print "in insert_monitor_data, the data=",data;
        #print "\nsql_cmd=%s\n"%(sql_cmd);
        sys.stdout.flush();
        self.cursor.execute(sql_cmd);
        self.conn.commit();
        self.cache.push_vm_info(data);
        return True;

    def get_instances_in_cache(self):
        return self.cache.get_instance_list();
    
    def get_instance_info_in_cache(self,instance_id):
        return self.cache.get_instance_info(instance_id);
 
    def get_all_instances(self,start_time):
        """ list all instances from time ${start_time} to now"""
        self.__reconnect_db__();
        sql_cmd='''select distinct instance_id from vm_monitor where monitor_time>='%s';'''%start_time;
 #       print ' in get all instances func: sql_cmd=%s'%sql_cmd;
        self.cursor.execute(sql_cmd);
        return self.cursor.fetchall();

    def get_instance_info(self,instance_id,start_time):
        """ get vm info by instance_id from time $(start_time) to now"""
        self.__reconnect_db__();
        sql_cmd='''select cpu_usage,mem_free,mem_max,nic_in,nic_out,disk_read,disk_write,monitor_time uuid from vm_monitor where instance_id='%s' and monitor_time>='%s' '''%(instance_id,start_time);
        #print " in get instance info by id sql cmd=%s"%sql_cmd;
        self.cursor.execute(sql_cmd);
        return self.cursor.fetchall();

    def process_monitor_info(self,tool,info):
### info= {'instance-00000001': [('cpu', 'total', (1344394313.516737, 0.0)), ('mem', 'total', (1344394313.516737, 524288L, 0L)), ('nic', 'vnet0', (1344394313.52059, 29645L, 0L)), ('blk', 'vda', (1344394313.525229, 512L, 0L))]
        for instance in info:
            ## create a list with length 9
            data=range(10);
            data[0]=instance;
            data[9]=tool.get_uuid_by_novaid(instance);
            #print 'nova id:%s--->uuid:%s'%(data[0],data[9]);
            instance_info=info[instance];
            nic_in_info="";
            nic_out_info="";
            blk_read_info="";
            blk_write_info="";
            for item_info in instance_info:
                if item_info[0]==unicode("cpu"):
                    cpu_usage=str(item_info[2][1]);
                    ##print 'cpu_usage=',cpu_usage;
                    data[1]=cpu_usage[0:5];
                    data[8]=timestamp=int(item_info[2][0]);
                elif item_info[0]==unicode("mem"):
                    data[2]=mem_free=item_info[2][2];
                    data[3]=mem_max=item_info[2][1];
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
            self.insert_monitor_data(data);
        return True; 

if __name__=='__main__':
    info= {'test':[('cpu','total', (1344394313.516737, 0.0)), ('mem', 'total', (1344394313.516737, 524288L, 0L)), ('nic', 'vnet0', (1344394313.52059, 29645L, 0L)), ('blk', 'vda', (1344394313.525229, 512L,0L)),('nic','vnet1',(13,2954L,0L)),('blk','vdb',(144,10234L,243L))]};
#   info={'instance-00000001':[('cpu','total',(1344394313.516737,0.0)),('mem','total',(134394313.5167337,524288L,0L))]};
    mysql_conn_str="{'host':'localhost','user':'root','passwd':'ljsljs','db':'openstack'}";
    mysql_server=MysqlDb(eval(mysql_conn_str));
    mysql_server.process_monitor_info(info);
    print 'test over';  
