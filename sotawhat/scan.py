import os
import re
import sys
import urllib.error
import urllib.request
import warnings
import html
from tenacity import retry, stop_after_attempt
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from spellchecker import SpellChecker
import time
import pandas as pd
from add_gpt import gpt_marker
from tqdm import tqdm


AUTHOR_TAG = '<a href="/search/?searchtype=author'
TITLE_TAG = '<p class="title is-5 mathjax">'
ABSTRACT_TAG = '<span class="abstract-full has-text-grey-dark mathjax"'
DATE_TAG = '<p class="is-size-7"><span class="has-text-black-bis has-text-weight-semibold">Submitted</span>'

SAVE_INTERVAL = 15    # 每处理N篇保存一次
MAX_WORKERS = 32      # 并发线程数

##TODO: add sorting program

def get_authors(lines, i):
    authors = []
    while True:
        if not lines[i].startswith(AUTHOR_TAG):
            break
        idx = lines[i].find('>')
        if lines[i].endswith(','):
            authors.append(lines[i][idx + 1: -5])
        else:
            authors.append(lines[i][idx + 1: -4])
        i += 1
    return authors, i


def get_next_result(lines, start):
    """
    Extract paper from the xml file obtained from arxiv search.

    Each paper is a dict that contains:
    + 'title': str
    + 'pdf_link': str
    + 'main_page': str
    + 'authors': []
    + 'abstract': str
    """

    result = {}
    idx = lines[start + 3][10:].find('"')
    result['main_page'] = lines[start + 2].split("href=")[1].split(">")[0].replace('"', '')
    idx = lines[start + 4][23:].find('"')
    result['pdf'] = lines[start + 4][22: 23 + idx] + '.pdf'

    start += 4

    while lines[start].strip() != TITLE_TAG:
        start += 1

    title = lines[start + 1].strip()
    title = title.replace('<span class="search-hit mathjax">', '')
    title = title.replace('</span>', '')
    result['title'] = title

    authors, start = get_authors(lines, start + 5)  # orig: add 8

    while not lines[start].strip().startswith(ABSTRACT_TAG):
        start += 1
    abstract = lines[start + 1]
    abstract = abstract.replace('<span class="search-hit mathjax">', '')
    abstract = abstract.replace('</span>', '')
    result['abstract'] = abstract
    result['authors'] = authors

    while not lines[start].strip().startswith(DATE_TAG):
        start += 1

    idx = lines[start].find('</span> ')
    end = lines[start][idx:].find(';')

    result['date'] = lines[start][idx + 8: idx + end]

    return result, start


def clean_empty_lines(lines):
    cleaned = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned.append(line)
    return cleaned


def is_float(token):
    return re.match(r"^\d+?\.\d+?$", token) is not None


def is_citation_year(tokens, i):
    if len(tokens[i]) != 4:
        return False
    if re.match(r'[12][0-9]{3}', tokens[i]) is None:
        return False
    if i == 0 or i == len(tokens) - 1:
        return False
    if (tokens[i - 1] == ',' or tokens[i - 1] == '(') and tokens[i + 1] == ')':
        return True
    return False


def is_list_numer(tokens, i, value):
    if value < 1 or value > 4:
        return False
    if i == len(tokens) - 1:
        return False

    if (i == 0 or tokens[i - 1] in set(['(', '.', ':'])) and tokens[i + 1] == ')':
        return True
    return False

def get_report(paper, keywords):
    # print(keyword in paper['abstract'].lower())
    # print(keyword in paper['title'].lower())
    title = html.unescape(paper['title'])
    headline = '{} ({} - {})\n'.format(title, paper['authors'], paper['date'])
    abstract = html.unescape(paper['abstract'])
    report = headline + abstract + '\nLink: {}'.format(paper['main_page'])
    return report

def txt2reports(txt):
    reports = []
    found = False
    txt = ''.join(chr(c) for c in txt)
    lines = txt.split('\n')
    lines = clean_empty_lines(lines)

    for i in range(len(lines)):
        line = lines[i].strip()
        if len(line) == 0:
            continue
        if line == '<li class="arxiv-result">':
            found = True
            paper, i = get_next_result(lines, i)
            # report, has_number = get_report(paper, keyword)
            # if has_number:
            reports.append(paper)
                # num_to_show -= 1
        if line == '</ol>':
            break
    return reports, found

