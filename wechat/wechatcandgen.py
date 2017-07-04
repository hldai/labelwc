# -*- coding: utf-8 -*-
import time
from utils import seg_cn
from mention import Mention
from elasticsearch import Elasticsearch

es_url = 'localhost:9200'
index_name = 'wechat'
nickname_doc_type = 'nickname'


def __get_chars(s):
    chars = set()
    for ch in s:
        chars.add(ch)
    return chars


def __build_inverted_index(name_file):
    char_name_dict = dict()
    f = open(name_file, 'r')
    for i, line in enumerate(f):
        name = line.strip().decode('utf-8')
        chars = __get_chars(name)

        for ch in chars:
            name_list = char_name_dict.get(ch, None)
            if not name_list:
                char_name_dict[ch] = name_list = list()
            name_list.append(name)
    f.close()

    return char_name_dict


def __intersection(name_lists):
    if not name_lists:
        return None

    r = list()
    for name in name_lists[0]:
        exist_in_all = True
        for name_list in name_lists[1:]:
            if name not in name_list:
                exist_in_all = False
                break
        if exist_in_all:
            r.append(name)
    return r


def __find_substr(q, char_name_dict):
    name_lists = list()
    chars = __get_chars(q)
    for ch in chars:
        names = char_name_dict.get(ch, None)
        if names:
            name_lists.append(names)

    names = __intersection(name_lists)
    if not names:
        return

    for name in names:
        if q in name:
            print name


def __add_alias_to_dict(alias_dict, name, alias):
    aliases = alias_dict.get(name, None)
    if not aliases:
        aliases = list()
        alias_dict[name] = aliases
    aliases.append(alias)


def load_redirects(redirect_file):
    alias_dict = dict()
    f = open(redirect_file, 'r')
    for line in f:
        vals = line.strip().split('\t')
        __add_alias_to_dict(alias_dict, vals[0], vals[1])
        __add_alias_to_dict(alias_dict, vals[1], vals[0])
    f.close()

    return alias_dict


def load_expansion_dict(redirect_file):
    anchor_text_file = 'e:/data/res/wiki/anchor_text_list.txt'

    return load_redirects(redirect_file)


def __load_acronym_expansion_file(acronym_expansion_file):
    acr_exp_dict = dict()
    f = open(acronym_expansion_file, 'r')
    for line0 in f:
        line1 = f.next().strip()
        acr_exp_dict[line0.strip()] = line1.replace('\t', ' ')
    f.close()
    return acr_exp_dict


def load_strs_file(words_file):
    words = set()
    f = open(words_file, 'r')
    for line in f:
        words.add(line.strip().decode('utf-8'))
    f.close()
    return words


def load_freq_acronym_name(acronym_name_cnt_file, exclude_strs):
    # exclude_words = __load_strs_file(expansion_exclude_words_file)
    # exclude_words = set()

    acr_name_dict = dict()
    f = open(acronym_name_cnt_file, 'r')
    line = f.next()
    flg = True
    while flg:
        vals = line.strip().split('\t')
        max_cnt = int(vals[2])
        acr = vals[0].decode('utf-8')
        name_max = vals[1].decode('utf-8')

        while True:
            try:
                line = f.next()
                vals = line.strip().split('\t')
                if vals[0].decode('utf-8') != acr:
                    break
                cnt = int(vals[2])
                if cnt > max_cnt:
                    name_max = vals[1].decode('utf-8')
            except StopIteration:
                flg = False
                break

        if acr in exclude_strs:
            continue

        acr_name_dict[acr] = name_max
        # print acr, name_max

    f.close()

    return acr_name_dict


def expand_word(word, acr_name_dict):
    name_exp = ''
    pl = 0
    while pl < len(word):
        pr = len(word)
        exps = ''
        while pr > pl:
            exps = acr_name_dict.get(word[pl:pr], None)
            if exps:
                break
            pr -= 1

        if pr > pl:
            name_exp += exps
            pl = pr
        else:
            name_exp += word[pl]
            pl = pr + 1

    return name_exp


def expand_name_by_words(name_words, acr_name_dict, exclude_strs):
    name_exp = ''
    lw = len(name_words)
    l = 0
    while l < lw:
        r = lw
        cur_str = ''
        while r > l:
            cur_str = ''.join(name_words[l:r])
            if cur_str in exclude_strs:
                break
            r -= 1

        if r > l:
            name_exp += cur_str
            l = r
        else:
            name_exp += expand_word(name_words[l], acr_name_dict)
            l += 1
    return name_exp


def __find_substr_test():
    name_file = 'e:/data/res/wiki/titles.txt'
    char_name_dict = __build_inverted_index(name_file)
    __find_substr(u'北大', char_name_dict)


class WechatCandGen:
    def __init__(self, acronym_name_cnt_file, expansion_exclude_strs_file, es_url):
        self.es = Elasticsearch([es_url])
        self.exclude_strs = load_strs_file(expansion_exclude_strs_file)
        self.acr_name_dict = load_freq_acronym_name(acronym_name_cnt_file, self.exclude_strs)

    def gen_canidates(self, name_str):
        name_str_seg = seg_cn(name_str)

        name_words = name_str_seg.split(' ')
        name_exp = expand_name_by_words(name_words, self.acr_name_dict, self.exclude_strs)

        # print name_str
        # print name_str_seg
        # print name_exp

        hits_info = self.__match_name_es(name_str_seg)

        cands = list()
        # res = es.get(index=index_name, id='507b2220716ecdf0e87fa99fe51ec0d7')
        # print res['_source']['name']
        # print hits_info['total']
        hits = hits_info['hits']
        for hit in hits:
            # print hit['_id'], hit['_score']
            # print hit['_source']['name']
            cands.append((hit['_id'], hit['_source']['name'], hit['_score']))

        if name_exp != name_str:
            name_exp_seg = seg_cn(name_exp)
            hits_info = self.__match_name_es(name_exp_seg)
            # print hits_info['total']
            hits = hits_info['hits']
            for hit in hits:
                # print hit['_id'], hit['_score']
                # print hit['_source']['name']
                cands.append((hit['_id'], hit['_source']['name'], hit['_score']))

        # print
        return cands

    def __match_name_es(self, name_str):
        qbody = {
            # "query": {"match_all": {}}
            "query": {"match": {"name": name_str}}
        }

        res = self.es.search(index=index_name, doc_type=nickname_doc_type, body=qbody, size=10)
        return res['hits']


def __cand_gen():
    mentions_file = 'e:/data/wechat/mentions_raw_text.txt'
    acronym_name_cnt_file = 'e:/data/res/wiki/acronym_name_cnt.txt'
    expansion_exclude_strs_file = 'res/expansion_exclude_strs.txt'

    wcg = WechatCandGen(acronym_name_cnt_file, expansion_exclude_strs_file, es_url)

    cnt = 0
    f = open(mentions_file, 'r')
    while True:
        m = Mention.fromfile(f)
        if not m:
            break

        wcg.gen_canidates(m.name_str)

        cnt += 1
        if cnt == 6:
            break
    f.close()


if __name__ == '__main__':
    # __find_substr_test()
    # __name_expansion()
    __cand_gen()
    pass
