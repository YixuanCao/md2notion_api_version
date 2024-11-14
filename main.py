import glob
import argparse
from Parser.md2block import read_file
from NotionClient import NotionSyncDatabase, NotionSyncPage
from uploader import Md2NotionUploader
from notion_client.errors import APIResponseError
from notion.block import TextBlock
import os
import json


def get_parameter():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file_path", '-f',help="input file_path")
    parser.add_argument("--connection_key", type=str, help="the notion connection key")
    parser.add_argument("--database_id", type=str, help="the notion database_id")
    parser.add_argument("--smms_token", type=str, help="the smms token")
    parser.add_argument("--start_line", default=0, type=int, help="the start line of the update")
    
    args = parser.parse_args()
    return args

def has_children(content):
    return content.get('children')


def try_to_upload_blocks(uploader, batch, client, page_id):
    try:
        uploader.uploadBlocks(batch, client.notion, page_id)
    except APIResponseError as e:
        if 'Invalid image url' in json.loads(e.body)['message']:
            print('Invalid image url, retrying...')
            for i, block in enumerate(batch):
                if block['type']._type == 'image':
                    # convert this block to text block
                    batch[i] = {'type': TextBlock, 'title': block['source']}
            uploader.uploadBlocks(batch, client.notion, page_id)

def upload_single_file(filepath, client: NotionSyncPage|NotionSyncDatabase,
                       uploader: Md2NotionUploader,filename=None, start_line = 0):
    if filename is None:
        filename = os.path.basename(filepath)
    # create a new page for this file
    client.create_new_page(filename)
    page_id = client.get_page_id_via_name(filename)
    # get the notion style block information
    notion_blocks = read_file(filepath)
    uploader.local_root = os.path.dirname(filepath)
    batch = []
    for i, content in enumerate(notion_blocks):
        if i < start_line:continue    
        if len(batch) >= 60 or has_children(content):
            print(f"uploading lines {i-len(batch)} - {i},............")
            try_to_upload_blocks(uploader, batch, client, page_id)
            # uploader.uploadBlocks(batch, client.notion, page_id)
            batch = []

        if not has_children(content):
            batch.append(content)
        else:
            print(f"uploading line {i},............")
            uploader.uploadBlock(content, client.notion, page_id)
    if len(batch) > 0:
        print(f"uploading lines {i-len(batch)} - {i},............")
        try_to_upload_blocks(uploader, batch, client, page_id)
        # uploader.uploadBlocks(batch, client.notion, page_id)
    print('done!')


if __name__ == '__main__':

   
    args = get_parameter()
    connection_key = args.connection_key
    database_id  = args.database_id
    client      = NotionSyncDatabase(connection_key, database_id)
    # client      = NotionSyncPage(connection_key, database_id)
    uploader       = Md2NotionUploader(image_host='smms', smms_token=args.smms_token)
    filepath   = args.file_path
    if os.path.isdir(filepath):
        start_line = 0
        print('if you are uploading a directory, the start_line will be set to 0')
        files = glob.glob(os.path.join(filepath, '*.md'))
        for file in files:
            upload_single_file(file, client, uploader, start_line = start_line)
    else:
        start_line = args.start_line
        upload_single_file(filepath, client, uploader, start_line = start_line)