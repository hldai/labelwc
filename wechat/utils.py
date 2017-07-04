import re
import socket


def seg_cn(text):
    ENDSTR = "DHLDHLDHLEND"
    BUF_SIZE = 1024
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('127.0.0.1', 7131))
        sock.sendall(text.encode('utf-8') + ENDSTR)

        data = ''
        while True:
            data_tmp = sock.recv(BUF_SIZE)
            data += data_tmp
            if data.endswith(ENDSTR):
                break
        data = data[:-len(ENDSTR)]

    finally:
        sock.close()

    return data.decode('utf-8')
