#! /usr/bin/env python
import memcache;
class CacheClient(object):
    """memecached client object""";
    def __init__(self,config):
        conn_str=config['cache_server']+":11211";
        self.client=memcache.Client([conn_str,]);
        ### assume kanyun-worker send vm info every 5 seconds,but actually not, the time gap maybe 1 minute.
        self.cache_pool_size=int(config['cache_pool_size']);

    def __add_new_instance__(self,instance_id,uuid):
        self.client.set(instance_id,'1');
        self.client.set(instance_id+'_uuid',uuid);
        ### add to instance list
        if self.client.get('instance_list') is None:
            self.client.set('instance_list',instance_id);
        else:
            self.client.append('instance_list',' '+instance_id);
        print 'add a new instance:%s'%(self.client.get('instance_list'));

    def __construct_index_key__(self,dict_info):
        """ construct cache key accroding the same rule(by add suffix"""
        def reset_instance_index(cache_client,instance_id,index):
            """ reset index, when index<0, its means the pool is full"""
            cache_client.replace(instance_id,str(index));
 
        instance_id=dict_info['instance_id'];
        ### maybe exist a better way to decide if the key exits
        cur_index=self.client.get(instance_id);
        if cur_index is None:
            self.__add_new_instance__(instance_id,dict_info['uuid']);
            return instance_id+'_1';
        index=int(cur_index);
        ### the pool is full, need flush old data
        if abs(index)==self.cache_pool_size:
            reset_instance_index(self.client,instance_id,-1);
            return instance_id+'_1';

        if index>0:   ### the datasize is less than  $cache_pool_size
            reset_instance_index(self.client,instance_id,index+1);
            return instance_id+'_'+str(index+1);
        ### otherwise  index<0, the cache pool for the instance is full
        reset_instance_index(self.client,instance_id,index-1);
        return instance_id+'_'+str(abs(index-1));

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
        #print 'dict_info=','$'*60;
        #print dict_info;
        index_key=self.__construct_index_key__(dict_info);
       #print 'the index_key=%s'%(index_key);
        ### save to the memcached server
        self.client.set(index_key,dict_info['info']);

    def get_instance_list(self):
        """ return the instance list the memcached server keeped"""
        instances=[];
        str_list=self.client.get('instance_list');
        if str_list is not None:
            for ins in str_list.split():
                uuid=self.client.get(ins+'_uuid');
                instances.append((ins,uuid));
        return instances;

    def get_instance_info(self,instance_id):
        """ get instance info from memcached server"""
        index_key=self.client.get(instance_id);
        if index_key is None:
            return None;
        index_key=int(index_key);
        if index_key>0: ## not full
            index_list=range(1,index_key+1);
        else:
            index_key=-index_key;
            index_list=range(index_key+1,self.cache_pool_size)+range(1,index_key+1);
        key_list=[instance_id+'_'+str(index) for index in index_list];
        value_dict=self.client.get_multi(key_list);
        if value_dict is None:
            return None;
        return value_dict.values();

