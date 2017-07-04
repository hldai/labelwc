# -*- coding: utf-8 -*-

import json
import socket

from elasticsearch import Elasticsearch

from mention import Mention

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


def get_candidates_of_mentions(mentions):
    if not mentions:
        return None

    mention_candidates = list()
    for m in mentions:
        data = json.dumps({'query': 'candidates', 'name_str': m.name_str})
        res = __query_wechat_dispatcher(data)
        # print res
        tup = (m, False, res['candidates'])
        mention_candidates.append(tup)
    return mention_candidates


def get_article_id_mentions(article_idx):
    data = json.dumps({'query': 'article', 'article_idx': article_idx})
    res = __query_wechat_dispatcher(data)
    mention_dicts = res['mentions']
    mentions = [Mention.from_dict(mdict) for mdict in mention_dicts]
    return res['article_id'], mentions


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
