from elasticsearch import Elasticsearch
test_index_name = 'wechattest'
index_name = 'wechat'
es_url = 'localhost:9200'

nickname_doc_type = 'nickname'
article_doc_type = 'article'

es = Elasticsearch([es_url])


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
