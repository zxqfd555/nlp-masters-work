import json
import os
from multiprocessing.dummy import Pool as ThreadPool

from masters.core.download import BasicDownloadTask


TAG_POSTS_PATTERN = 'https://public-api.wordpress.com/rest/v1.1/read/tags/{}/posts'


class DownloadTask(BasicDownloadTask):

    @classmethod
    def from_settings(cls, tag, meta=None):
        url = TAG_POSTS_PATTERN.format(tag)
        return super().from_settings(
            url,
            meta={
                'tag': tag,
            }
        )

    def parse_api_response(self, response_json):
        posts = response_json['posts']
        result = []
        for post in posts:
            content_raw = post['content']
            content_clean = self.remove_html_trace_simple(content_raw)
            title_raw = post['title']
            title_clean = self.remove_html_trace_simple(title_raw)
            tags = self._cannonize_tags(post['tags'].keys())
            result.append(
                {
                    'content_raw': content_raw,
                    'content_clean': content_clean,
                    'title_raw': title_raw,
                    'title_clean': title_clean,
                    'tags': tags,
                }
            )

        return result

    def execute(self):
        response = self.download_url(self._url)
        if not response:
            return

        parsed_dataset_lines = self.parse_api_response(response.json())

        output_path = os.path.join(self._output_path, self._meta['tag'])
        with open(output_path, 'w') as f:
            json.dump(parsed_dataset_lines, f)

    def _cannonize_tags(self, tags_raw):
        result = []
        for tag in tags_raw:
            result.append(tag.strip('#').lower())  # #Tag -> tag

        return result


def download_dataset(seeds_path, output_path, max_threads):
    with open(seeds_path, 'r') as f:
        seeds = f.read().strip().split('\n')

    tasks = []
    for seed in seeds:
        task = DownloadTask.from_settings(seed)
        task.set_output_path(output_path)
        tasks.append(task)

    pool = ThreadPool(max_threads)
    pool.map(lambda t: t.execute(), tasks)
