import re
import sys
import time
import urllib
import urllib2


headers = {'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; '\
                           'rv:1.9.2.10) Gecko/20100928 Firefox/3.6.1'}

host = 'http://www.cuevana.tv'

series_url = host+'/series/'
seassons_url = host+'/list_search_id.php?serie=%s'
episodes_url = host+'/list_search_id.php?temporada=%s'

episode_url = host+"/series/%s/%s/%s/"
player_url = host+'/player/source?id=%s&subs=,ES,EN&onstart=yes&tipo=s&sub_pre=ES'
source_get = host+'/player/source_get'

sub_url = host+'/files/s/sub/%s_%s.srt'


series_re = re.compile('serieslist.push\(\{id:([0-9]*),nombre:"(.*?)"\}\);')
seasson_re = re.compile('<li onclick=\'listSeries\(2,"([0-9]*)"\)\'>(.*?)</li>')
episode_re = re.compile('<li onclick=\'listSeries\(3,"([0-9]*)"\)\'>'\
                        '<span class=\'nume\'>([0-9]*)</span>(.*?)</li>')
mega_id_re = re.compile('goSource\((.*?)\',\'megaupload\'\)')

captcha_re = re.compile('<img src="(http\:\/\/.*megaupload\.com\/'\
                                           'gencap.php\?.*\.gif)"')
fname_re = re.compile('font-size:22px; font-weight:bold;">(.*?)</font><br>')

source_re = re.compile("goSource\('([a-zA-Z0-9]*?)','([a-zA-Z]*?)'\)")

def retry(callback):
    ''' Retry decorator '''
    def deco(url, data=None, filename=None):
        tried = 0
        while tried < 3:
            try:
                return callback(url, data, filename)
            except Exception, error:
                tried += 1
                time.sleep(1)
        raise Exception, 'Can\'t download "%s" error: "%s"' % (url, error)
    return deco

@retry
def url_open(url, data=None, filename=None):
    if data:
        request = urllib2.Request(url, urllib.urlencode(data), headers)
    else:
        request = urllib2.Request(url, headers=headers)
    rc = urllib2.urlopen(request)
    if filename:
        local = open(filename, 'wb')

    text = ''
    size = 0
    lastsize = 0

    while True:
        buffer = rc.read(1024)
        if buffer == '':
            break

        if filename:
            size += len(buffer)
            local.write(buffer)
            if (size - 1024*4) > lastsize:
                sys.stdout.write(str(size/1024) + "kb downloaded...\r")
                sys.stdout.flush()
                lastsize = size
        else:
            text += buffer
    if filename:
        local.close()
        print

    return text

def get_series(name=None):
    series = series_re.findall(url_open(series_url))
    if name:
        series = [s for s in series if name.lower() in s[1].lower()]
    return series

def get_seassons(serie):
    seassons = seasson_re.findall(url_open(seassons_url % serie[0]))
    return seassons

def get_episodes(seasson):
    episodes = episode_re.findall(url_open(episodes_url % seasson[0]))
    return episodes


def main():
    lang = 'ES'
    if len(sys.argv) > 2:
        print 'Usage %s ["Name Of Serie"]' % sys.argv[0]
        exit()

    name = None
    if len(sys.argv) == 2:
        name = sys.argv[1]

    series = get_series(name)
    if not series:
        print 'Serie not found "%s"' % name
        exit()

    for key, value in enumerate(series, 1):
        print key, value[1]

    serie_id = int(raw_input('>> '))
    serie = series[serie_id-1]

    seassons = get_seassons(serie)
    for key, value in enumerate(seassons, 1):
        print key, value[1]

    seasson_id = int(raw_input('>> '))
    seasson = seassons[seasson_id-1]

    episodes = get_episodes(seasson)
    print 0, 'All'
    for key, value in enumerate(episodes, 1):
        print key, value[2]

    episode_id = int(raw_input('>> '))

    if episode_id:
        episodes = [episodes[episode_id-1]]

    for episode in episodes:
        print '"%s" - "%s" - "%s"' % (serie[1], seasson[1], episode[2])
        print 'Subtitle', sub_url % (episode[0], lang)
        print

        data = url_open(player_url % episode[0])
        for key, value in source_re.findall(data):
            url = url_open(source_get, data=[('key', key), ('host', value),
                   ('vars', '&id=9555&subs=,ES,EN&tipo=s&amp;sub_pre=ES')])
            # before http are ugly chars
            url = url[url.find('http:'):].split('&id')[0]
            print '%s: %s' % (value, url)

        # Download Subtitle
        #url_open(sub_url % (episode[0], lang), filename=filename+'.srt')


if __name__ == '__main__':
    main()
