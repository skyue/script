import requests
from datetime import datetime
import random
import time

# 开始时间，备份取这一天之后的所有数据
START_DATE = datetime.strptime('20220401','%Y%m%d') 

#图片存储目录
IMG_PATH = '/Users/skyue/Dropbox/backup/weibo_backup/202204/'
#markdown文件存储目录
MD_PATH = '/Users/skyue/Dropbox/backup/weibo_backup/202204/'

#cookie从浏览器中取
HEADERS={
    'cookie': '',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'
}

# 获取单条微博内容，不含转发内容。
def get_one_weibo(wb_json_obj):
    #print(wb_json_obj)
    mblogid = wb_json_obj['mblogid']
    print('mblogid:', mblogid)
    wb_url = 'https://weibo.com/5384740764/' + mblogid
    created_at = datetime.strptime(wb_json_obj['created_at'].replace('+0800',''),'%a %b %d %H:%M:%S %Y')
    created_at_str = created_at.strftime('%Y-%m-%d %H:%M')
    #print(wb_json_obj['user']) 
    
    #判断微博是否违规被平台删除
    if wb_json_obj['user'] != None:
        user_name = wb_json_obj['user']['screen_name']
    

        if wb_json_obj['isLongText'] == False:
            text_raw = wb_json_obj['text_raw'].replace('\u200b','').strip()
            if 'url_struct' in wb_json_obj.keys():
                text_raw = replace_url(text_raw, wb_json_obj['url_struct'])
    
        else:
            long_data = requests.get('https://weibo.com/ajax/statuses/longtext?id='+mblogid,headers=HEADERS).json()['data']
            #print(long_data,'\n\n')
            if 'longTextContent' in long_data.keys():
                text_raw=long_data['longTextContent'].replace('\u200b','').strip()
                if 'url_struct' in long_data.keys():
                    text_raw=replace_url(text_raw, long_data['url_struct'])
            else:
                text_raw = wb_json_obj['text_raw'].replace('\u200b','').strip()
                if 'url_struct' in wb_json_obj.keys():
                    text_raw = replace_url(text_raw, wb_json_obj['url_struct'])
            
        #微博内容，保留地理位置信息
        if 'tag_struct' in wb_json_obj.keys():
            for tag in wb_json_obj['tag_struct']:
                if 'otype' in tag.keys() and tag['otype'] == 'place':
                    text_raw = text_raw + ' *at '+ tag['tag_name'] + '* '


        pic_ids = wb_json_obj['pic_ids']
        pic_text = ''
        for pic_id in pic_ids:
            #pic_url = wb_json_obj['pic_infos'][pic_id]['original']['url']
            pic_url = 'https://wx1.sinaimg.cn/orj1080/' + pic_id + '.jpg'
            pic_name = download_pic(pic_url, created_at.strftime('%Y%m%d'))
            pic_text = pic_text + '![[' + pic_name + ']]' + '\n'

        wb_text = '{text_raw}\n\n{pic_text}'.format( 
            text_raw=text_raw ,
            #wb_url=wb_url,
            pic_text=pic_text
        ) 
    
    else:
        user_name = ''
        wb_text = wb_json_obj['text_raw']
    
    return {
        'wb_time': created_at,
        'wb_url': wb_url,
        'wb_user': user_name,
        'wb_text': wb_text,
        'wb_md': '@{user_name}：{org_text} \n\n'.format(
            user_name=user_name,
            org_text=wb_text,
        )
    }



# 获取单条微博，若有转发含转发内容，并且封装成md格式文本
def get_single_weibo(wb_json_obj):
    org_weibo=get_one_weibo(wb_json_obj)
    if 'retweeted_status' in wb_json_obj.keys():
        re_weibo=get_one_weibo(wb_json_obj['retweeted_status'])
        full_text = '- [{time}]({url})\n\n{org_text}\n> {re_text}\n\n'.format(
            time=org_weibo['wb_time'],
            url=org_weibo['wb_url'],
            org_text=org_weibo['wb_md'],
            re_text=re_weibo['wb_md'].strip().replace('\n\n','\n> \n> ')
        )
    else:
        full_text = '- [{time}]({url})\n\n{org_text}\n\n'.format(
            time=org_weibo['wb_time'],
            url=org_weibo['wb_url'],
            org_text=org_weibo['wb_md'],
        )

    if 'url_struct' in wb_json_obj.keys():
        full_text=replace_url(full_text, wb_json_obj['url_struct'])
        
    return {
        'wb_time': org_weibo['wb_time'],
        'full_text': full_text
    }

    


# 获取一页微博，且要求时间在START_DATE（含）之后
def get_page_weibo(page_no,START_DATE):
    page_url = 'https://weibo.com/ajax/statuses/mymblog?uid=5384740764&feature=0&page=' + str(page_no)
    wb_req = requests.get(page_url, headers=HEADERS)
    if wb_req.json()['ok'] != 1:
        return {
            'page_no': page_no,
            'ok': wb_req.json()['ok'],
            'date_stop': False,
            'my_wb_list': []
        }
    else:
        print('ok')
        wb_list = wb_req.json()['data']['list']
        my_wb_list = []
        date_stop = False
        for wb in wb_list:
            #print('wb:',wb,'\n')
            single_wb = get_single_weibo(wb)
            #print('single_wb:', single_wb, '\n')
            time = single_wb['wb_time']
            if time >= START_DATE:
                my_wb_list.append(single_wb)
            else:
                date_stop = True
        return {
            'page_no': page_no,
            'ok': 1,
            'date_stop': date_stop,
            'my_wb_list': my_wb_list
        }


# 取START_DATE之后的所有微博，最多最多100页2000条
def get_month_weibo(START_DATE):
    month_weibo = []
    for page_no in range(1,100):
        print('page_no:', page_no, '\n')
        time.sleep(random.random()*5)
        page_weibo = get_page_weibo(page_no, START_DATE)
        month_weibo.append(page_weibo)
        if page_weibo['date_stop'] == True:
            break
    return month_weibo


# 下载图片到pic文件夹，图片名加weibo-yyyymm前缀，并且返回图片的名称
def download_pic(url, daytime):
    pic_name = 'weibo-' + daytime + '-' + url.split('?')[0].split('/')[-1]
    pic_req = requests.get(url)
    with open(IMG_PATH+pic_name, 'wb') as f:
        f.write(pic_req.content)
    return pic_name

# 将微博文本中的短链替换为原始长链
def replace_url(text, url_struct):
    for url in url_struct:
        md_url='[{url_title}]({long_url})'.format(url_title=url['url_title'], long_url=url['long_url'])
        text=text.replace(url['short_url'], md_url)
    return text


# 将微博写入md文件，并返回抓取失败的页面
def work():
    month_weibo = get_month_weibo(START_DATE)
    md_content = ''
    page404 = []

    for page in month_weibo:
        print(page['page_no'],': ',page['ok'], '\n')
        for weibo in page['my_wb_list']:
            md_content = weibo['full_text'] + md_content
            
    file_name = '微言小义（{start}）.md'.format(start=START_DATE.strftime('%Y%m'))
    with open(MD_PATH + file_name,'w') as f:
        f.write(md_content)
        
work()

print('done')
