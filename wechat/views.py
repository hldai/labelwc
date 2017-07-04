import json
import socket

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import views as auth_views

import articledata
from mention import Mention


REV_DISPATCH_HOST, REV_DISPATCH_PORT = 'localhost', 9741
DATA_END_STR = 'DHLDHLDHLEND'


def index(request):
    return show_article(request, 12)
    # return HttpResponse('Hi')


def __query_wechat_dispatcher(article_idx):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data = json.dumps({'article_idx': article_idx})

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


def show_article(request, article_idx):
    article_idx = int(article_idx)
    res = __query_wechat_dispatcher(article_idx)
    article_id = res['article_id']
    mention_dicts = res['mentions']
    mentions = [Mention.from_dict(mdict) for mdict in mention_dicts]
    print 'mentions', mentions
    article_info = articledata.get_article_info(article_id)
    article_text = article_info['text']
    biz_id = article_info['bizid']
    highlighted_article = articledata.highlight_mentions(article_text, mentions, [])

    context = dict()
    context['username'] = 'hldai'
    context['highlighted_article'] = highlighted_article
    context['prev_article_idx'] = article_idx - 1 if article_idx > 1 else 1
    context['next_article_idx'] = article_idx + 1
    return render(request, 'wechat/article.html', context)
    # return HttpResponse(highlighted_article)


def logout(request):
    return auth_views.logout(request, next_page=reverse('wechat:login'))


def label(request, article_idx):
    # tbeg = time()
    # articledata.update_label_result(request.user.username, request.POST)
    # return HttpResponse('OK' + rev_idx)
    # print time() - tbeg
    return HttpResponseRedirect(reverse('wechat:article', args=(article_idx,)))
