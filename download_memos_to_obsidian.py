#!/usr/local/bin/python3
# -*- coding: UTF-8 -*-

import requests, time, os, random

FOLDER = '/Users/skyue/Documents/obsidian_default/40-摘录备份/memos/' # Memos的备份目录
IMG_PATH = '/Users/skyue/Documents/obsidian_default/assets/' # Obsidian的图片附件目录

#下载图片到本地，修改文件名
def download_resource(resource_url, img_name):
    wait_time = random.randint(1,5)
    time.sleep(wait_time)
    resource_name = img_name + '-' + resource_url.split('?')[0].split('/')[-1]
    resource_req = requests.get(resource_url)
    with open(IMG_PATH + resource_name, 'wb') as f:
        f.write(resource_req.content)
    return resource_name

# 入参memo是json格式
def download_memo(memo):
    #时间处理
    create_date = memo['createTime'][0:10]
    create_time = memo['createTime'][0:-4]
    update_time = memo['updateTime'][0:-4]

    
    # 判断是否有图片数据
    resource_markdown = ''
    if 'resources' in memo:
        for resource in memo['resources']:
            img_name = 'memo-img-' + str(resource['id'])
            if resource['externalLink']:
                resource_url = resource['externalLink']
            else:
                resource_url = 'https://memos.skyue.com/o/r/' + str(resource['id']) + '/' + resource['filename']
            resource_markdown = resource_markdown + '![[{}]]'.format(download_resource(resource_url, img_name)) + '\n'
            
    
    
    #笔记内容
    memo_body = '''---
memo_id: {memo_id}
created: {created_time}
updated: {updated_time}
---

{content}

{image}
'''.format(memo_id=memo['id'], created_time=create_time, updated_time=update_time, content=memo['content'], image=resource_markdown)
    

    #查看是否已经下载过，并根据结果给出需要保存/覆盖的笔记标题
    names = os.listdir(FOLDER)
    mk_title = create_date + '~' + str(memo['id'])
    for name in names:
        if name.find(mk_title)==0:
            mk_title = name[:-3]
            break

    
    with open(FOLDER + mk_title + '.md', 'w') as f:
        f.write(memo_body)

    print('download:', memo['id'])
        
    
if __name__ == '__main__':
    # 使用的v2接口，URL和Authorization中的Token换成自己的
    r = requests.get(
        url = 'https://memos.skyue.com/api/v2/memos?pageSize=2000',
        headers= {
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6InYxIiwidHlwIjoiSldUIn0.eyJuYW1lIjoic2t5dWUiLCJpc3MiOiJtZW1vcyIsInN1YiI6IjEiLCJhdWQiOlsidXNlci5hY2Nlc3MtdG9rZW4iXSwiaWF0IjoxNzAwMzU3ODk4fQ.K7cbfX66_EjTGtvSxJStr2ZA35YjMIwYb62cr1YW1fA',
            'Accept': 'application/json'
        }
        )

    for memo in r.json()['memos']:
        download_memo(memo)

    print('done')
