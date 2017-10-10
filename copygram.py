#!/usr/bin/env python

from os import mkdir
from os.path import exists
from datetime import datetime
from time import sleep
from json import dump as j_dump
from pickle import dumps as p_dumps

from telethon import TelegramClient
from telethon.tl.functions.channels import (GetMessagesRequest,
        GetFullChannelRequest)
from telethon.tl.types import (Channel, Message, MessageMediaPhoto,
        MessageMediaDocument, DocumentAttributeFilename, DocumentAttributeAudio)

from config import (API_ID, API_HASH, PHONE, ROOT_DIR, SESSION_NAME,
                    ITERATIONS, MESSAGE_LIMIT, PAUSE)
 

def create_dirs(channel_dir):
    print("Creating directories...")
    if not exists(ROOT_DIR):
        mkdir(ROOT_DIR)
    if not exists(channel_dir):
        mkdir(channel_dir)
    for _dir in ("pickles", "jsons", "media"):
        if not exists(channel_dir + _dir):
            mkdir(channel_dir + _dir)

    
def dict_recursive_format(_dict): 
    if type(_dict) is dict:
        for key, val in _dict.items():
            if type(key) in (datetime, bytes):
                val = _dict.pop(key)
                _dict[str(key)] = val 
            if type(val) in (datetime, bytes) and type(key) in (datetime, bytes):
                _dict[str(key)] = str(val)
            elif type(val) in (datetime, bytes):
                _dict[key] = str(val)
            if type(val) is dict: 
                dict_recursive_format(val)
            elif type(val) is list: 
                for each in val:
                    dict_recursive_format(each)
    elif type(_dict) is list:
        for each in _dict:
            dict_recursive_format(each)
    return _dict


def get_extension(media):
    if media.document.mime_type == 'audio/ogg':
        return '.ogg'
    elif media.document.mime_type == 'text/plain':
        return '.txt'
    elif media.document.mime_type == 'audio/mpeg':
        return '.mp3'
    else:
        return '.xxx'


def date_format(date):
    return date.strftime('%Y-%m-%d_%H-%M-%S')


def get_client(sess_name, api_id, api_hash, phone):
    client = TelegramClient(sess_name, api_id, api_hash)
    try:
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            client.sign_in(phone, input('Enter the code: '))
    except ConnectionResetError:
        client.disconnect()
        client = get_client()
    return client


def get_channel(client):
    entities = client.get_dialogs()[1]
    channels = [entity for entity in entities if isinstance(entity, Channel)]
    for ch, num in zip(channels, range(len(channels))):
        print(num + 1, ' ', ch.title)
    choice = int(input('Enter number of channel: ')) - 1
    channel = channels[choice]
    return channel


def get_event_list(client, channel, _iter, limit, pause):
    ev_list = []
    for c in range(_iter):
        # TODO GetHistoryRequest implementing
        request = GetMessagesRequest(channel, range(c * limit, (c + 1) * limit))
        events = client(request, retries=10)
        ev_list.append(events)
        sleep(pause)
    return ev_list
    

def save_channel_pickle(dict_channel, dirname):
    pickles_dir = dirname + "pickles/"
    full_path = pickles_dir + "channel_info.pickle"
    with open(full_path, 'wb') as _file:
        _file.write(p_dumps(dict_channel))


def save_channel_json(dict_channel, dirname):
    jsons_dir = dirname + "jsons/"
    full_path = jsons_dir + "/channel_info.json"
    fixed_dict = dict_channel.copy()
    with open(full_path, 'w') as _file:
        fixed_dict = dict_recursive_format(fixed_dict)
        j_dump(fixed_dict, _file, ensure_ascii=False, indent=4)


def save_channel_info(client, channel, dirname):
    print("Saving channel info...")
    dict_channel = client(GetFullChannelRequest(channel)).to_dict()
    download_channel_photo(client, channel, dirname)
    save_channel_pickle(dict_channel, dirname)
    save_channel_json(dict_channel, dirname)


def save_messages_pickle(events, path):
    with open(path, 'wb') as _file:
        _file.write(p_dumps(events.to_dict()))


def save_messages_json(events, path):
    with open(path, 'w') as _file:
        fixed_dict = events.to_dict()
        fixed_dict = dict_recursive_format(fixed_dict)
        j_dump(fixed_dict, _file, ensure_ascii=False, indent=4)


def save_messages(channel, events, iter_num, dirname):
    print("Saving messages...")
    i = str(iter_num)
    full_path_pickle = dirname + '/pickles/messages-' + i + '.pickle'
    full_path_json = dirname + '/jsons/messages-' + i + '.json'
    save_messages_pickle(events, full_path_pickle)
    save_messages_json(events, full_path_json)
    

def download_channel_photo(client, channel, dirname):
    client.download_profile_photo(channel, dirname)


def download_photo(client, message, dirname):
    media_date = date_format(message.date)
    message_id = str(message.id).rjust(3, '0')
    media_id = str(message.media.photo.id)
    media_name = message_id + '.' + media_date + '.' + media_id + '.jpg'
    full_path = dirname + media_name
    if not exists(full_path):
        client.download_media(message, full_path)
        print('File "' + full_path + '" downloaded')
        return True
    else:
        print('File "' + full_path + '" exists already')
        return False


def download_document(client, message, dirname):
    media_date = date_format(message.media.document.date)
    message_id = str(message.id).rjust(3, '0')
    media_id = str(message.media.document.id)
    media_ext = get_extension(message.media)
    media_name = message_id + '.' + media_date + '.' + media_id + media_ext
    for attr in message.media.document.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            media_name = message_id  + '.' + media_id + '.' + attr.file_name
    full_path = dirname + media_name
    if not exists(full_path):
        client.download_media(message, full_path)
        print('File "' + full_path + '" downloaded')
        return True
    else:
        print('File "' + full_path + '" exists already')
        return False


def download_media(client, events, pause, dirname):
    print("Downloading media...")
    dirname += 'media/'
    for message in events.messages:
       if isinstance(message, Message):
           if message.media:
               if isinstance(message.media, MessageMediaPhoto):
                   if download_photo(client, message, dirname):
                       sleep(pause)
               if isinstance(message.media, MessageMediaDocument):
                   if download_document(client, message, dirname):
                       sleep(pause)


def main():
    client = get_client(SESSION_NAME, API_ID, API_HASH, PHONE)
    channel = get_channel(client)
    channel_dir = ROOT_DIR + channel.title + '/'
    create_dirs(channel_dir)
    save_channel_info(client, channel, channel_dir)
    ev_list = get_event_list(client, channel, ITERATIONS, MESSAGE_LIMIT, PAUSE)
    for events, iter_num in zip(ev_list, range(len(ev_list))):
        save_messages(channel, events, iter_num, channel_dir)
    for events, iter_num in zip(ev_list, range(len(ev_list))):
        download_media(client, events, (PAUSE / 4), channel_dir)
    client.disconnect()


if __name__ == '__main__':
    main()
