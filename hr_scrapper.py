import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import List
from datetime import datetime
import asyncio
import re

@dataclass(order=("pub_date", "title", "content"), frozen=True)
class HRPost:
    url: str
    author_url: str
    content: str
    pub_date: datetime
    topic: str

@dataclass(order=True)
class HRUser:
    url: str
    posts: List[HRPost] = field(default_factory=list)
    def posts_ammount(self) -> int:
        return len(self.posts)
    

class HRScrapper:
    root_url = "https://hyperreal.info/"
    talk_path = "talk/"
    def __init__(self, max_thread_len: int = None) -> None:
        self.max_thread_len = max_thread_len

    async def scrape_subforums(self):
        base_url = f"{self.root_url}{self.talk_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url) as response:
                resp_html = await response.text()
                soup = BeautifulSoup(resp_html)
                subforums_urls = soup.find_all("a", class_= "subforum unread")
                for subforum_url in subforums_urls:
                    yield subforum_url.get('href')
    
    async def scrape_subforum_topics_url(self, subforum_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(subforum_url) as response:
                resp_html = await response.text()
                soup = BeautifulSoup(resp_html)
                forums_urls = soup.find_all("a", class_="forum-title")
                for forum_url in forums_urls:
                    async for topic_url in self.scrape_subforum_topics_url(forum_url.get("href")):
                        yield topic_url
                topics_urls = soup.find_all("a")
                for topic_url in topics_urls:
                    yield topic_url.get("href")

    async def scrape_topic_page_posts(self, topic_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(topic_url) as response:
                resp_html = await response.text()
                soup = BeautifulSoup(resp_html)
                topic_posts = soup.find_all("div", "timeline-post position-relative clearfix")
                for topic_post in topic_posts:
                    post_url = topic_post.find("a", class_="post-title")
                    post_url = post_url.get("href")
                    content = topic_post.find("div", class_="content pb-2")
                    content = content.text
                    author_url = topic_post.find("a", class_="username-coloured")
                    if author_url is None:
                        author_url = topic_post.find("a", class_="username")
                    author_url = author_url.get("href")
                    
                    pub_date = topic_post.find("time")
                    pub_date = pub_date.get("datetime")[:-6]
                    pub_date = datetime.strptime(pub_date, '%Y-%m-%dT%H:%M:%S')
                    yield HRPost(post_url, author_url, content, pub_date, topic_url)

    async def get_topic_pages_ammount(self, topic_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(topic_url) as response:
                resp_html = await response.text()
                soup = BeautifulSoup(resp_html)
                page_range = soup.find("span", class_="fw-normal")
                page_range = page_range.find_all("strong")
                return int(page_range[1].text)

    async def scrape_topic_all_posts(self, topic_url):
        url = re.sub(r'\b-\d+\.html\b', ".html", topic_url)
        async for topic_post in self.scrape_topic_page_posts(url):
            yield topic_post
        page_ammount = await self.get_topic_pages_ammount(url)
        page_ammount -= 1
        page_nr = 10
        while page_ammount > 0:
            page_ammount -= 1
            curr_url = re.sub(r'.html', f"-{page_nr}.html", url)
            async for topic_post in self.scrape_topic_page_posts(curr_url):
                yield topic_post
            page_nr += 10

from argparse import ArgumentParser

async def main():
    hr_scrapper = HRScrapper()
    async for topic in hr_scrapper.scrape_topic_all_posts("https://hyperreal.info/talk/najgorsza-rzecz-jak-zrobili-cie-sie-t19567-10.html"):
        print(topic)
if __name__ == '__main__':
    asyncio.run(main())