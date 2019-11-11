#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# todo
# - USEN HTML download           #
# - HTML parse                   #
#   - multiple pages             #
#   - merge lists                #
# - Item parse                   #
#   - Salon Classic Instrumental #
#   - Baroque                    
#   - Salon Jazz Instrumental    
# - Spotify search               #
#   - resume
#   - log no hit tracks
# - Spotify add to playlist      #

# todo: function-ize

import os
import sys
import requests
import codecs

import lxml.html

import re
from zen2han import zen2han

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util

def create_day_set(npdate):
    sys.stderr.write("[Info] loading USEN playlist...\n")

    day_set = set()
    len_day_set = 0
    for hour in xrange(24):
        usen_html_source = get_usen_html(npdate, "%02d:00:00" % hour)
        hour_list = unpack_usen_html(usen_html_source)
        day_set |= set(hour_list)
        len_new = len(day_set) - len_day_set 
        len_day_set = len(day_set)
        sys.stderr.write("[Info] hour=%s load:%s new:%s\n" % (hour, len(hour_list), len_new))
        # sys.stderr.flush()
    sys.stderr.write("[Info] USEN playlist total:%s\n" % (len(day_set)))
    # sys.stderr.flush()
    return day_set

def get_usen_html(npdate, nptime):
    usen_url = "http://music.usen.com/usencms/search_nowplay1.php"
    result = requests.get(usen_url, {'npband': 'B', 'npch': '38', 'npdate': npdate, 'nptime': nptime, 'nppage' : 'yes'})
    return result.text
    
def unpack_usen_html(usen_html_source):
    # print usen_html
    usen_html = lxml.html.fromstring(usen_html_source)

    # for li in usen_html.xpath('/div[@class="np_lists"]/ul/li'):
    return [li.text \
            for li in usen_html.xpath('./div[@class="np-lists"]/ul/li') ]
    # print(len(li.text))
    # print(li.text)
    # print(li.text.encode('cp932', "ignore").decode('cp932'))
    # sys.stderr.write(li.text.decode('cp932', "ignore"))
    # sys.stderr.write("\n")
        

def spotify_init(username):
    client_id = u'9196671e8cd54fc7b00eeef5067cb49f'
    client_secret = u'9c620f5f48e8430bbcfe050e239d0fc0'
    redirect_uri = u'http://127.0.0.1:8080/'
    
    os.environ['SPOTIPY_CLIENT_ID'] = client_id
    os.environ['SPOTIPY_CLIENT_SECRET'] = client_secret
    os.environ['SPOTIPY_REDIRECT_URI'] = redirect_uri
    
    client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(client_id, client_secret)
    token = spotipy.util.prompt_for_user_token(username, 'playlist-modify-public')
    spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager, auth=token)
    return spotify


def unpack_musicname(musicname):
    parenthesis_open = musicname.index(u'【')
    parenthesis_close = musicname.index(u'】', parenthesis_open)
    slash = musicname.index(u'／', parenthesis_close)    
    
    composer = musicname[parenthesis_open+1:parenthesis_close]

    composer_slash = composer.find(u'／')
    if not (composer_slash == -1):
        composer = composer[0:composer_slash] 

    composition = musicname[parenthesis_close+2:slash-1]
    player = musicname[slash+2:]
    return (composer, composition, player)


def adjust_musicname(composer, composition, player):
    # todo: postprocessing musicname
    # ideas
    # * one time
    #   - spell miss
    #     - peti -> petit
    #     - anthemise -> anthemis
    #   - op. XX YY (omit else)
    #     - number -> rome number
    # * needs trials and errors
    #   - word which sounds like music title
    #     eg berceuse
    
    composer = zen2han(composer) \
        .replace('Scriabine', 'Scriabin') \
        .replace('Moussorgsky', 'Mussorgsky') \
        .replace('F.Couperin', 'Couperin')

    composition = zen2han(composition)
    if len(composition)==90:
        # sys.stderr.write("%s %s\n" % (len(composition), composition))
        last_word_match = re.search('\S+$', composition)
        if last_word_match:
            composition = composition[:last_word_match.start()]
        
    composition = composition \
        .replace('.', ' . ') \
        .replace(',', ' , ') \
        .replace('Opus', 'op.') \
        .replace('Poemes', '') \
        .replace('Pour Piano', '') \
        .replace('For Piano', '') \
        .replace('A 4 Mains', '') \
        .replace('"', '')

    return (composer, composition, player)


def search_track(spotify, composer, composition, player, track_ids):
    result = spotify.search(q=u'artist:%s %s' % (composer, composition), type=u'track', limit=1)
    items = result['tracks']['items']
    if len(items)==0:
        return False
    # print(items[0][u'name'])
    track_ids.append(items[0]['id'])
    return True

