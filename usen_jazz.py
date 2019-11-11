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

def create_day_set(channel, npdate):
    sys.stderr.write("[Info] loading USEN playlist...\n")

    day_set = set()
    len_day_set = 0
    for hour in xrange(24):
        usen_html_source = get_usen_html(channel, npdate, "%02d:00:00" % hour)
        hour_list = unpack_usen_html(usen_html_source)
        day_set |= set(hour_list)
        len_new = len(day_set) - len_day_set 
        len_day_set = len(day_set)
        sys.stderr.write("[Info] hour=%s load:%s new:%s\n" % (hour, len(hour_list), len_new))
        # sys.stderr.flush()
    sys.stderr.write("[Info] USEN playlist total:%s\n" % (len(day_set)))
    # sys.stderr.flush()
    return day_set

def get_usen_html(channel, npdate, nptime):
    usen_url = "http://music.usen.com/usencms/search_nowplay1.php"
    result = requests.get(usen_url, {'npband': channel[1], 'npch': channel[2], 'npdate': npdate, 'nptime': nptime, 'nppage' : 'yes'})
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
    # token = spotipy.util.prompt_for_user_token(username, 'playlist-modify-public')
    token = spotipy.util.prompt_for_user_token(username, 'playlist-modify-private')
    # token = spotipy.util.prompt_for_user_token(username, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
    spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager, auth=token)
    return spotify


def unpack_musicname(musicname):
    slash = musicname.index(u'／')    
    
    trackname = musicname[:slash-1]
    artist = musicname[slash+2:]
    return (trackname, artist)


def adjust_musicname(trackname, artist):
    trackname = zen2han(trackname)

    # artist_sep = -1
    artist_slash = artist.find(u'／')
    if artist_slash != -1:
        artist = artist[:artist_slash]
        
    artist_and = artist.find(u'Ａｎｄ')
    if artist_and != -1:
        artist = artist[:artist_and]

    artist_and = artist.find(u'＆')
    if artist_and != -1:
        artist = artist[:artist_and]

    artist_plus = artist.find(u'＋')
    if artist_plus != -1:
        artist = artist[:artist_plus]

    artist_with = artist.find(u'Ｗｉｔｈ')
    if artist_plus != -1:
        artist = artist[:artist_with]

        
    artist_comma = artist.find(u'，')
    if artist_comma != -1:
        artist = artist[:artist_comma]
        
    # if artist_sep != -1:
    #     artist = artist[:artist_sep-1]
    
    artist = zen2han(artist)

    return (trackname, artist)


def search_track(spotify, trackname, artist, track_ids):
    result = spotify.search(q=u'%s %s' % (artist, trackname), type=u'track', limit=1)
    items = result['tracks']['items']
    if len(items)==0:
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

    channel_ary = [ \
        ('Smooth Jazz', 'B', '33'), \
        ('Piano Trio', 'B', '37'), \
        ('NEW DISC JAZZ', 'C', '50'), \
        ('JAZZ (discunion)', 'C', '25'), \
        ('Modern Jazz Piano', 'D', '18'), \
        ('Slow Jazz', 'H', 11), \
        ('Light Jazz', 'I', '07'), \
        ('Salon Jazz Instrumental', 'C', '18') , \
        ('Lounge Music', 'D', '05') \
    ]
    channel = channel_ary[7]
                   
    usen_date = '20190211'
    day_set = create_day_set(channel, usen_date)
    
    username = u'31hvgcmvsfx2mhyxh2kzaronagp4'
    spotify = spotify_init(username)
    # print('hello')    
    track_ids = []

    for musicname in day_set:
        # sys.stderr.write("[Info] %s\n" % (musicname))
        trackname, artist = unpack_musicname(musicname)
        # sys.stderr.write("[Info] %s: %s\n" % (trackname, artist))
        trackname, artist = \
            adjust_musicname(trackname, artist)
        # sys.stderr.write("[Info] %s: %s\n" % (trackname, artist))
        # sys.stderr.flush()
        if not search_track(spotify, trackname, artist, track_ids):
            sys.stderr.write("[Warn] nohit: %s %s\n" \
                % (trackname, artist))
                # sys.stderr.flush()
        # sys.stdout.flush()

    sys.stderr.write('[Info] hit=%s all=%s\n' % (len(track_ids), len(day_set)))
    # sys.stderr.flush()
    f_track_ids = codecs.open('track_ids.txt', 'w', 'utf_8')
    f_track_ids.write('\n'.join(track_ids))
    # for track_id in track_ids:
    #     f_track_ids.write("%s\n" % track_id)
    f_track_ids.close()

    # f_track_ids = codecs.open('track_ids_JPT.txt', 'r', 'utf_8')
    # track_ids_log = f_track_ids.read()
    # track_ids = track_ids_log.split('\n')
    # f_track_ids.close()

    
    sys.stderr.write('[Info] creating playlist on Spotify...\n')
    # sys.stderr.flush()
    playlists = spotify.user_playlist_create(username, "%s %s" % (channel[0], usen_date), public=False)
    playlist_id = playlists['id']
    sys.stderr.write("[Info] playlist_id=%s\n" % playlist_id)

    max_tracks_per_req = 100 # 100
    num_reqs = (len(track_ids)+max_tracks_per_req-1)/max_tracks_per_req
    for req_num in xrange(num_reqs):
        sys.stderr.write('[Info] %s / %s\n' % (req_num+1, num_reqs))
        # sys.stderr.flush()
        track_num_begin = req_num*max_tracks_per_req
        track_num_end = (req_num+1)*max_tracks_per_req
        # print track_ids[track_num_begin:track_num_end]
        spotify.user_playlist_add_tracks(username, playlist_id, track_ids[track_num_begin:track_num_end])

        
