#!/usr/local/bin/python3
# -*- coding: UTF-8 -*-

import xmlrpc.client
import datetime
import time
import re
import upyun
import sys
import os
import yaml


# 个人信息配置
BLOG_USERNAME = '' # 博客用户名
BLOG_PASSWORD = '' # 博客密码
UP_SERVICE = '' #又拍云服务名
UP_USERNAME = '' # 又拍云操作员名称
UP_PASSWORD = '' #又拍云操作员密码
UP_PATH = '/blog_img/' # 又拍云上传图片的目录

OB_VAULT = '/Home/Documents/my_note' # Obsidian的vault目录
PICTURE_PATH = OB_VAULT + '/assets/' # 本地保证图片的目录，即我的Obsidian附件目录
PICTURE_UPLOADED = OB_VAULT + '/00-template/picture_uploaded.md' # 使用一则笔记保存图片上传记录，更新文章时避免重复上传
SLUG_CID_MAPPING = OB_VAULT + '/00-template/slug_cid_mapping.md' # 使用一则笔记保存slug与cid的mapping文件，实现对已发布的文章进行更新，避免重复发布
YEAR=''

METAWEBLOG_API = '' # 博客metaweblog api地址

# 解析markdown文件
#     入参：markdown文件路径
#     返回：data字典，data['meta']为front_meta字典，包含title/date/category/tags(列表)，data['content']为文章正文[[]]未经特殊处理
def file_read(file):
    with open(file, 'r') as f:
        file_content = f.read().strip()
    
    if file_content.strip().find('---') == 0: array = file_content.strip()[3:].strip().split('---\n', 1)
    else: array = file_content.strip().split('+++\n', 1)
    
    if len(array) != 2:
        print('格式错误\n\n\n')
    else:
        front_meta_dict = yaml.safe_load(array[0])
        
        if 'title' not in front_meta_dict or front_meta_dict['title'] == '': 
            print('必须有title且不能为空')
        if 'publish_date' not in front_meta_dict or front_meta_dict['publish_date'] == '': 
            print('必须有publish_date且不能为空')

        front_meta_dict['date'] = str(front_meta_dict['publish_date'])

        
        global YEAR 
        YEAR=front_meta_dict['date'][0:4]
        if 'slug' not in front_meta_dict or front_meta_dict['slug'] == '':
            front_meta_dict['slug'] = front_meta_dict['date'][2:10]
        if 'type' not in front_meta_dict or front_meta_dict['type'] not in ['post','page']:
            front_meta_dict['type'] = 'post'
        if 'categories' not in front_meta_dict:
            front_meta_dict['categories'] = []
        if 'blogtags' not in front_meta_dict:
            front_meta_dict['blogtags'] = ''
        else:
            front_meta_dict['blogtags'] = ','.join(front_meta_dict['blogtags'])
        if 'mt_allow_comments' not in front_meta_dict:
            front_meta_dict['mt_allow_comments'] = 1
        data = {'meta': front_meta_dict, 'content': array[1].strip().split('\n## ChangeLog\n')[0].strip()}
        return data

# 格式化字符串list，去掉空值，去掉字符串两端的空字符
def list_strip(lst):
    result = []
    for v in lst:
        if v.strip() != '': result = result + [v]
    return result

# URL替换函数：把[[]]替换为[]()标准markdown链接
def url_repl(matchobj):
    meta = matchobj.group(0)[2:-2].split('|', 1)
    # 如果有|线，使用|线后的文字做链接文字
    if len(meta) == 2:
        return '[{txt}]({url})'.format(\
        txt=meta[1], \
        url='https://www.skyue.com/' + meta[0].split('~')[0].strip() + '.html')
    # 如果不存在|线，从~~中间取文字链接
    else:
        return '[{txt}]({url})'.format(\
        txt=meta[0].split('~')[1], \
        url='https://www.skyue.com/' + meta[0].split('~')[0].strip() + '.html')

