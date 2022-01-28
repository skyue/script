#!/usr/local/bin/python3
import requests, sys, json, re, os, time, random
from datetime import datetime

# 配置
USER = '' # hypothesis账户名
TOKEN = '' # hypothesis的token
AUTH = "Bearer " + TOKEN
BASE_DIR = '/Users/skyue/Library/Mobile Documents/iCloud~md~obsidian/Documents/obsidian_icloud/2.归档/hypothes/' # 备份目录



# 获取最近的标注，支持限定URL，API不稳定，失败后重新请求，最多10次
def get_with_limit(user, auth, limit, url=''):
    params={
        "user": user,
        "limit": limit,
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
        
            
        

# 获取最近200条标注的url并去重
def get_recent_urls():
    annotations = json.loads(get_with_limit(USER, AUTH, 200).text)
    urls = []
    for annotation in annotations['rows']:
        urls.append(annotation['uri'])
    urls = list(set(urls))
    return urls




# 重新结构化单条标注，type区分段落标注和页面标注
def parse_annotation(annotation):
    if 'selector' not in annotation['target'][0]:
        annotation_type = 'page'
        annotation_text = ''
        annotation_offset = '0'
    else:
        annotation_type = 'annotation'
        for selector in annotation['target'][0]['selector']:
            if selector['type'] == 'TextQuoteSelector':
                annotation_text = str(selector['exact'])
            if selector['type'] == 'TextPositionSelector':
                annotation_offset = str(selector['start'])

    tags = ''
    for tag in annotation['tags']:
        tags = tags + '[[' + tag + ']] '
        
    return {
        'id': annotation['id'],
        'created': annotation['created'][:16].replace('T', ' '),
        'updated': annotation['updated'][:16].replace('T', ' '),
        'title': annotation['document']['title'][0],
        'url': annotation['uri'],
        'mark': annotation['text'].strip(),
        'tags': tags,
        'type': annotation_type,
        'text': annotation_text.strip(),
        'offset': annotation_offset
    }

              
        
# 获取一篇文章标注结果为markdown，如果没有URL，则获取最近一篇
def get_page_hls_markdown(url=''):
    if not url.startswith('http'):
        url = json.loads(get_with_limit(USER, AUTH, 1).text)['rows'][0]['uri']
    hls = []
    page_hls_json = json.loads(get_with_limit(USER, AUTH, 200, url).text)
    for index, item in enumerate(page_hls_json['rows']):
        hls.append(parse_annotation(item))
        
    hls = sorted(hls, key=lambda hl: hl['offset'].rjust(10,'0'))
    
    createds = []
    updateds = []
    
    text = ''
    for hl in hls:
        createds.append(hl['created'])
        updateds.append(hl['updated'])
        if hl['mark'] == '':
            part = '\n- {text} {tags}'.format(text=re.sub(r'\n|\t', ' ', hl['text']), tags=hl['tags'])
        else:
            part = '\n- {text}【{mark}】 {tags}'.format(text=re.sub(r'\n|\t', ' ', hl['text']),mark=re.sub(r'\n|\t', ' ', hl['mark']), tags=hl['tags'])
        text = text + part
    created = min(createds)
    updated = max(updateds)
    
    excerpts = '''---
title: {title}
link: {url}
created: {created}
updated: {updated}
---

{text}'''.format(title=hls[0]['title'], \
                url=hls[0]['url'],\
                created=created, \
                updated=updated, \
                text=text)
    
    return {
        'title': hls[0]['title'],
        'url': hls[0]['url'],
        'created': created,
        'updated': updated,
        'content': excerpts
    }




if __name__ == '__main__':
    try:
        url = '' if len(sys.argv) != 2 else sys.argv[1]
        if url:
            page_hls = get_page_hls_markdown(url=url)
            file_name = page_hls['created'][2:10].replace('-','') + '~' + page_hls['title'] + '.md'
            with open(BASE_DIR + file_name, 'w') as f:
                f.write(page_hls['content'])
            with open(BASE_DIR + 'done_url.md', 'a+') as f:
                f.write(datetime.now().strftime('%Y-%m-%d') + '指定 ' + url + '\n')
            print('\n更新成功: {}\n'.format(url))
        else:
            recent_urls = get_recent_urls()
            with open(BASE_DIR + 'done_url.md', 'r') as f:
                done_urls_tmp = f.read()

            add_urls = ''
            for url in recent_urls:
                if done_urls_tmp.find(url) == -1:
                    page_hls = get_page_hls_markdown(url=url)
                    file_name = page_hls['created'][2:10].replace('-','') + '~' + page_hls['title'] + '.md'
                    with open(BASE_DIR + file_name, 'w') as f:
                        f.write(page_hls['content'])
                    with open(BASE_DIR + 'done_url.md', 'a+') as f:
                        f.write(datetime.now().strftime('%Y-%m-%d') + '批量 ' + url + '\n')
                    add_urls = add_urls + page_hls['title'] + ': ' + url + '\n'

            msg = '''
            \n去重URL: {recent_urls}个\n新添加URL: {add_urls_len}个，分别如下：\n{add_urls_detail}\n
            '''.format(recent_urls=len(recent_urls), add_urls_len=len(add_urls.split('\n'))-1, add_urls_detail=add_urls)

            print(msg)
        
    except Exception as e:
        print(sys.argv)
        print(e)
