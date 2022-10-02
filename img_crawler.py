import os
import time
import requests
import shutil
from multiprocessing import Pool
import argparse
from get_links import GetLinks
import imghdr
from pathlib import Path


class ImgCrawler:
    def __init__(self, skip_already_exist=True, n_threads=4, download_path='download', limit=0):
        """
        Args:
            skip_already_exist {bool} -- Skips keyword already downloaded before. If False, re-downloading.
            n_threads {int} -- Number of threads to download.
            download_path {str} -- Download folder path (default: ./download)
            limit {int} -- Maximum count of images to download. (0: infinite)
        """

        self.skip = skip_already_exist
        self.n_threads = n_threads
        self.download_path = download_path
        self.limit = limit

        os.makedirs('./{}'.format(self.download_path), exist_ok=True)

    @staticmethod
    def make_dir(dir_name):
        current_path = os.getcwd()
        path = os.path.join(current_path, dir_name)
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def get_keywords(keywords_file='keywords.txt'):
        # read keywords from file
        with open(keywords_file, 'r', encoding='utf-8-sig') as f:
            text = f.read()
            lines = text.split('\n')
            lines = filter(lambda x: x != '' and x is not None, lines)
            keywords = sorted(set(lines))

        print('{} keywords found: {}'.format(len(keywords), keywords))

        # re-save sorted keywords
        with open(keywords_file, 'w+', encoding='utf-8-sig') as f:
            for keyword in keywords:
                f.write('{}\n'.format(keyword))

        return keywords

    @staticmethod
    def get_extension_from_link(link, default='jpg'):
        splits = str(link).split('.')
        if len(splits) == 0:
            return default
        ext = splits[-1].lower()
        if 'jpg' in ext or 'jpeg' in ext:
            return 'jpg'
        elif 'gif' in ext:
            return 'gif'
        elif 'png' in ext:
            return 'png'
        else:
            return default

    @staticmethod
    def save_object_to_file(object, file_path):
        try:
            with open('{}'.format(file_path), 'wb') as file:
                shutil.copyfileobj(object.raw, file)
        except Exception as e:
            print('Save failed - {}'.format(e))

    @staticmethod
    def validate_image(path):
        ext = imghdr.what(path)
        if ext == 'jpeg':
            ext = 'jpg'
        return ext  # returns None if not valid

    def download_images(self, keyword, links, site_name, max_count=0):
        self.make_dir('{}/{}'.format(self.download_path, keyword.replace('"', '')))
        total = len(links)
        success_count = 0

        if max_count == 0:
            max_count = total

        for index, link in enumerate(links):
            if success_count >= total:
                break

            try:
                print('Downloading {} from {}: {} / {}'.format(keyword, site_name, success_count + 1, max_count))

                response = requests.get(link, stream=True)
                ext = self.get_extension_from_link(link)

                no_ext_path = '{}/{}/{}_{}'.format(self.download_path.replace('"', ''), keyword, site_name,
                                                   str(index).zfill(4))
                path = no_ext_path + '.' + ext
                self.save_object_to_file(response, path)

                success_count += 1
                del response

                ext2 = self.validate_image(path)
                if ext2 is None:
                    print('Unreadable file - {}'.format(link))
                    os.remove(path)
                    success_count -= 1
                else:
                    if ext != ext2:
                        path2 = no_ext_path + '.' + ext2
                        os.rename(path, path2)
                        print('Renamed extension {} -> {}'.format(ext, ext2))

            except Exception as e:
                print('Download failed - ', e)
                continue

    def download_from_site(self, keyword, site_name='naver'):
        try:
            get_links = GetLinks()  # initialize chrome driver
        except Exception as e:
            print('Error occurred while initializing chromedriver - {}'.format(e))
            return

        try:
            print('Collecting links... {} from {}'.format(keyword, site_name))
            links = get_links.get_naver_links(keyword)

            print('Downloading images from collected links... {} from {}'.format(keyword, site_name))
            self.download_images(keyword, links, site_name, max_count=self.limit)
            Path('{}/{}/{}_done'.format(self.download_path, keyword.replace('"', ''), site_name)).touch()

        except Exception as e:
            print('Exception {}:{} - {}'.format(site_name, keyword, e))

    def download(self, keyword):
        self.download_from_site(keyword=keyword)

    def do_crawling(self):
        keywords = self.get_keywords()

        tasks = []
        for keyword in keywords:
            dir_name = '{}/{}'.format(self.download_path, keyword)
            already_done = os.path.exists(os.path.join(os.getcwd(), dir_name))
            if already_done and self.skip:
                print('Skipping done task {}'.format(dir_name))
                continue

            if not already_done:
                tasks.append(keyword)

        pool = Pool(self.n_threads)
        pool.map_async(self.download, tasks)
        pool.close()
        pool.join()
        print('Task ended. Pool join. End Program')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip', type=str, default='true',
                        help='Skips keyword already downloaded before. This is needed when re-downloading.')
    parser.add_argument('--threads', type=int, default=4, help='Number of threads to download.')
    parser.add_argument('--limit', type=int, default=0,
                        help='Maximum count of images to download per site. (0: infinite)')
    parser.add_argument("--mode", default='client')
    parser.add_argument("--port", default=80)
    args = parser.parse_args()

    _skip = False if str(args.skip).lower() == 'false' else True
    _threads = args.threads
    _limit = int(args.limit)
    _mode = args.mode
    _port = args.port

    print('Options - skip:{}, threads:{}, limit:{}, mode:{}, port:{}'.format(_skip, _threads, _limit, _mode, _port))

    crawler = ImgCrawler(skip_already_exist=_skip, n_threads=_threads, limit=_limit)

    start_time = time.time()
    crawler.do_crawling()
    print(time.strftime("%H:%M:%S", time.gmtime(time.time() - start_time)))