#! /usr/bin/env python
from redis import Redis;
from threading import Thread;
from time import sleep,time;
from collections import deque;

class RecordRemover(Thread):
    def __init__(self,redis,work_peroid=5):
        Thread.__init__(self);
        self.work_peroid=work_peroid;
        self.working=True;
        self.redis=redis;
        ### thread safe queue
        self.job_queue=deque();
    def add_job(self,job_item):
        self.job_queue.append(job_item);

    def run(self):
        print "record remover thread start working....";
        while self.working:
            time_now=int(time());
            cnt=0;
            while len(self.job_queue)>0:
                left_item=self.job_queue[0];
                if left_item[1]<=time_now:
                    self.job_queue.popleft();
                    self.redis.lpop(left_item[0]);
                    cnt=cnt+1;
                else:
                    break;
            print "delete %s items at time:%s"%(cnt,time_now);
            sleep(self.work_peroid);
    def stop(self):
        self.working=False;
        print "record remover thread stop work.";

class CacheClient(object):
    """memecached client object""";
    def __init__(self,config):
        self.client=Redis(host=config['cache_server']);
        self.client.flushdb();
        ### assume kanyun-worker send vm info every 5 seconds,but actually not, the time gap maybe 1 minute.
        self.cache_time_buffer=int(config['cache_time_buffer']);
        print "cache_time_buffer=%s"%(self.cache_time_buffer);
        self.recordRemover=RecordRemover(self.client);
## for debug
        self.recordRemover.start();

    def __del__(self):
        self.recordRemover.stop();

    def push_vm_info(self,info):
        """ push instance info into memcached server""";
        def formate_to_cache_info(info):
            """ formate as dict """
            dict_info=dict();
            dict_info['instance_id']=str(info[0]);
            dict_info['uuid']=str(info[9]);
            dict_info['info']='$'.join(info[1:9]);
            return dict_info;
        #### process vm info
        dict_info=formate_to_cache_info(info);
        recordTime=int(info[8]);
        #print 'dict_info=','$'*60;
        #print dict_info;
        index_key=dict_info['instance_id'];
        self.client.rpush(index_key,dict_info['info']);
        self.client.expire(index_key,self.cache_time_buffer);
        self.recordRemover.add_job((index_key,recordTime+self.cache_time_buffer));
        print "add record of %s at time:%s,will delete at time:%s"%(index_key,recordTime,recordTime+self.cache_time_buffer);
        print "system time:%s"%(int(time()));
        index_key='uuid#'+dict_info['instance_id'];
        self.client.set(index_key,dict_info['uuid']);
        self.client.expire(index_key,self.cache_time_buffer);
       #print 'the index_key=%s'%(index_key);

    def get_instance_list(self):
        """ return the instance list the memcached server keeped"""
        instances=[];
        instance_list=self.client.keys('instance-*');
        for instance_id in instance_list:
            instances.append((instance_id,self.client.get('uuid#'+instance_id)));
        return instances;

    def get_instance_info(self,instance_id):
        """ get instance info from cache server"""
        return self.client.lrange(instance_id,0,-1);

