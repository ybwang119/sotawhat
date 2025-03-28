import os
import re
import sys
import urllib.error
import urllib.request
import warnings
import html
# import nltk
# from nltk.tokenize import word_tokenize
# from six.moves.html_parser import HTMLParser
from spellchecker import SpellChecker
import time
import pandas as pd
from add_gpt import gpt_marker
from tqdm import tqdm
# try:
#     nltk.data.find('tokenizers/punkt')
# except LookupError:
#     nltk.download('punkt')

# h = HTMLParser()

AUTHOR_TAG = '<a href="/search/?searchtype=author'
TITLE_TAG = '<p class="title is-5 mathjax">'
ABSTRACT_TAG = '<span class="abstract-full has-text-grey-dark mathjax"'
DATE_TAG = '<p class="is-size-7"><span class="has-text-black-bis has-text-weight-semibold">Submitted</span>'
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


# def has_number(sent):
#     tokens = word_tokenize(sent)
#     for i, token in enumerate(tokens):
#         if token.endswith('\\'):
#             token = token[:-2]
#         if token.endswith('x'):  # sometimes people write numbers as 1.7x
#             token = token[:-1]
#         if token.startswith('x'):  # sometimes people write numbers as x1.7
#             token = token[1:]
#         if token.startswith('$') and token.endswith('$'):
#             token = token[1:-1]
#         if is_float(token):
#             return True
#         try:
#             value = int(token)
#         except:
#             continue
#         if (not is_citation_year(tokens, i)) and (not is_list_numer(tokens, i, value)):
#             return True

#     return False


# def contains_sota(sent):
#     return 'state-of-the-art' in sent or 'state of the art' in sent or 'SOTA' in sent


# def extract_line(abstract, keyword):
#     lines = []
#     numbered_lines = []
#     kw_mentioned = False
#     abstract = abstract.replace("et. al", "et al.")
#     sentences = abstract.split('. ')
#     kw_sentences = []
#     for sent in sentences:
#         if keyword in sent.lower():
#             kw_mentioned = True
#             if has_number(sent):
#                 numbered_lines.append(sent)
#             elif contains_sota(sent):
#                 numbered_lines.append(sent)
#             else:
#                 kw_sentences.append(sent)
#                 lines.append(sent)
#             continue

#         if kw_mentioned and has_number(sent):
#             if not numbered_lines:
#                 numbered_lines.append(kw_sentences[-1])
#             numbered_lines.append(sent)
#         if kw_mentioned and contains_sota(sent):
#             lines.append(sent)

#     if len(numbered_lines) > 0:
#         return '. '.join(numbered_lines), True
#     return '. '.join(lines[-2:]), False


def get_report(paper, keywords):
    # print(keyword in paper['abstract'].lower())
    # print(keyword in paper['title'].lower())
    title = html.unescape(paper['title'])
    headline = '{} ({} - {})\n'.format(title, paper['authors'], paper['date'])
    abstract = html.unescape(paper['abstract'])
    report = headline + abstract + '\nLink: {}'.format(paper['main_page'])

        # extract, has_number = extract_line(abstract, keyword)
        # if extract:
        #     # report = headline + extract + '\nLink: {}'.format(paper['main_page'])
        #     report = headline + abstract + '\nLink: {}'.format(paper['main_page'])
        #     # print("---------------------------------link---------------------------------")
        #     # print(paper['main_page'])
    return report
    # return report, has_number

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
        
def get_papers(keyword="alignment attack jailbreak cot deepseek o1 reasoning safety chain-of-thought privacy",data_start="2025-03-27",data_end="2025-03-28"):
    all_papers = []
    """
    If keyword is an English word, then search in CS category only to avoid papers from other categories, resulted from the ambiguity
    """
    keyword = keyword.lower()
    words = keyword.split()
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
    from datetime import datetime
    paper_frame = pd.DataFrame()
    all_papers.sort(key=lambda x: datetime.strptime(x['date'], '%d %B, %Y'),reverse=True)
    all_reports=[]
    print(f"Finish searching! Got {len(all_papers)} in total!")
    for paper in all_papers:
        report= get_report(paper, keyword)
        # print(report)
        # print('====================================================')
        paper_frame = pd.concat([paper_frame, pd.DataFrame([paper])], ignore_index=True)
        all_reports.append(report)
    print("Now analyzing...")
    del paper_frame['pdf']
    paper_frame['content']=all_reports
    paper_frame['date']=pd.to_datetime(paper_frame['date']).dt.strftime("%m/%d, %Y")
    # paper_frame['related']=None
    paper_frame['related_score']=None
    paper_frame['analyze_reason']=None
    paper_frame['classification']=None
    
    for i in tqdm(range(len(all_papers))):
        marker=gpt_marker()
        marker.analyze(all_reports[i])
        # paper_frame.loc[i,'related']=marker.related
        paper_frame.loc[i,'related_score']=marker.related_score
        paper_frame.loc[i,'analyze_reason']=marker.reason
        paper_frame.loc[i,'classification']=marker.classification
        paper_frame.to_csv(f'../history/{keyword.replace(" ","_")}_{data_start}->{data_end}.csv')





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

    get_papers(data_start="2024-12-01",data_end="2025-01")


if __name__ == '__main__':
    main()
