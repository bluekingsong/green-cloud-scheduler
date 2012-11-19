#! /usr/bin/env python
from redis import Redis;
from threading import Thread;
from time import sleep,time;
from collections import deque;
import pdb



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
        #self.recordRemover=RecordRemover(self.client);
        #self.recordRemover.start();

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
        index_key=dict_info['uuid'];
        self.client.rpush(index_key,dict_info['info']);
        self.client.expire(index_key,self.cache_time_buffer);

    def get_instance_info(self,instance_id):
        """ get instance info from cache server"""
        return self.client.lrange(instance_id,0,-1);

if __name__=='__main__':
    conf={}
    conf['cache_server'] = 'localhost'
    conf['cache_time_buffer'] = '3600'
    cc = CacheClient(conf)
    print cc.get_instance_list()
    #print cc.get_instance_info(cc.get_instance_list()[0])
    

