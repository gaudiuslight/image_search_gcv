from google.cloud import vision
from google.cloud.vision import types
from request import Request
from response_handler import Response_Handler 
import json
import pickle
import io
import os


def search_images(infos = {}, source=None, count_start = 0, batch = 'new'):
    images = []
    requests = []
    batch_name = batch
    is_from_dict = False
    map_dict_reverse = {}

    if not source:
        print('ERROR FROM IMAGE SEARCH: no images requested')
        return 
            
    # at the end the needed format to make the batch request is a list of paths/urls
    # and these paths/urls will then be put into a list called requests, containing Request objects that have the structure required by google cloud vision API
    # but the source of the final list can be of various format as listed below...
    if isinstance(source, str):
        # in case of directory that contains images paths/urls
        if os.path.isdir(source):
            for filename in os.listdir(source):
                if filename.split('.')[-1].lower() in ('jpeg', 'jpg', 'png'):
                    images.append(os.path.join(source, filename))
        elif os.path.isfile(source):
            # or a file txt containing image paths/urls line by line can be passed
            if os.path.basename(source).split('.')[1] != 'txt':
                print('ERROR: File txt required')
                return
            with open(source) as f:
                for line in f:
                    images.append(line)
        else:
            print('ERROR: source passed is neither a txt file nor a directory')
            return
    elif isinstance(source, dict):
        # also a dictionary containing paths/urls can be passed
        is_from_dict = True
        count = 0
        for k, val in source.items():
            images.append(val)
            map_dict_reverse[count] = k
            count += 1
    elif isinstance(source, list):
        # or directly a list containing paths/urls can be passed
        images = source
    else:
        print('WARNING: not valid form of source')
        return
    
    # Initialize Client
    client = vision.ImageAnnotatorClient()
    # limiti di images per batch
    if len(images) > 16:
        print('ATTENTION: Maximum 16 images')
        return

    # The Request object needs the path/url as parameter and will create the adequate request body structure
    requests = [Request(img) for img in images]

    try:
        batch = client.batch_annotate_images([req.get_req() for req in requests])
    except:
        raise
    
    # get all methods of response_handler that take care of the response from google cloud vision
    methodList = ['gc_OCR']
    for i, response in enumerate(batch.responses):
        rh = Response_Handler()
        current_src =  requests[i].get_src()
        print('Extracting info from Image n. {}\nSource: {}'.format(i+1, current_src))
        for method in methodList:
            func = getattr(rh, method)
            func(response)
        is_local = not current_src.startswith('http')

        # if file is local... the info name assigned will be the filename itself + batch_name
        # else it will be called 'web_img + assigned number + batch_name'
        if is_from_dict:
            info_name = map_dict_reverse[i] 
        else:
            info_name = os.path.basename(current_src).split('.')[0] if is_local else 'web_img' + str(i + count_start) 
            info_name = info_name + '_from_' + batch_name
            
        infos[info_name] = rh.get_img_info() 
        infos[info_name]['source'] = current_src
    return infos

def save_to_file(info_to_save, file_name='tmp'):
    with io.open(file_name + '.json', 'w',encoding='utf8') as fp:
        _str = json.dumps(info_to_save,
                      indent=4, sort_keys=True,
                      separators=(',', ': '), ensure_ascii=False)
        fp.write(str(_str))

def main():
    # TODO handle if batch or not
    # handle requests desired
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="./apikey.json"
    my_infos = {}   
    # my_infos = search_images(my_infos, ['D:/annotate.png'])
    # print(my_infos["annotate_from_new"]["ocr"]["text"])
    # save_to_file(my_infos, 'annotates')

if __name__ == "__main__":
    main()


