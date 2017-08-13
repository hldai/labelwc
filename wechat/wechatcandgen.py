# -*- coding: utf-8 -*-
import time
from elasticsearch import Elasticsearch
from py4j.java_gateway import JavaGateway

from mention import Mention
from queryexp import QueryExpansion

es_url = 'localhost:9200'
index_name = 'wechat'
nickname_doc_type = 'nickname'


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


def load_acronym_to_name(acronym_name_file, exclude_strs):
    acr_name_dict = dict()
    f = open(acronym_name_file, 'r')
    for line in f:
        line = line.strip().decode('utf-8')
        acr, name, _ = line.split('\t')

        if exclude_strs and acr in exclude_strs:
            continue

        acr_name_dict[acr] = name
        # print acr, name_max

    f.close()

    return acr_name_dict


def load_name_to_acronym(acronym_name_file):
    name_acr_cnt_dict = dict()
    f = open(acronym_name_file, 'r')
    for line in f:
        line = line.strip().decode('utf-8')
        acr, name, cnt = line.split('\t')
        cnt = int(cnt)

        tup = name_acr_cnt_dict.get(name, None)
        if not tup or tup[1] < cnt:
            name_acr_cnt_dict[name] = (acr, cnt)
        # print acr, name_max
    f.close()

    name_acr_dict = dict()
    for name, (acr, cnt) in name_acr_cnt_dict.iteritems():
        name_acr_dict[name] = acr

    return name_acr_dict


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


class WechatCandGen:
    def __init__(self, acr_name_file, extra_acr_name_file, expansion_exclude_strs_file,
                 abbrev_exclude_strs_file, es_url):
        self.es = Elasticsearch([es_url])

        gateway = JavaGateway()
        self.cn_seg_app = gateway.entry_point
        self.qe = QueryExpansion(acr_name_file, extra_acr_name_file, expansion_exclude_strs_file,
                                 abbrev_exclude_strs_file, self.cn_seg_app)

    def gen_canidates(self, name_str):
        name_str_seg = self.cn_seg_app.segment(name_str)

        name_words = name_str_seg.split(' ')
        exp_names = self.qe.query_expansion_words(name_words)

        # print name_str
        # print name_str_seg
        # print name_exp

        candidates = self.__query_es_for_candidates(name_str_seg)

        for exp_name in exp_names:
            name_exp_seg = self.cn_seg_app.segment(exp_name)
            candidates += self.__query_es_for_candidates(name_str_seg)

        return candidates

    def __query_es_for_candidates(self, name_seg):
        candidates = list()
        hits_info = self.__match_name_es(name_seg)
        hits = hits_info['hits']
        for hit in hits:
            # print hit['_id'], hit['_score']
            # print hit['_source']['name']
            candidates.append((hit['_id'], hit['_source']['name'], hit['_score']))
        return candidates

    def __match_name_es(self, name_str):
        qbody = {
            # "query": {"match_all": {}}
            "query": {"match": {"name": name_str}}
        }

        res = self.es.search(index=index_name, doc_type=nickname_doc_type, body=qbody, size=10)
        return res['hits']


def __name_abbrev_test():
    acr_name_file = 'e:/data/res/wiki/acr_name_filter.txt'
    extra_acr_name_file = 'e:/data/res/wiki/acr_name_man.txt'
    name_str_file = 'e:/data/wechat/20w/name_strs_stat.txt'
    expansion_exclude_strs_file = 'res/expansion_exclude_strs.txt'
    abbrev_exclude_strs_file = 'res/abbrev_exclude_strs.txt'
    dst_file = 'e:/data/wechat/tmp/name_strs_acr.txt'

    gateway = JavaGateway()
    cn_seg_app = gateway.entry_point
    # print cn_seg_app.segment(u'市卫计委')

    qe = QueryExpansion(acr_name_file, extra_acr_name_file, expansion_exclude_strs_file,
                        abbrev_exclude_strs_file, cn_seg_app)
    # print qe.expand_name(u'市卫计委')

    f = open(name_str_file)
    fout = open(dst_file, 'wb')
    for i, line in enumerate(f):
        vals = line.strip().split('\t')
        name_str = vals[0].decode('utf-8')

        # name_abr = qe.abbrev_name(name_str)
        # if name_abr:
            # print name_str, name_exp
            # if name_abr.endswith(u'大学'):
            #     print name_str, name_abr
            # fout.write((u'%s\t%s\n' % (name_str, name_abr)).encode('utf-8'))
        exp_names = qe.query_expansion(name_str)
        if exp_names:
            fout.write(name_str.encode('utf-8'))
            for n in exp_names:
                fout.write((u'\t%s' % n).encode('utf-8'))
            fout.write('\n')

        if i % 10000 == 0:
            print i
        # if i > 10000:
        #     break

    f.close()
    fout.close()


if __name__ == '__main__':
    # __find_substr_test()
    # __name_expansion()
    __name_abbrev_test()
    pass
