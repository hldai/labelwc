from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import views as auth_views

import articledata


def index(request):
    return show_article(request, 12)
    # return HttpResponse('Hi')


def show_article(request, article_idx):
    article_idx = int(article_idx)
    article_id, mentions = articledata.get_article_id_mentions(article_idx)
    # print 'mentions', mentions
    article_info = articledata.get_article_info(article_id)
    print article_id, len(article_info['contents']), 'paragraphs'
    # article_text = article_info['text']
    # highlighted_article = articledata.highlight_mentions(article_text, mentions, [])
    # highlighted_article = '<br>'.join(article_info['contents'])
    highlighted_article = articledata.highlight_mentions_para(article_info['contents'], mentions, [])

    account_id = article_info['account_id']

    context = dict()
    context['username'] = 'hldai'
    context['account'] = articledata.get_account_info(account_id)
    context['highlighted_article'] = highlighted_article
    context['prev_article_idx'] = article_idx - 1 if article_idx > 1 else 1
    context['next_article_idx'] = article_idx + 1
    context['mention_candidates'] = articledata.get_candidates_of_mentions(mentions)
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


def search_candidates(request):
    mention_id = request.POST['mention_id']
    qstr = request.POST['query_str']
    # reviewed_city = request.POST['reviewed_biz_city']
    candidates = articledata.search_candidates(qstr)
    # print candidates
    context = {
        'mention_id': mention_id,
        'candidates': candidates,
        "candidate_type": "search"
    }
    return render(request, 'wechat/candidates.html', context)


