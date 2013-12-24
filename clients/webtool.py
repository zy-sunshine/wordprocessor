import os, sys
import imghdr
import urllib2, socket
from urlparse import urlparse

img_ext = ['bmp', 'gif', 'jpg', 'jpeg', 'png']
headers = {
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:2.0.1) Gecko/2010010' \
    '1 Firefox/4.0.1',
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language':'en-us,en;q=0.5',
    'Accept-Charset':'ISO-8859-1,utf-8;q=0.7,*;q=0.7'}

def get_img_to_tmpdir(url, tmpdir):
    o = urlparse(url)
    file_name = os.path.basename(o.path)

    req = urllib2.Request(url, None, headers)
    try:
        f = urllib2.urlopen(req)
        img = f.read()
    except socket.error as e:
        sys.stderr.write('Can not download socket.error %s\n' % e)
        return None
    img_type = imghdr.what('ignore', img)
    if img_type is None:
        img_type = 'jpeg'

    # Get a uniqe file path
    name, ext = os.path.splitext(file_name)
    if not ext:
        ext = '.'+img_type
    fn = '%s%s' % (name, ext)
    #save_to = os.path.join(tmpdir, fn)
    def get_a_valid_fpath(tmpdir, fn, idx=0):
        fpath = os.path.join(tmpdir, fn)
        if os.path.exists(fpath):
            n, e = os.path.splitext(fn)
            if idx != 0:
                r = n.rfind('-')
                if r != -1:
                    n = n[:]
            name_n = '%s-%s%s' % (n, idx, e)
            return get_a_valid_fpath(tmpdir, name_n, idx+1)
        else:
            return fpath
    save_to = get_a_valid_fpath(tmpdir, fn)

    f = open(save_to, 'wb')
    f.write(img)
    f.close()

    if os.path.exists(save_to):
        return save_to
    else:
        return None

if __name__ == '__main__':
    imgurl = 'http://mmbiz.qpic.cn/mmbiz/MV0MBDnQ3khbWt5MDVaRCq9Fq8pDFtc7uDnLYKFugtO5sGsVasbSI0Zkk4Sjiae3tfskicpZUtN34ia7wNTmIWgCA/0'
    get_img_to_tmpdir(imgurl, os.path.join(os.path.dirname(os.path.abspath(__file__)),'test'))
#req = urllib2.Request('http://www.amaderforum.com/login.php?do=lostpw', None,
#                      headers)