# IMG替换函数：上传图片到又拍云，并把![[]]替换为![]()标准markdown图片
def img_repl(matchobj):
    meta = matchobj.group(0)[3:-2].split('|', 1)
    file_path = PICTURE_PATH + meta[0]
    up_path = '/blog_static/{year}/'.format(year=YEAR) + meta[0]

    #20210503添加……
    with open(PICTURE_UPLOADED, 'r') as picture_uploaded_file:
        picture_uploaded_status = picture_uploaded_file.readlines()
    #print(picture_uploaded_status)

    if up_path+'\n' not in picture_uploaded_status:
        upload_picture_to_upyun(file_path, up_path)
        with open(PICTURE_UPLOADED, 'a') as picture_uploaded_file:
            picture_uploaded_file.write(up_path+'\n')
        if len(meta) == 2:
            return '![{txt}]({url})'.format(txt=meta[1], url=up_path)
        else:
            return '![{txt}]({url})'.format(txt='', url=up_path)
    else:
        if len(meta) == 2:
            return '![{txt}]({url})'.format(txt=meta[1], url=up_path)
        else:
            return '![{txt}]({url})'.format(txt='', url=up_path)    
    

# 将[[]]和![[]]转化为标准的[]()和![]()
def to_stard_markdown(content):
    content = re.sub('!\[\[(.+?[png|PNG|jpg|JPG|jpeg|JPEG|gif|GIF].*?)\]\]', img_repl, content)
    content = re.sub('\[\[[0-9]{8}(.+?)\]\]', url_repl, content)
    content = content.replace('[[','').replace(']]','')
    return content

# 上传图片到又拍云，并将上传关在保存在picture_uploaded
# 入参：file_path本地文件路径，up_path定义又拍云路径
def upload_picture_to_upyun(file_path, up_path):
    up = upyun.UpYun(UP_SERVICE, UP_USERNAME, UP_PASSWORD)
    with open(file_path, 'rb') as f:
        res = up.put(up_path, f)
        print('\n上传图片: ', up_path, '\n', res)
        
        
# 根据slug获取本地的cid
def get_cid(slug):
    with open(SLUG_CID_MAPPING, 'r') as f:
        kvs = list_strip(f.read().split('\n'))
    if kvs == []:
        return '0'
    else:
        mapping = {}
        for kv in kvs:
            mapping[kv.split(':')[0].strip()] = kv.split(':')[1].strip()
        if slug not in mapping:
            return '0'
        else:
            return mapping[slug]


# 保存slug和cid的关系
def save_cid(slug, cid):
    if int(cid) > 0:
        with open(SLUG_CID_MAPPING, 'a') as f:
            f.write(slug + ':' + cid + '\n')
    else:
        return 'cid不对，保存失败'
            
# 创建文章，若文件已经存在，则自动更新，
#     入参：file要发布的文件，post_type发布类型（post-文章，page：页面）
def new_post(file):
    data = file_read(file)
    slug = data['meta']['slug']
    cid = get_cid(slug)


    if file.split('/')[-1].split('~')[0] != slug:
        print('文件标题slug不对')
        exit()


    # 构建发布内容
    struct = {
        'title': data['meta']['title'],
        'dateCreated': datetime.datetime.strptime(data['meta']['date'],'%Y%m%d%H%M')-datetime.timedelta(hours=0),
        'wp_slug': slug, 
        'categories': data['meta']['categories'],
        'mt_keywords': data['meta']['blogtags'],
        'post_type': data['meta']['type'],
        'mt_allow_comments': data['meta']['mt_allow_comments'],
        'description': to_stard_markdown(data['content']),
    }

    client = xmlrpc.client.ServerProxy(METAWEBLOG_API)

    if int(cid) > 0:
        try:
            result = client.metaWeblog.editPost(cid, BLOG_USERNAME, BLOG_PASSWORD, struct, True)
            print('\n文章已存在（cid={cid}），更新成功，信息如下：\n'.format(cid=cid))
            for key, value in struct.items():
                if key != 'description': print(key, ': ', value)
            print('\n')
        except Exception as e:
            print(e)
    else:
        cid = client.metaWeblog.newPost('',BLOG_USERNAME, BLOG_PASSWORD, struct, True)
        if cid != 0:
            save_cid(str(slug), str(cid))
        print('\n发布成功(cid={cid})，信息如下：\n'.format(cid=cid))
        for key, value in struct.items():
            if key != 'description': print(key, ': ', value)
        print('\n')



python_script = sys.argv[0]
file_path = sys.argv[2]
vault_path = sys.argv[1]

abs_file_path = os.path.abspath(os.path.join(vault_path, file_path))

print(f"This is the open file: {abs_file_path}")

new_post(abs_file_path)
