#!/usr/bin/env python
#coding=utf-8
import MySQLdb as mysql;

class MysqlDb(object):
    def __init__(self):
        self.conn=mysql.connect(host="localhost",user="root",passwd="ljsljs",db="openstack");
        self.cursor=self.conn.cursor();
    def __del__(self):
        print 'close connection to mysql...';
        self.cursor.close();
        self.conn.close();
   
    def insert_monitor_data(self,data):
        sql_cmd='''insert into vm_monitor(instance_id,cpu_usage,mem_free,mem_max,nic_in,nic_out,\
disk_read,disk_write,monitor_time)values('%s','%s',%s,%s,'%s','%s','%s','%s',from_unixtime('%s','%%Y-%%m-%%d %%T'))'''%tuple(data);
        print "sql_cmd=%s"%sql_cmd;
        self.cursor.execute(sql_cmd);
        self.conn.commit();
        return True;

    def process_monitor_info(self,info):
### info= {'instance-00000001': [('cpu', 'total', (1344394313.516737, 0.0)), ('mem', 'total', (1344394313.516737, 524288L, 0L)), ('nic', 'vnet0', (1344394313.52059, 29645L, 0L)), ('blk', 'vda', (1344394313.525229, 512L, 0L))]
        for instance in info:
            ## create a list with length 9
            data=range(9);
            data[0]=instance;
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
   mysql_server=MysqlDb();
   mysql_server.process_monitor_info(info);
   print 'test over';  