def search_track_2(spotify, composer, composition, player, track_ids):
    q = None
    sep_pos_ary = []
    # todo sep on 'pour piano' ?
    
    op_no_re = "[Oo][Pp]\s*[.]\s*(\d+)[-\s]+(\d+)"
    op_no_match = re.search(op_no_re, composition)
    if op_no_match:
        op_num = op_no_match.group(1)
        no_num = op_no_match.group(2)
        sep_pos_ary.append(op_no_match.end())
    else:
        op_re = "[Oo][Pp]\s*[.]\s*(\d+)"
        op_match = re.search(op_re, composition)
        if op_match:
            op_num = op_match.group(1)
            sep_pos_ary.append(op_match.end())
        else:
            op_num = None
            
        no_re = "[Nn][Oo]\s*[.]\s*(\d+)"
        no_match = re.search(no_re, composition)
        if no_match:
            no_num = no_match.group(1)
            sep_pos_ary.append(no_match.end())
        else:
            no_num = None

    sep_pos_ary.append(composition.rfind('.'))
    sep_pos_ary.append(composition.rfind(':'))
    sep_pos_ary.append(composition.rfind('-'))
    
    sep_pos_last = max(sep_pos_ary)
    if sep_pos_last > 0:
        trackname = composition[sep_pos_last+1:]
    else:
        trackname = None
        
    if op_num and no_num:
        q = u'artist:%s "op.%s" "no.%s"' \
            % (composer, op_num, no_num)
    elif op_num and trackname:
        q = u'artist:%s "op.%s" %s' \
            % (composer, op_num, trackname)
    elif trackname:
        q = u'artist:%s %s' % (composer, trackname)
    elif op_num:
        q = u'artist:%s "op.%s"' % (composer, op_num)
    else:
        q = u'artist:%s %s' % (composer, composition)
            
    result = spotify.search(q=q, type=u'track', limit=1)
    items = result['tracks']['items']
    if len(items)==0:
        # sys.stderr.write("[Info] q:%s\n" % (q))
        # sys.stderr.write("[Info] op:%s no:%s trackname:%s\n" \
        #     % (op_num, no_num, trackname))
        return False
    # print(items[0][u'name'])
    track_ids.append(items[0]['id'])
    return True

if __name__ == u'__main__':

    ### python3
    # sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
    # sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)
    # sys.stdin = os.fdopen(sys.stdin.fileno(), 'r', buffering=1)

    ### python2
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)
    # sys.stdin = os.fdopen(sys.stdin.fileno(), 'r', buffering=1)
    
    sys.stdin = codecs.getreader('utf_8')(sys.stdin)
    sys.stdout = codecs.getwriter('utf_8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf_8')(sys.stderr)
    
    # f_usen_html = codecs.open('usen.html', 'r', 'utf_8')
    # usen_html_source = f_usen_html.read()
    # f_usen_html.close()
    
    # usen_html_source = get_usen_html('20190208', '11:00:00')
    # musicnames = unpack_usen_html(usen_html_source)
    # for musicname in musicnames:
    #     print musicname
    # exit()

    # f_musicnames = codecs.open('SCI.txt', 'r', 'utf_8')
    # musicnames = f_musicnames.read()
    # f_musicnames.close()
    
    usen_date = '20190208'
    day_set = create_day_set(usen_date)
    
    username = u'31hvgcmvsfx2mhyxh2kzaronagp4'
    spotify = spotify_init(username)
    
    track_ids = []

    # for musicname in musicnames.split('\n'):
    for musicname in day_set:
        composer, composition, player = unpack_musicname(musicname)
        composer, composition, player = \
            adjust_musicname(composer, composition, player)
        # sys.stderr.write("[Info] %s: %s\n" % (composer, composition))
        # sys.stderr.flush()
        if not search_track(spotify, composer, composition, player, track_ids):
            if not search_track_2(spotify, composer, composition, player, track_ids):
                sys.stderr.write("[Warn] nohit: %s %s\n" \
                    % (composer, composition))
                # sys.stderr.flush()
        # sys.stdout.flush()

    sys.stderr.write('[Info] hit=%s all=%s\n' % (len(track_ids), len(day_set)))
    # sys.stderr.flush()
    f_track_ids = codecs.open('track_ids.txt', 'w', 'utf_8')
    for track_id in track_ids:
        f_track_ids.write("%s\n" % track_id)
    f_track_ids.close()
        
    sys.stderr.write('[Info] creating playlist on Spotify...\n')
    # sys.stderr.flush()
    playlists = spotify.user_playlist_create(username, "Salon Classic Instrumental %s" % usen_date, public=False)
    playlist_id = playlists['id']
    sys.stderr.write("[Info] playlist_id=%s\n" % playlist_id)

    max_tracks_per_req = 100
    num_reqs = 1+len(track_ids)/max_tracks_per_req
    for req_num in xrange(num_reqs):
        sys.stderr.write('[Info] %s / %s\n' % (req_num+1, num_reqs))
        # sys.stderr.flush()
        track_num_begin = req_num*max_tracks_per_req
        track_num_end = (req_num+1)*max_tracks_per_req
        spotify.user_playlist_add_tracks(username, playlist_id, track_ids[track_num_begin:track_num_end])
        
