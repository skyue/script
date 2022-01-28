#!/usr/local/bin/python3
import requests, sys, json, re, os, time, random, xmlrpc.client
from datetime import datetime, timedelta


# 配置
USER = '' # hypothesis账户名
TOKEN = '' # hypothesis的token
AUTH = "Bearer " + TOKEN

BLOG_USERNAME = '' # 博客用户名
BLOG_PASSWORD = '' # 博客密码
METAWEBLOG_API = 'https://hypothesis.skyue.com/action/xmlrpc' # 博客metaweblog api地址

PUB_HISTORY = '/Users/skyue/Library/Mobile Documents/iCloud~md~obsidian/Documents/obsidian_icloud/2.归档/hypothes/publish.md' #记录发布历史



# 获取最近的标注，支持限定URL
def get_with_limit(user, auth, limit, url=''):
    params={
        "user": user,
        "limit": limit,
        "tag": "hypothesis"
    }
    if url:
        params.setdefault('url', url)
        
    for i in range(10):
        try:
            response = requests.get(
                url="https://api.hypothes.is/api/search",
                params=params,
                headers={
                    "Authorization": auth,
                    "Content-Type": "application/json;charset=utf-8",
                },
            )
            return response
        except requests.exceptions.RequestException:
            time.sleep(random.randint(2,9))
        
    print('连续10次请求均失败')
        


annotations = json.loads(get_with_limit(USER, AUTH, 20).text)['rows']
for annotation in annotations:
    title = annotation['document']['title'][0]
    created_time = annotation['created']
    domain = annotation['uri'].split('/')[2]
    url = annotation['uri']
    note = annotation['text']
    tags = annotation['tags']
    tags.remove('hypothesis')
    content = '''链接：[{domain}]({url})

{note}'''.format(domain=domain, url=url, note=note)

    struct = {
        'title': title,
        'dateCreated': datetime.strptime(created_time[:19], '%Y-%m-%dT%H:%M:%S'),
        'categories': list(tags),
        'post_type': 'post',
        'description': content,
    }
    
    
    with open(PUB_HISTORY, 'r') as f:
        pub_url_tmp = f.read()
        
    if pub_url_tmp.find(url) == -1:
        client = xmlrpc.client.ServerProxy(METAWEBLOG_API)

        cid = client.metaWeblog.newPost('',BLOG_USERNAME, BLOG_PASSWORD, struct, True)
        if cid != 0:
            with open(PUB_HISTORY, 'a') as f:
                f.write('{cid} : {url}\n'.format(cid=cid, url=url))
            print('发布成功')
    else:
        print('已发布过')
