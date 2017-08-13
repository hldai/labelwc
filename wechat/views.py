from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import views as auth_views

import articledata


def index(request):
    if not request.user.is_authenticated():
        return auth_views.login(request, template_name="login.html")

    context = dict()
    context['username'] = username = request.user.username
    num_articles = articledata.get_user_num_articles(username)
    context['num_articles'] = num_articles
    #     context['num_mentions'] = reviewdata.get_user_num_labeled_mentions(username)
    context['label_article_idx'] = 1 if num_articles == 0 else num_articles
    return render(request, 'wechat/userlabelstat.html', context)
    # return HttpResponse('Hi, %s, %d' % (username, num_articles))


def show_article(request, username, article_idx):
    print username, article_idx
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('wechat:login'))
    if username != request.user.username:
        return HttpResponse('404')

    article_idx = int(article_idx)
    article_idx, article_id, mentions = articledata.get_article_id_mentions(username, article_idx)
    print article_id
    # print 'mentions', mentions
    article_info = articledata.get_article_info(article_id)
    print article_id, len(article_info['contents']), 'paragraphs'
    # article_text = article_info['text']
    # highlighted_article = articledata.highlight_mentions(article_text, mentions, [])
    # highlighted_article = '<br>'.join(article_info['contents'])
    label_results = articledata.get_label_results(mentions, request.user.username)
    highlighted_article = articledata.highlight_mentions_para(article_info['contents'], mentions, label_results)

    account_id = article_info['account_id']

    context = dict()
    context['username'] = username
    context['num_mentions'] = len(mentions)
    context['article_title'] = article_info['title']
    context['account'] = articledata.get_account_info(account_id)
    context['highlighted_article'] = highlighted_article
    context['user_article_idx'] = article_idx
    context['prev_article_idx'] = article_idx - 1 if article_idx > 1 else 1
    context['next_article_idx'] = article_idx + 1
    context['mention_candidates'] = articledata.get_candidates_of_mentions(mentions, label_results)
    return render(request, 'wechat/article.html', context)


def logout(request):
    return auth_views.logout(request, next_page=reverse('wechat:login'))


def label(request, article_idx):
    # tbeg = time()
    articledata.update_label_result(request.user.username, request.POST)
    # return HttpResponse('OK' + rev_idx)
    # print time() - tbeg
    return HttpResponseRedirect(reverse('wechat:article', args=(request.user.username, article_idx,)))


def delete_label(request, user_article_idx, mention_id):
    articledata.delete_label_result(mention_id, request.user.username)
    return HttpResponseRedirect(reverse('wechat:article', args=(request.user.username, user_article_idx,)))


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


