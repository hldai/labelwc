# -*- coding: utf-8 -*-

import json
import socket

from django.shortcuts import get_object_or_404

from elasticsearch import Elasticsearch

from mention import Mention
from models import LabelResultWe

REV_DISPATCH_HOST, REV_DISPATCH_PORT = 'localhost', 9741
DATA_END_STR = 'DHLDHLDHLEND'

test_index_name = 'wechattest'
index_name = 'wechat'
es_url = 'localhost:9200'

nickname_doc_type = 'nickname'
article_doc_type = 'article'

es = Elasticsearch([es_url])


def __query_wechat_dispatcher(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to server and send data
        sock.connect((REV_DISPATCH_HOST, REV_DISPATCH_PORT))
        sock.sendall(data)

        received = ''
        # Receive data from the server and shut down
        while True:
            data = sock.recv(1024)
            received += data
            if received.endswith(DATA_END_STR):
                break
        # print username, received
        received = json.loads(received[:-len(DATA_END_STR)])
    finally:
        sock.close()

    return received


def get_user_num_articles(username):
    data = json.dumps({'query': 'user_num_articles', 'username': username})
    res = __query_wechat_dispatcher(data)
    return res['num_articles']


def get_label_results(mentions, username):
    label_result_dict = dict()
    for m in mentions:
        try:
            mention_id = m['mention_id']
            lr = LabelResultWe.objects.get(mention_id=mention_id, username=username)
            label_result_dict[mention_id] = lr
        except LabelResultWe.DoesNotExist:
            continue
    return label_result_dict


def get_candidates_of_mentions(mentions, label_results):
    if not mentions:
        return None

    mention_candidates = list()
    for m in mentions:
        mention_id = m['mention_id']
        # print mention_id
        lr = label_results.get(mention_id, None)
        if lr:
            lr_disp = dict()
            lr_disp['cur_state'] = lr.cur_state
            if lr.cur_state == 3:
                lr_disp['account'] = get_account_info(lr.account_id)
            # lr_disp['is_franchise'] = lr.is_franchise
            lr_disp['is_wrong_span'] = lr.is_wrong_span
            tup = (m, True, lr_disp)
            mention_candidates.append(tup)
        else:
            data = json.dumps({'query': 'candidates', 'name_str': m['name_str']})
            res = __query_wechat_dispatcher(data)
            # print res
            tup = (m, False, res['candidates'])
            mention_candidates.append(tup)
    return mention_candidates


def get_article_id_mentions(username, expected_article_idx):
    data = json.dumps({'query': 'article', 'username': username, 'article_idx': expected_article_idx})
    res = __query_wechat_dispatcher(data)
    mentions = res['mentions']
    # mentions = [Mention.from_dict(mdict) for mdict in mention_dicts]
    return res['corrected_idx'], res['article_id'], mentions


def get_account_name(account_id):
    data = json.dumps({'query': 'account', 'account_id': account_id})
    res = __query_wechat_dispatcher(data)
    nickname = res['name']
    return nickname


def get_account_info(account_id):
    name = get_account_name(account_id)
    return {'name': name}


def get_article_info(article_id):
    res = es.get(index=index_name, doc_type=article_doc_type, id=article_id)
    return res['_source']


def highlight_mentions(rev_text, mentions, label_results):
    new_text = u''
    last_pos = 0
    for i, m in enumerate(mentions):
        span_class = 'span-mention'
        if m.mention_id in label_results:
            span_class += ' span-mention-labeled'
        span_attrs = 'id="mention-span-%d" class="%s" onclick="mentionClicked(%d, \'%s\')' % (
            i, span_class, i, m.mention_id)
        new_text += u'%s<span %s">%s</span>' % (rev_text[last_pos:m.begpos], span_attrs,
                                                rev_text[m.begpos:m.endpos + 1])
        last_pos = m.endpos + 1

    new_text += rev_text[last_pos:]
    return new_text.replace('\n', '<br/>')


def __paragraph_mention_dict(mentions):
    pidx_mention_dict = dict()
    if not mentions:
        return pidx_mention_dict
    for m in mentions:
        para_idx = m['para_idx']
        cur_para_mentions = pidx_mention_dict.get(para_idx, list())
        if not cur_para_mentions:
            pidx_mention_dict[para_idx] = cur_para_mentions
        cur_para_mentions.append(m)
    return pidx_mention_dict


def __highlight_mentions_in_text(mentions, text, label_results, start_mention_idx):
    new_text = u''
    last_pos = 0
    for i, m in enumerate(mentions):
        mention_idx = i + start_mention_idx
        span_class = 'span-mention'
        mention_id = m['mention_id']
        if mention_id in label_results:
            span_class += ' span-mention-labeled'
        span_attrs = 'id="mention-span-%d" class="%s" onclick="mentionClicked(%d, \'%s\')' % (
            mention_idx, span_class, mention_idx, mention_id)
        left_pos, right_pos = m['span']
        new_text += u'%s<span %s">%s</span>' % (text[last_pos:left_pos], span_attrs,
                                                text[left_pos:right_pos + 1])
        last_pos = right_pos + 1

    new_text += text[last_pos:]
    return new_text.replace('\n', '<br/>')


def highlight_mentions_para(contents, mentions, label_results):
    disp_text = u''
    pidx_mention_dict = __paragraph_mention_dict(mentions)
    start_mention_idx = 0
    for i, content in enumerate(contents):
        if disp_text:
            disp_text += '<br>'

        mentions = pidx_mention_dict.get(i, None)
        if not mentions:
            disp_text += content
            continue

        highlighted_text = __highlight_mentions_in_text(mentions, content, label_results, start_mention_idx)
        start_mention_idx += len(mentions)
        disp_text += highlighted_text
    return disp_text


def search_candidates(qstr):
    data = json.dumps({'query': 'candidates', 'name_str': qstr})
    res = __query_wechat_dispatcher(data)
    return res['candidates']


def update_label_result(username, post_data):
    LabelResultWe.update_label_result(username, post_data)


def delete_label_result(mention_id, username):
    # lr = LabelResult.objects.get(mention_id=mention_id, username=username)
    lr = get_object_or_404(LabelResultWe, mention_id=mention_id, username=username)
    lr.delete()

    # user_num_mentions[username] -= 1