def make_request_with_retry(req, max_retries=5, retry_delay=2):
    """
    带重试功能的请求函数
    :param req: 请求对象
    :param max_retries: 最大重试次数
    :param retry_delay: 重试等待时间(秒)
    :return: 响应对象或None
    """
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            response = urllib.request.urlopen(req)
            return response  # 请求成功，返回响应
        except urllib.error.HTTPError as e:
            if e.code == 400 and retry_count < max_retries:
                retry_count += 1
                print(f'HTTP 400错误，等待{retry_delay}秒后重试... (尝试次数: {retry_count})')
                time.sleep(retry_delay)
                continue
            
            print(f'Error {e.code}: problem accessing the server')
            return None
        except Exception as e:
            print(f'Unexpected error: {str(e)}')
            return None

@retry(stop=stop_after_attempt(3))
def process_paper(i, report):
    """ 处理单篇论文的独立函数 """
    marker = gpt_marker()
    marker.analyze(report)
    return {
        'index': i,
        'related_score': marker.related_score,
        'analyze_reason': marker.reason,
        'classification': marker.classification
    }     

def load_progress(paper_frame):
    # 深拷贝原始DataFrame避免污染
    current_df = paper_frame.copy()
    
    pending_mask = (current_df['related_score'].isnull())
    pending_indices = current_df[pending_mask].index.tolist()
    
    return current_df, pending_indices
    
def save_progress(df,TEMP_FILE):
    """ 原子化保存进度 """
    temp_path = TEMP_FILE + ".tmp"
    df.to_csv(temp_path)
    os.replace(temp_path, TEMP_FILE)  # 原子操作替换文件

def concurrent_processing(paper_frame, keyword,data_start, data_end,TEMP_FILE):
    # 1. 加载已有进度
    current_df, pending_indices = load_progress(paper_frame)
    if not pending_indices:
        print("所有论文已处理完成！")
    else:
        print(f"待处理论文数量: {len(pending_indices)}/{len(current_df)}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(process_paper, i, paper_frame.loc[i,'content']): i 
                for i in pending_indices
            }
            
            # 4. 带进度条的批处理
            batch = []
            for future in tqdm(as_completed(futures), total=len(pending_indices)):
                try:
                    result = future.result()
                    # 更新内存数据
                    for col in ['related_score', 'analyze_reason', 'classification']:
                        current_df.loc[result['index'], col] = result[col]
                    batch.append(result['index'])
                    
                    # 定期保存
                    if len(batch) >= SAVE_INTERVAL:
                        save_progress(current_df,TEMP_FILE)
                        batch = []
                        
                except Exception as e:
                    print(f"处理索引 {futures[future]} 失败: {str(e)}")
                    save_progress(current_df,TEMP_FILE)  # 出错时立即保存

            # 5. 最终保存
            if batch:
                save_progress(current_df,TEMP_FILE)
        
    # 6. 重命名为最终文件
    final_path = f'../history/{keyword.replace(" ","_")}_{data_start}->{data_end}.csv'
    os.rename(TEMP_FILE, final_path)  

