from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^article/(?P<article_idx>[0-9]+)/$', views.show_article, name='article'),
]
