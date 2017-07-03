from django.shortcuts import render
from django.http import HttpResponse

import json
import socket


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
    res = __query_wechat_dispatcher(article_idx)
    return HttpResponse(json.dumps(res))