def get_papers(keyword="alignment attack jailbreak cot deepseek o1 reasoning safety chain-of-thought privacy defen",data_start="2025-03-27",data_end="2025-03-28", force_search=False):

    all_papers = []
    """
    If keyword is an English word, then search in CS category only to avoid papers from other categories, resulted from the ambiguity
    """
    keyword = keyword.lower()
    words = keyword.split()
    TEMP_FILE = f"../history/temp_{keyword.replace(' ','_')}_{data_start}->{data_end}.csv"
    if os.path.exists(TEMP_FILE) and not force_search:
        # 直接加载临时文件
        paper_frame = pd.read_csv(TEMP_FILE, index_col=0)
        print(f"检测到临时文件，从中恢复进度...")
    else:

        # d = SpellChecker()
        # if not d.unknown(words):
        #     query_temp = 'https://arxiv.org/search/advanced?advanced=&terms-0-operator=AND&terms-0-term={}&terms-0-field=all&classification-computer_science=y&classification-physics_archives=all&date-filter_by=all_dates&date-year=&date-from_date=&date-to_date=&date-date_type=submitted_date&abstracts=show&size={}&order=-announced_date_first&start={}'
        url_relation=''
        for index, word in enumerate(words):
            url_relation+=f'&terms-{str(index)}-operator=OR&terms-{str(index)}-term={word}&terms-{str(index)}-field=all' if index>0 else f'&terms-0-operator=AND&terms-0-term={word}&terms-0-field=all'
        query_temp = 'https://arxiv.org/search/advanced?advanced={}&classification-computer_science=y&classification-physics_archives=all&classification-include_cross_list=include&date-filter_by=date_range&date-year=&date-from_date={}&date-to_date={}&date-date_type=submitted_date&abstracts=show&size={}&order=-announced_date_first&start={}'
        # keyword_q = keyword.replace(' ', '+')
        page = 0
        per_page = 200
        keep="initial_start"
        print("start scanning!")
        while keep:
            query = query_temp.format(url_relation, data_start, data_end, str(per_page), str(page*per_page))

            req = urllib.request.Request(query)
            response=make_request_with_retry(req)
            if not response:
                return
            txt = response.read()
            papers, found = txt2reports(txt)
            # print("papers: ", papers)
            if not found:
                if keep=="initial_start":
                    print('Sorry, we were unable to find any abstract or title with the word {}'.format(keyword))
                    return
                elif keep=="searching":
                    print("finished searching!")
                    break

            all_papers.extend(papers)
            page += 1
            keep="searching"
            print(f'Currently {len(all_papers)} papers are found!')
            # if len(all_papers)>number:
            #     break
        # 按照日期对论文进行排序
        paper_frame = pd.DataFrame()
        all_papers.sort(key=lambda x: datetime.strptime(x['date'], '%d %B, %Y'),reverse=True)
        all_reports=[]
        print(f"Finish searching! Got {len(all_papers)} in total!")
        for paper in all_papers:
            report= get_report(paper, keyword)
            paper_frame = pd.concat([paper_frame, pd.DataFrame([paper])], ignore_index=True)
            all_reports.append(report)
        del paper_frame['pdf']
        paper_frame['content']=all_reports
        paper_frame['date']=pd.to_datetime(paper_frame['date']).dt.strftime("%m/%d, %Y")
        paper_frame['related_score']=None
        paper_frame['analyze_reason']=None
        paper_frame['classification']=None
        paper_frame.to_csv(TEMP_FILE)
        print(f"Successfully saved all papers to {TEMP_FILE}!")

    print("Now analyzing...")
    concurrent_processing(paper_frame=paper_frame,keyword=keyword,data_start=data_start,data_end=data_end,TEMP_FILE=TEMP_FILE)
    # for i in tqdm(range(len(all_papers))):
    #     marker=gpt_marker()
    #     marker.analyze(all_reports[i])
    #     # paper_frame.loc[i,'related']=marker.related
    #     paper_frame.loc[i,'related_score']=marker.related_score
    #     paper_frame.loc[i,'analyze_reason']=marker.reason
    #     paper_frame.loc[i,'classification']=marker.classification
    #     paper_frame.to_csv(f'../history/{keyword.replace(" ","_")}_{data_start}->{data_end}.csv')





def main():
    if 'nt' in os.name:
        try:
            import win_unicode_console
            win_unicode_console.enable()
        except ImportError:
            warnings.warn('On Windows, encoding errors may arise when displaying the data.\n'
                          'If such errors occur, please install `win-unicode-consolde` via \n'
                          'the command `pip install win-unicode-console`.')

    # if len(sys.argv) < 2:
    #     raise ValueError('You must specify a keyword')

    # try:
    #     num_results = int(sys.argv[-1])
    #     assert num_results > 0, 'You must choose to show a positive number of results'
    #     keyword = ' '.join(sys.argv[1:-1])

    # except ValueError:
    #     keyword = ' '.join(sys.argv[1:])
    #     num_results = 5

    # get_papers(keyword="attack",data_start="2024-12-01",data_end="2024-12-02")
    get_papers(force_search=True)


if __name__ == '__main__':
    main()
